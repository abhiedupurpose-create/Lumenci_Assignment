"""Versioned claim chart state: apply suggestions, undo, and diff.

The frontend holds exactly one ChartStore in session state; every mutation goes
through it so history and diffs stay consistent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.models import ClaimChart, ClaimRow, Suggestion


@dataclass
class ChartVersion:
    chart: ClaimChart
    label: str


@dataclass
class CellChange:
    row_id: str
    field_name: str
    before: str
    after: str


@dataclass
class ChartStore:
    history: list[ChartVersion] = field(default_factory=list)
    last_changes: list[CellChange] = field(default_factory=list)
    added_row_ids: set[str] = field(default_factory=set)
    viewing: Optional[int] = None  # index of an older version being viewed; None = latest

    # ---- lifecycle -------------------------------------------------------

    def load(self, chart: ClaimChart) -> None:
        self.history = [ChartVersion(chart.copy(), "Original upload")]
        self.last_changes = []
        self.added_row_ids = set()
        self.viewing = None

    @property
    def loaded(self) -> bool:
        return bool(self.history)

    @property
    def current(self) -> ClaimChart:
        return self.history[-1].chart

    @property
    def version_labels(self) -> list[str]:
        return [f"v{i}: {v.label}" for i, v in enumerate(self.history)]

    @property
    def version_number(self) -> int:
        """Current version index (0 = original upload)."""
        return len(self.history) - 1

    @property
    def can_undo(self) -> bool:
        return len(self.history) > 1

    # ---- version viewing & restore ----------------------------------------

    @property
    def is_viewing_old(self) -> bool:
        return self.viewing is not None

    @property
    def displayed(self) -> ClaimChart:
        """The chart the UI should render: an older snapshot when viewing one,
        otherwise the latest. Mutations always apply to the latest."""
        if self.viewing is not None:
            return self.history[self.viewing].chart
        return self.current

    def view_version(self, index: int) -> str:
        """Point the display at a version (read-only). Returns its label."""
        if not 0 <= index < len(self.history):
            raise ValueError(f"No version v{index}")
        self.viewing = None if index == self.version_number else index
        return self.history[index].label

    def return_to_latest(self) -> None:
        self.viewing = None

    def diff_between(self, a: int, b: int):
        """Changes from version a to version b: (cell changes, added row
        elements, removed row elements). Rows are matched by row_id."""
        old = {r.row_id: r for r in self.history[a].chart.rows}
        new = {r.row_id: r for r in self.history[b].chart.rows}
        changes: list[CellChange] = []
        for rid, row in new.items():
            prev = old.get(rid)
            if prev is None:
                continue
            for field_name in ("element", "feature", "reasoning", "strength"):
                before, after = getattr(prev, field_name), getattr(row, field_name)
                if before != after:
                    changes.append(CellChange(rid, field_name, before, after))
        added = [r.element for rid, r in new.items() if rid not in old]
        removed = [r.element for rid, r in old.items() if rid not in new]
        return changes, added, removed

    def restore(self, index: int) -> str:
        """Non-destructive restore: append a copy of an older version as the
        new latest, so history stays linear and the restore itself is undoable."""
        if not 0 <= index < len(self.history):
            raise ValueError(f"No version v{index}")
        target = self.history[index]
        changes, added_elements, _ = self.diff_between(self.version_number, index)
        label = f"Restored to v{index} ({target.label})"
        new_chart = target.chart.copy()
        prev_ids = {r.row_id for r in self.current.rows}
        self.history.append(ChartVersion(new_chart, label))
        self.last_changes = changes
        self.added_row_ids = {r.row_id for r in new_chart.rows
                              if r.row_id not in prev_ids}
        self.viewing = None
        return label

    # ---- mutations -------------------------------------------------------

    def apply_suggestion(self, sug: Suggestion, label: str,
                         overrides: Optional[dict] = None) -> None:
        """Apply an accepted (or user-modified) suggestion as a new version.

        `overrides` carries analyst edits from the Modify flow and wins over
        the suggestion's proposed values.
        """
        overrides = overrides or {}
        new_chart = self.current.copy()
        changes: list[CellChange] = []
        added: set[str] = set()

        if sug.action == "add_row":
            element = (overrides.get("element", sug.proposed_element) or "").strip()
            if not element:
                raise ValueError("A new row requires a non-empty claim element.")
            row = ClaimRow(
                element=element,
                feature=overrides.get("feature", sug.proposed_feature or ""),
                reasoning=overrides.get("reasoning", sug.proposed_reasoning or ""),
                strength=overrides.get("strength", sug.proposed_strength or "moderate"),
            )
            new_chart.rows.append(row)
            added = {row.row_id}
        elif sug.action == "revise" and sug.target_row_id:
            row = new_chart.get_row(sug.target_row_id)
            if row is None:
                raise ValueError(f"Suggestion targets unknown row {sug.target_row_id}")
            proposed = {
                "element": overrides.get("element", sug.proposed_element),
                "feature": overrides.get("feature", sug.proposed_feature),
                "reasoning": overrides.get("reasoning", sug.proposed_reasoning),
                "strength": overrides.get("strength", sug.proposed_strength),
            }
            for field_name, new_value in proposed.items():
                if new_value is None:
                    continue
                old_value = getattr(row, field_name)
                if new_value != old_value:
                    changes.append(CellChange(row.row_id, field_name, old_value, new_value))
                    setattr(row, field_name, new_value)
            if not changes:
                return  # nothing actually changed; don't record an empty version
        else:
            return  # needs_input suggestions never mutate the chart

        # Highlight state resets only once we know a new version is recorded,
        # so a no-op call can't wipe the previous version's highlights.
        self.history.append(ChartVersion(new_chart, label))
        self.last_changes = changes
        self.added_row_ids = added

    def undo(self) -> Optional[str]:
        """Revert the latest refinement. Returns the undone label, or None."""
        if len(self.history) <= 1:
            return None
        undone = self.history.pop()
        self.last_changes = []
        self.added_row_ids = set()
        return undone.label

    # ---- queries ---------------------------------------------------------

    def changed_cells(self) -> set[tuple[str, str]]:
        """(row_id, field_name) pairs changed by the most recent version."""
        return {(c.row_id, c.field_name) for c in self.last_changes}

    def change_log(self) -> list[str]:
        """Human-readable history of refinements (excludes the original upload)."""
        return [v.label for v in self.history[1:]]
