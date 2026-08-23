"""Sample data: the Acme thermostat claim chart from the assignment PDF,
plus two mock product documents so the grounding check has real text to verify
against, and the default system prompt."""
from __future__ import annotations

from backend.models import ClaimChart, ClaimRow, DocFile
from backend.prompts import load_prompt

SAMPLE_CHART_TITLE = "Patent US123456 vs. Acme Corp Thermostat"


def sample_chart() -> ClaimChart:
    return ClaimChart(
        title=SAMPLE_CHART_TITLE,
        rows=[
            ClaimRow(
                element="A temperature control device with a wireless communication module",
                feature=('Acme Thermostat product page states: "WiFi-enabled smart '
                         'thermostat connects to your home network"'),
                reasoning=("The Acme device has WiFi capability which satisfies the "
                           "wireless communication module requirement."),
                strength="strong",
            ),
            ClaimRow(
                element="A motion sensor for detecting occupancy",
                feature=('Acme technical specifications document shows: "Built-in motion '
                         'sensor detects when people are home"'),
                reasoning=("Motion sensor explicitly mentioned in specs directly maps to "
                           "the claim element for occupancy detection."),
                strength="strong",
            ),
            ClaimRow(
                element=("Machine learning algorithm that learns user temperature "
                         "preferences over time"),
                feature=('Acme marketing materials claim: "Auto-Schedule learns your '
                         'preferred temperatures"'),
                reasoning=("The learning behavior described suggests ML algorithm, though "
                           "technical implementation details are not disclosed. May need "
                           "stronger technical evidence."),
                strength="weak",
            ),
        ],
    )


SAMPLE_PRODUCT_PAGE = """Acme Smart Thermostat — Product Page

WiFi-enabled smart thermostat connects to your home network for control from
anywhere using the Acme Home app.

Auto-Schedule learns your preferred temperatures and builds a personalized
heating and cooling schedule around your life.

Built-in motion sensor detects when people are home, switching automatically
to Away mode when the house is empty to save energy.

Multi-zone comfort: pairs with Acme Room Sensors to balance temperatures
across rooms using a temperature sensor array distributed through the home.
"""

SAMPLE_TECH_SPEC = """Acme Smart Thermostat — Technical Specifications (Rev 2.3)

Connectivity: 802.11 b/g/n WiFi (2.4 GHz) wireless module; Bluetooth Low
Energy 5.0 for local pairing.

Sensors: Built-in motion sensor detects when people are home (PIR, 120-degree
field of view, 5 m range); ambient temperature sensor (accuracy +/- 0.1 C);
humidity sensor.

Temperature sensor array: supports up to 6 remote Acme Room Sensors; the
controller aggregates readings from the temperature sensor array to compute a
weighted whole-home temperature.

Adaptive control: the Auto-Schedule engine applies an on-device machine
learning model. The Auto-Schedule engine trains a gradient-boosted preference
model on manual setpoint adjustments, occupancy patterns, and time-of-day
signals to predict preferred temperatures over time. Model weights update
nightly on-device.
"""


def sample_docs() -> list[DocFile]:
    return [
        DocFile(name="acme_product_page.txt", text=SAMPLE_PRODUCT_PAGE, source="sample"),
        DocFile(name="acme_tech_spec.txt", text=SAMPLE_TECH_SPEC, source="sample"),
    ]


# The default analyst instructions live in prompts/system_prompt.md (all LLM
# prompts are versioned files there, never string literals in code).
DEFAULT_SYSTEM_PROMPT = load_prompt("system_prompt")
