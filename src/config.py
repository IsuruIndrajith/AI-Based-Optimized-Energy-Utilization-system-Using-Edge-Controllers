"""
config.py — Centralized system configuration
=============================================
All operational thresholds, tariff rates, capacity limits, and tuning
parameters are defined here.  No magic numbers should appear in agent.py
or validate_policies.py; import from this module instead.

LECO tariff values are based on the Lanka Electricity Company (LECO)
Time-of-Use (TOU) domestic tariff schedule (2024 revision).
"""

# ---------------------------------------------------------------------------
# APPLIANCES
# ---------------------------------------------------------------------------

#: Canonical appliance identifiers used throughout the pipeline.
APPLIANCES = [
    "WashingMachine_Power",
    "Heater_Power",
    "AC_Power",
    "VehicleCharger_Power",
    "VacuumCleaner_Power",
]

#: Rated power consumption per appliance (kWh per ON-hour).
#: Source: manufacturer data-sheets / field measurements.
POWER_KWH: dict = {
    "WashingMachine_Power": 0.6,
    "Heater_Power":         2.0,
    "AC_Power":             1.2,
    "VehicleCharger_Power": 2.2,
    "VacuumCleaner_Power":  1.1,
}


# ---------------------------------------------------------------------------
# MQTT / CONNECTIVITY
# ---------------------------------------------------------------------------

MQTT_BROKER  = "test.mosquitto.org"
MQTT_PORT    = 1883
MQTT_TOPIC   = "power/tou_domestic"

#: Seconds to wait for an MQTT message before raising a timeout error.
MQTT_TIMEOUT_SECONDS: int = 30

#: Seconds to wait for the MQTT message inside the fetch_data LangGraph node
#: (shorter budget than the full timeout so the agent stays responsive).
MQTT_FETCH_TIMEOUT_SECONDS: int = 15

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

LLM_MODEL       = "llama3.2:latest"
LLM_TEMPERATURE = 0.0

# ---------------------------------------------------------------------------
# LOCATION (used for weather API)
# ---------------------------------------------------------------------------

#: Latitude / Longitude for Colombo, Sri Lanka.
LOCATION_LAT: float = 6.9271
LOCATION_LON: float = 79.8612
LOCATION_TZ:  str   = "Asia/Colombo"

# ---------------------------------------------------------------------------
# DEFAULT WEATHER FALLBACK
# When the Open-Meteo API is unreachable, these values are used.
# ---------------------------------------------------------------------------

DEFAULT_TEMPERATURE_C:   int = 25   # °C  – neutral tropical ambient
DEFAULT_HUMIDITY_PCT:    int = 60   # %   – moderate humidity

# ---------------------------------------------------------------------------
# WEATHER-BASED COMFORT THRESHOLDS
# ---------------------------------------------------------------------------

#: Hours at or above this temperature (°C) are considered "hot" for AC comfort.
HOT_TEMPERATURE_THRESHOLD_C:  float = 28.0

#: Hours at or above this humidity (%) are considered "humid" for AC comfort.
HIGH_HUMIDITY_THRESHOLD_PCT:  float = 80.0

#: Hours at or below this temperature (°C) are considered "cold" for Heater comfort.
COLD_TEMPERATURE_THRESHOLD_C: float = 20.0

# ---------------------------------------------------------------------------
# COMFORT SCHEDULING — SCORING BIAS
# Applied inside allocate_schedule() to make comfort-critical hours extremely
# attractive for AC and Heater, overriding minor price differences.
# ---------------------------------------------------------------------------

#: Negative score delta applied to hot/humid hours for AC_Power.
AC_COMFORT_SCORE_BIAS:     float = -100.0

#: Negative score delta applied to cold hours for Heater_Power.
HEATER_COMFORT_SCORE_BIAS: float = -100.0

# ---------------------------------------------------------------------------
# GRID CAPACITY DEFAULTS
# Used as fallback when the MQTT payload does not contain capacity fields.
# Values are in kW (total load ceiling per time-of-use band).
# ---------------------------------------------------------------------------

DEFAULT_CAPACITY_OFF_PEAK_KW: float = 5.0
DEFAULT_CAPACITY_DAY_KW:      float = 3.5
DEFAULT_CAPACITY_PEAK_KW:     float = 1.5

#: Minimum capacity assumed per hour when no TOU data is available at all.
FALLBACK_SLOT_CAPACITY_KW: float = 3.0

# ---------------------------------------------------------------------------
# LECO TOU TARIFF (FALLBACK / VALIDATION DEFAULTS)
# Used by validate_policies.py when no live MQTT price-map is available.
# Source: LECO domestic TOU tariff schedule, 2024.
# ---------------------------------------------------------------------------

#: Electricity rate (LKR / kWh) for each TOU band.
LECO_RATE_OFF_PEAK_LKR: float = 33.0
LECO_RATE_DAY_LKR:      float = 47.0
LECO_RATE_PEAK_LKR:     float = 106.0

#: Hour-of-day ranges [start, end) for each TOU band (24-hour clock).
#: off_peak = 00:00–05:00 and 22:00–24:00  (implicitly everything outside day/peak)
LECO_DAY_START_HOUR:      int = 5
LECO_DAY_END_HOUR:        int = 18
LECO_PEAK_START_HOUR:     int = 18
LECO_PEAK_END_HOUR:       int = 22

# ---------------------------------------------------------------------------
# VALIDATION TOLERANCES
# ---------------------------------------------------------------------------

#: Absolute kW tolerance when checking whether a slot's total load exceeds
#: its capacity limit (avoids floating-point false positives).
CAPACITY_TOLERANCE_KW: float = 0.001

#: Absolute cost tolerance (LKR) when comparing optimised vs. baseline cost.
#: A tiny margin prevents false failures due to floating-point rounding.
COST_TOLERANCE_LKR: float = 0.01

#: Maximum allowable scheduling runtime mismatch as a fraction of the
#: appliance's required hours (used in robustness policy checks).
#: E.g. 0.50 → up to 50 % mismatch is acceptable when capacity forces
#: the agent into a soft-fallback allocation.
RUNTIME_TOLERANCE_FRACTION: float = 0.50

#: Minimum absolute runtime mismatch tolerance in hours.
#: Ensures at least this many hours of slack even for appliances with
#: very short required runtimes.
RUNTIME_TOLERANCE_MIN_HOURS: int = 2

#: Minimum fraction of AC or Heater ON-hours that must overlap with
#: comfort-critical hours (hot/cold) for the comfort policy to PASS.
COMFORT_OVERLAP_MIN_RATIO: float = 0.40

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

#: Interval between successive agent decision cycles (seconds).
AGENT_LOOP_INTERVAL_SECONDS: int = 1800  # 30 minutes
