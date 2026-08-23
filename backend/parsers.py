"""Input parsing: claim charts (CSV/XLSX/JSON), product docs (TXT/MD/PDF),
and URL fetching for the "AI can't find evidence" edge case.

Parsing is intentionally forgiving, not production-grade — the assignment
explicitly scopes out complex file parsing.
"""
from __future__ import annotations

import io
import json
import re
from html.parser import HTMLParser

from backend.models import ClaimChart, ClaimRow, DocFile

# Column-name aliases → canonical field. Matching is case/punctuation-insensitive.
_COLUMN_ALIASES = {
    "element": {"patentclaimelement", "claimelement", "element", "claim"},
    "feature": {"accusedproductfeature", "accusedproductfeatureevidence",
                "productfeature", "feature", "evidence"},
    "reasoning": {"aireasoning", "reasoning", "analysis", "aireasoningevidence"},
    "strength": {"strength", "evidencestrength", "confidence"},
}

_VALID_STRENGTHS = {"strong", "moderate", "weak"}

# XML 1.0-invalid control characters (crash python-docx and pollute prompts)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value) -> str:
    """Strip XML-invalid control characters and surrounding whitespace."""
    return _CONTROL_CHARS.sub("", str(value or "")).strip()


class ChartParseError(ValueError):
    """Raised when an uploaded claim chart can't be understood."""


def _normalize(col: str) -> str:
    return re.sub(r"[^a-z]", "", str(col).lower())


def _map_columns(columns: list[str]) -> dict[str, str]:
    """Map actual column names to canonical fields.

    Positional fallback (col 0/1/2 = element/feature/reasoning) applies ONLY
    when no alias matched at all — mixing recognized names with positions
    could silently map two fields onto one column."""
    mapping: dict[str, str] = {}
    for col in columns:
        norm = _normalize(col)
        for canon, aliases in _COLUMN_ALIASES.items():
            if norm in aliases and canon not in mapping:
                mapping[canon] = col
    if not mapping and len(columns) >= 3:
        mapping = {"element": columns[0], "feature": columns[1],
                   "reasoning": columns[2]}
    missing = {"element", "feature", "reasoning"} - mapping.keys()
    if missing:
        raise ChartParseError(
            "Could not identify the 3 claim chart columns "
            "(Patent Claim Element / Accused Product Feature / AI Reasoning). "
            f"Missing: {sorted(missing)}. Found columns: {columns}")
    return mapping


def _rows_from_records(records: list[dict], mapping: dict[str, str],
                       title: str) -> ClaimChart:
    rows = []
    for rec in records:
        element = clean_text(rec.get(mapping["element"], ""))
        if not element:
            continue
        strength = clean_text(rec.get(mapping.get("strength", ""), "")).lower()
        rows.append(ClaimRow(
            element=element,
            feature=clean_text(rec.get(mapping["feature"], "")),
            reasoning=clean_text(rec.get(mapping["reasoning"], "")),
            strength=strength if strength in _VALID_STRENGTHS else "moderate",
        ))
    if not rows:
        raise ChartParseError("The claim chart file contained no data rows.")
    return ClaimChart(title=title, rows=rows)


def parse_claim_chart(filename: str, data: bytes) -> ClaimChart:
    """Parse an uploaded claim chart file into a ClaimChart."""
    import pandas as pd  # deferred: keeps backend importable without pandas for tests

    title = re.sub(r"\.[^.]+$", "", filename).replace("_", " ").strip() or "Claim Chart"
    lower = filename.lower()
    try:
        if lower.endswith(".json"):
            payload = json.loads(data.decode("utf-8"))
            records = payload.get("rows", payload) if isinstance(payload, dict) else payload
            if not isinstance(records, list) or not records:
                raise ChartParseError("JSON must be a list of row objects (or {'rows': [...]}).")
            mapping = _map_columns(list(records[0].keys()))
            return _rows_from_records(records, mapping, title)
        if lower.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(data))
        elif lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
        else:
            raise ChartParseError(f"Unsupported chart format: {filename}. Use CSV, XLSX, or JSON.")
    except ChartParseError:
        raise
    except Exception as exc:  # malformed file — surface a friendly message
        raise ChartParseError(f"Could not read {filename}: {exc}") from exc

    df = df.fillna("")
    mapping = _map_columns([str(c) for c in df.columns])
    return _rows_from_records(df.to_dict("records"), mapping, title)


def parse_product_doc(filename: str, data: bytes) -> DocFile:
    """Extract plain text from an uploaded product document."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise ChartParseError(f"Could not read PDF {filename}: {exc}") from exc
    else:  # txt / md / anything text-like
        text = data.decode("utf-8", errors="replace")
    text = clean_text(text)
    if not text:
        raise ChartParseError(f"{filename} contained no extractable text.")
    return DocFile(name=filename, text=text, source="upload")


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self._chunks.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self._chunks)


_PRIVATE_HOST = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1)",
    re.IGNORECASE)


def fetch_url_as_doc(url: str, timeout: int = 15) -> DocFile:
    """Fetch a URL and reduce it to plain text (simple scrape for the
    'no evidence found → analyst provides a URL' edge case).

    Guards: scheme normalized case-insensitively, private/loopback hosts
    rejected (basic SSRF hygiene for a public deployment), and non-text
    content types rejected instead of polluting the evidence pool."""
    import requests

    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/")[0]
    if _PRIVATE_HOST.match(host):
        raise ChartParseError("Private/local network URLs are not allowed.")
    resp = requests.get(url, timeout=timeout,
                        headers={"User-Agent": "iLumos-prototype/0.1"})
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "").lower()
    if ctype and not any(t in ctype for t in ("text/", "html", "xml", "json")):
        raise ChartParseError(f"That URL returned '{ctype}', not a readable page. "
                              "Download the file and upload it as a document instead.")
    extractor = _TextExtractor()
    extractor.feed(resp.text)
    text = clean_text(extractor.text)
    if not text:
        raise ChartParseError("The page returned no readable text.")
    name = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)[:60]
    return DocFile(name=name, text=text[:20000], source="url")
