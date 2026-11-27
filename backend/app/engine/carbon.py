"""Operational emissions comparison, excluding embodied/lifecycle emissions."""

import math
from numbers import Real


def _nonnegative(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite nonnegative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return number


def calculate_carbon(
    energy_served_kwh: float,
    unmet_energy_kwh: float,
    baseline_kg_co2_per_kwh: float = 0.7,
    renewable_kg_co2_per_kwh: float = 0.0,
    carbon_price_per_tonne: float = 0.0,
) -> dict[str, float]:
    """Compare an all-baseline supply against renewables plus assumed backup.

    The baseline factor also applies to hypothetical diesel coverage of unmet
    energy. Renewable emissions are configurable operational emissions, not a
    lifecycle assessment. Negative avoided emissions remain visible, but earn
    no carbon credits. Carbon prices are currency units per metric tonne CO2.
    """
    served = _nonnegative(energy_served_kwh, "energy_served_kwh")
    unmet = _nonnegative(unmet_energy_kwh, "unmet_energy_kwh")
    baseline_factor = _nonnegative(baseline_kg_co2_per_kwh, "baseline_kg_co2_per_kwh")
    renewable_factor = _nonnegative(renewable_kg_co2_per_kwh, "renewable_kg_co2_per_kwh")
    price = _nonnegative(carbon_price_per_tonne, "carbon_price_per_tonne")
    baseline = (served + unmet) * baseline_factor
    scenario = served * renewable_factor + unmet * baseline_factor
    avoided = baseline - scenario
    result = {
        "baseline_kg_co2": baseline,
        "scenario_kg_co2": scenario,
        "avoided_kg_co2": avoided,
        "carbon_credit_value": max(0.0, avoided) / 1000 * price,
    }
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("carbon calculation exceeds the supported numerical range")
    return result
