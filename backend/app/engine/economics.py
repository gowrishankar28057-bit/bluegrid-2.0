"""Pure nominal discounted-cash-flow cost calculations.

Cost streams follow PDF Eq. 21: ``annual_cost`` is the payment at the end
of year one, before escalation. Initial investment and subsequent asset
replacements are valued across one project horizon, with no salvage credit.
Generation replacements escalate with general inflation; battery replacements
use the separate battery-cost escalation assumption. A battery subsidy applies
only to the initial investment. All energy quantities are annual kWh.
"""

from collections.abc import Mapping
import math
from numbers import Real
from typing import Any


def _number(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def _rate(value: Any, name: str) -> float:
    result = _number(value, name)
    if result <= -1:
        raise ValueError(f"{name} must be greater than -1")
    return result


def _years(value: Any, name: str = "years") -> int:
    result = _number(value, name)
    if result < 1 or not result.is_integer():
        raise ValueError(f"{name} must be a positive integer")
    return int(result)


def _finite(result: float, name: str) -> float:
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds the supported numerical range")
    return result


def _geometric_sum(log_ratio: float, count: int) -> float:
    """Return sum(q**k for k in range(count)), with a stable q=1 limit."""
    if count == 0:
        return 0.0
    if log_ratio == 0:
        return float(count)
    try:
        return _finite(math.expm1(count * log_ratio) / math.expm1(log_ratio), "cash-flow sum")
    except OverflowError as exc:
        raise ValueError("cash-flow sum exceeds the supported numerical range") from exc


def nominal_discount_rate(real_rate: float, general_inflation: float) -> float:
    """Convert real discount and inflation rates using the Fisher relation."""
    real = _rate(real_rate, "real_rate")
    inflation = _rate(general_inflation, "general_inflation")
    return _rate(_finite((1 + real) * (1 + inflation) - 1, "nominal rate"), "nominal rate")


def capital_recovery_factor(rate: float, years: int) -> float:
    """Annualize an initial present cost, including the exact zero-rate limit."""
    discount = _rate(rate, "rate")
    horizon = _years(years)
    if discount == 0:
        return 1.0 / horizon
    try:
        denominator = -math.expm1(-horizon * math.log1p(discount))
    except OverflowError as exc:
        raise ValueError("capital recovery factor exceeds the supported numerical range") from exc
    return _finite(discount / denominator, "capital recovery factor")


def present_value_escalating(
    annual_cost: float, escalation: float, discount_rate: float, years: int
) -> float:
    """Present value of end-year payments C0, C0*(1+g), ... .

    This is PDF Eq. 21 without an additional year-one escalation factor.
    At equal rates the exact limit is ``years * annual_cost / (1 + rate)``.
    """
    cost = _number(annual_cost, "annual_cost", nonnegative=True)
    growth = _rate(escalation, "escalation")
    discount = _rate(discount_rate, "discount_rate")
    horizon = _years(years)
    if cost == 0:
        return 0.0
    log_ratio = math.log1p(growth) - math.log1p(discount)
    return _finite(cost / (1 + discount) * _geometric_sum(log_ratio, horizon), "present value")


def _finance(finance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(finance, Mapping):
        raise ValueError("finance must be a mapping")
    try:
        real = _rate(finance["real_discount_rate"], "real_discount_rate")
        inflation = _rate(finance["general_inflation"], "general_inflation")
        horizon = _years(finance["project_years"], "project_years")
    except KeyError as exc:
        raise ValueError(f"missing finance parameter: {exc.args[0]}") from exc
    subsidy = _number(finance.get("battery_subsidy_fraction", 0), "battery_subsidy_fraction", nonnegative=True)
    if subsidy > 1:
        raise ValueError("battery_subsidy_fraction must be between 0 and 1")
    currency = finance.get("currency", "INR")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency must be a nonempty string")
    nominal = nominal_discount_rate(real, inflation)
    return {
        "inflation": inflation,
        "years": horizon,
        "nominal": nominal,
        "crf": capital_recovery_factor(nominal, horizon),
        "opex_escalation": _rate(finance.get("opex_escalation", inflation), "opex_escalation"),
        "battery_cost_escalation": _rate(finance.get("battery_cost_escalation", 0), "battery_cost_escalation"),
        "diesel_escalation": _rate(finance.get("diesel_escalation", inflation), "diesel_escalation"),
        "diesel_cost_per_kwh": _number(finance.get("diesel_cost_per_kwh", 0), "diesel_cost_per_kwh", nonnegative=True),
        "subsidy": subsidy,
        "currency": currency.strip(),
    }


def _unit_costs(technology_costs: Mapping[str, Any], financial: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    if not isinstance(technology_costs, Mapping) or not technology_costs:
        raise ValueError("technology_costs must be a nonempty mapping")
    costs: dict[str, dict[str, float]] = {}
    for name, technology in technology_costs.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(technology, Mapping):
            raise ValueError("technology costs require names and parameter mappings")
        battery = name == "battery"
        unit = "kwh" if battery else "kw"
        try:
            capex = _number(technology[f"capex_per_{unit}"], f"{name}.capex_per_{unit}", nonnegative=True)
            opex = _number(technology[f"opex_per_{unit}_year"], f"{name}.opex_per_{unit}_year", nonnegative=True)
            lifetime = _years(technology["lifetime_years"], f"{name}.lifetime_years")
        except KeyError as exc:
            raise ValueError(f"missing cost parameter for {name}: {exc.args[0]}") from exc
        replacement_fraction = _number(technology.get("replacement_fraction", 1), f"{name}.replacement_fraction", nonnegative=True)
        net_capex = capex * (1 - financial["subsidy"] if battery else 1)
        replacement_pv = 0.0
        replacement_count = (financial["years"] - 1) // lifetime
        if replacement_count and capex and replacement_fraction:
            escalation = financial["battery_cost_escalation"] if battery else financial["inflation"]
            log_ratio = lifetime * (math.log1p(escalation) - math.log1p(financial["nominal"]))
            try:
                replacement_pv = _finite(
                    capex * replacement_fraction * math.exp(log_ratio)
                    * _geometric_sum(log_ratio, replacement_count), "replacement present value"
                )
            except OverflowError as exc:
                raise ValueError("replacement present value exceeds the supported numerical range") from exc
        opex_pv = present_value_escalating(opex, financial["opex_escalation"], financial["nominal"], financial["years"])
        project_npv = _finite(math.fsum([net_capex, replacement_pv, opex_pv]), "unit project present cost")
        costs[name] = {
            "capex": capex,
            "net_capex": net_capex,
            "opex_year_one": opex,
            "project_npv": project_npv,
            "annualized_cost": _finite(project_npv * financial["crf"], "unit annualized cost"),
        }
    return costs


def annual_cost_coefficients(technology_costs: Mapping[str, Any], finance: Mapping[str, Any]) -> dict[str, float]:
    """Return annual cost per installed kW (generation) or kWh (battery).

    These coefficients use exactly the same cost breakdown as evaluation, so
    their capacity-weighted sum equals ``evaluate_economics()['annualized_cost']``.
    """
    financial = _finance(finance)
    return {name: costs["annualized_cost"] for name, costs in _unit_costs(technology_costs, financial).items()}


def evaluate_economics(
    capacities_kw: Mapping[str, float],
    battery_kwh: float,
    energy_served_kwh: float,
    unmet_energy_kwh: float,
    technology_costs: Mapping[str, Any],
    finance: Mapping[str, Any],
) -> dict[str, float | str | None]:
    """Evaluate positive system costs; zero-energy unit costs are ``None``.

    ``project_npv`` and ``annualized_cost`` cover renewable generation and BESS.
    ``diesel_backup_cost`` is the annualized cost of hypothetically supplying
    unmet energy with diesel. LCOE excludes that backup; cost of service includes
    it and uses total demand as its denominator. No salvage is credited.
    """
    financial = _finance(finance)
    costs = _unit_costs(technology_costs, financial)
    if not isinstance(capacities_kw, Mapping):
        raise ValueError("capacities_kw must be a mapping")
    capacities: dict[str, float] = {}
    for name, capacity in capacities_kw.items():
        if name == "battery" or name not in costs:
            raise ValueError(f"unknown generation technology: {name}")
        capacities[name] = _number(capacity, f"{name}.capacity_kw", nonnegative=True)
    battery = _number(battery_kwh, "battery_kwh", nonnegative=True)
    if battery and "battery" not in costs:
        raise ValueError("battery cost parameters are required for nonzero battery capacity")
    if "battery" in costs:
        capacities["battery"] = battery
    served = _number(energy_served_kwh, "energy_served_kwh", nonnegative=True)
    unmet = _number(unmet_energy_kwh, "unmet_energy_kwh", nonnegative=True)
    demand = _finite(served + unmet, "demand energy")
    totals = {
        metric: _finite(math.fsum(capacity * costs[name][metric] for name, capacity in capacities.items()), metric)
        for metric in ("capex", "net_capex", "opex_year_one", "annualized_cost", "project_npv")
    }
    diesel_year_one = _finite(unmet * financial["diesel_cost_per_kwh"], "diesel year-one cost")
    diesel_eac = _finite(present_value_escalating(
        diesel_year_one, financial["diesel_escalation"], financial["nominal"], financial["years"]
    ) * financial["crf"], "diesel annualized cost")
    totals.update({
        "lcoe": _finite(totals["annualized_cost"] / served, "lcoe") if served else None,
        "cost_of_service": _finite((totals["annualized_cost"] + diesel_eac) / demand, "cost_of_service") if demand else None,
        "diesel_backup_cost": diesel_eac,
        "currency": financial["currency"],
    })
    return totals
