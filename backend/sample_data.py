"""Sample cases for instant testing: three claim charts (the assignment's Acme
thermostat plus two more), each with mock product documents so the grounding
check has real text to verify against. Also loads the default system prompt.

Every sample follows the same recipe: 3 rows (one deliberately weak, backed
only by marketing copy), a technical spec containing stronger language for the
weak row, and one disclosed feature the chart misses — so strengthen / add-row
/ no-evidence flows are all demonstrable on any sample.
"""
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


# ---------------------------------------------------------------------------
# Sample case 2: VoltEdge electric scooter
# ---------------------------------------------------------------------------

def _scooter_chart() -> ClaimChart:
    return ClaimChart(
        title="Patent US789012 vs. VoltEdge E-Scooter",
        rows=[
            ClaimRow(
                element="An electric hub motor with regenerative braking",
                feature=('VoltEdge technical specifications state: "The 500W rear hub '
                         'motor recovers energy through regenerative braking, feeding '
                         'charge back to the battery during deceleration"'),
                reasoning=("The specification explicitly discloses a hub motor with "
                           "regenerative braking, directly satisfying this element."),
                strength="strong",
            ),
            ClaimRow(
                element="A removable battery pack with a battery management system",
                feature=('VoltEdge technical specifications state: "The removable '
                         '48V battery pack includes an integrated battery management '
                         'system monitoring cell temperature, charge balance, and '
                         'discharge current"'),
                reasoning=("Removable pack and BMS are both expressly disclosed in "
                           "technical documentation."),
                strength="strong",
            ),
            ClaimRow(
                element=("A mobile application wirelessly controlling motor speed "
                         "settings"),
                feature=('VoltEdge marketing page claims: "The VoltEdge app puts you '
                         'in control of your ride"'),
                reasoning=("Marketing language implies app control but does not state "
                           "what is controlled or over which wireless link. Needs "
                           "stronger technical evidence."),
                strength="weak",
            ),
        ],
    )


_SCOOTER_PRODUCT_PAGE = """VoltEdge E-Scooter — Product Page

The VoltEdge app puts you in control of your ride. Customize your experience
and track every trip from your phone.

Go further: the removable 48V battery pack swaps in seconds, so you can keep
a spare charged and double your range.

Regenerative braking recovers energy every time you slow down, feeding charge
back into the battery.

Never lose your ride: built-in GPS anti-theft tracking keeps an eye on your
scooter wherever you park it.
"""

_SCOOTER_TECH_SPEC = """VoltEdge E-Scooter — Technical Specifications (Rev 1.4)

Motor: 500W rear hub motor. The 500W rear hub motor recovers energy through
regenerative braking, feeding charge back to the battery during deceleration.

Battery: The removable 48V battery pack includes an integrated battery
management system monitoring cell temperature, charge balance, and discharge
current. Charge time 4.5 hours.

Connectivity: The VoltEdge companion app communicates over Bluetooth Low
Energy 5.2 to adjust motor speed limits, acceleration profiles, and
regenerative braking strength in real time.

Security: Integrated GPS module reports scooter location every 30 seconds in
anti-theft mode; the system locks the motor and sounds an alarm when
unauthorized movement is detected.
"""


# ---------------------------------------------------------------------------
# Sample case 3: NimbusCam security camera
# ---------------------------------------------------------------------------

def _camera_chart() -> ClaimChart:
    return ClaimChart(
        title="Patent US456789 vs. NimbusCam Security Camera",
        rows=[
            ClaimRow(
                element="A motion sensor triggering video recording upon detection",
                feature=('NimbusCam technical specifications state: "The passive '
                         'infrared motion sensor triggers video recording within '
                         '200 milliseconds of detected movement"'),
                reasoning=("Motion-triggered recording is expressly disclosed with "
                           "quantified latency, directly mapping to this element."),
                strength="strong",
            ),
            ClaimRow(
                element="Infrared illumination for night-time image capture",
                feature=('NimbusCam technical specifications state: "Eight 850nm '
                         'infrared LEDs provide night vision up to 10 meters in '
                         'complete darkness"'),
                reasoning=("Infrared night capture is disclosed with specific LED "
                           "wavelength and range."),
                strength="strong",
            ),
            ClaimRow(
                element=("A machine learning model classifying detected motion as "
                         "human activity"),
                feature=('NimbusCam marketing page claims: "Smart alerts tell you '
                         'who\'s there"'),
                reasoning=("Marketing copy suggests intelligent classification but "
                           "discloses no model, hardware, or method. Needs stronger "
                           "technical evidence."),
                strength="weak",
            ),
        ],
    )


_CAMERA_PRODUCT_PAGE = """NimbusCam Security Camera — Product Page

Smart alerts tell you who's there — get notified about people, not passing
cars or pets.

See clearly day and night with infrared night vision that reaches every
corner of your yard.

Your footage stays yours: all clips are protected with end-to-end encryption
before they ever leave the camera.
"""

_CAMERA_TECH_SPEC = """NimbusCam Security Camera — Technical Specifications (Rev 3.1)

Detection: The passive infrared motion sensor triggers video recording within
200 milliseconds of detected movement. Detection range 9 meters, 130-degree
field of view.

Night vision: Eight 850nm infrared LEDs provide night vision up to 10 meters
in complete darkness.

On-device AI: The on-camera neural processing unit runs a quantized
convolutional neural network for person detection, classifying detected
motion as human activity and distinguishing people from pets and vehicles
before an alert is sent. Model updates are delivered with firmware releases.

Storage security: All footage is encrypted end-to-end with AES-256 before
upload; cloud clips remain encrypted at rest for 30 days.
"""


# ---------------------------------------------------------------------------
# Sample registry
# ---------------------------------------------------------------------------

SAMPLES: dict[str, dict] = {
    "Acme Smart Thermostat — US123456 (assignment sample)": {
        "chart": sample_chart,
        "docs": lambda: [
            DocFile(name="acme_product_page.txt", text=SAMPLE_PRODUCT_PAGE,
                    source="sample"),
            DocFile(name="acme_tech_spec.txt", text=SAMPLE_TECH_SPEC,
                    source="sample"),
        ],
        "hint": ('Element 3 (the ML algorithm) is weak — try: "The AI reasoning '
                 'for the ML algorithm element is weak — add more technical '
                 'details." The docs also disclose a temperature sensor array '
                 "the chart misses."),
    },
    "VoltEdge E-Scooter — US789012": {
        "chart": _scooter_chart,
        "docs": lambda: [
            DocFile(name="voltedge_product_page.txt", text=_SCOOTER_PRODUCT_PAGE,
                    source="sample"),
            DocFile(name="voltedge_tech_spec.txt", text=_SCOOTER_TECH_SPEC,
                    source="sample"),
        ],
        "hint": ('Element 3 (app control) is weak — try: "Strengthen the evidence '
                 'for element 3." The docs also disclose GPS anti-theft tracking '
                 "the chart misses."),
    },
    "NimbusCam Security Camera — US456789": {
        "chart": _camera_chart,
        "docs": lambda: [
            DocFile(name="nimbuscam_product_page.txt", text=_CAMERA_PRODUCT_PAGE,
                    source="sample"),
            DocFile(name="nimbuscam_tech_spec.txt", text=_CAMERA_TECH_SPEC,
                    source="sample"),
        ],
        "hint": ('Element 3 (person detection) is weak — try: "The reasoning for '
                 'element 3 is vague — add technical detail." The docs also '
                 "disclose AES-256 encrypted storage the chart misses."),
    },
}


def sample_names() -> list[str]:
    return list(SAMPLES.keys())


def load_sample(name: str) -> tuple[ClaimChart, list[DocFile], str]:
    """(chart, docs, starter hint) for a sample case by display name."""
    entry = SAMPLES[name]
    return entry["chart"](), entry["docs"](), entry["hint"]


# The default analyst instructions live in prompts/system_prompt.md (all LLM
# prompts are versioned files there, never string literals in code).
DEFAULT_SYSTEM_PROMPT = load_prompt("system_prompt")
