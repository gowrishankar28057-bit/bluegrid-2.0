"""Request normalization with explicit units and bounded resource use."""
from copy import deepcopy
import math
import numpy as np

from .config import TECHNOLOGIES, BATTERY_DEFAULTS, FINANCE_DEFAULTS, ILLUSTRATIVE_COSTS
from .data_loader import numeric_series


def number(value, name, minimum=0.0, maximum=1e9):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def mapping(value, name, allowed):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"{name} must be an object containing only {sorted(allowed)}")
    return value


def normalize_scenario(payload, dataset):
    allowed = {"location_id", "demand_kw", "demand_profile_kw", "capacities_kw", "battery_kwh", "battery", "max_lpsp", "min_wind_fraction"}
    mapping(payload, "scenario", allowed)
    if "demand_kw" in payload and "demand_profile_kw" in payload:
        raise ValueError("provide demand_kw or demand_profile_kw, not both")
    n = len(dataset["timestamps"])
    if "demand_profile_kw" in payload:
        demand = numeric_series(payload["demand_profile_kw"], "demand_profile_kw", length=n, maximum=1e6)
    else:
        demand = np.full(n, number(payload.get("demand_kw", 100.0), "demand_kw", maximum=1e6))
    if float(demand.sum()) <= 0:
        raise ValueError("annual demand must be greater than zero")
    capacities = mapping(payload.get("capacities_kw", {}), "capacities_kw", TECHNOLOGIES)
    capacities = {name: number(capacities.get(name, 0.0), name, maximum=1e7) for name in TECHNOLOGIES}
    battery = deepcopy(BATTERY_DEFAULTS)
    battery.update(mapping(payload.get("battery", {}), "battery", battery))
    for key in battery:
        battery[key] = number(battery[key], f"battery.{key}", minimum=0.0, maximum=10.0 if key == "c_rate" else 1.0)
    for key in ("charge_efficiency", "discharge_efficiency", "depth_of_discharge"):
        if battery[key] == 0:
            raise ValueError(f"battery.{key} must be greater than zero")
    return {"location_id": dataset["location_id"], "demand_profile_kw": demand,
            "capacities_kw": capacities, "battery_kwh": number(payload.get("battery_kwh", 0.0), "battery_kwh", maximum=1e8),
            "battery": battery, "max_lpsp": number(payload.get("max_lpsp", 0.05), "max_lpsp", maximum=1.0),
            "min_wind_fraction": number(payload.get("min_wind_fraction", 0.0), "min_wind_fraction", maximum=1.0)}


def normalize_costs(costs=None, finance=None):
    result = deepcopy(ILLUSTRATIVE_COSTS)
    if costs is not None:
        for name, entry in mapping(costs, "technology_costs", result).items():
            result[name].update(mapping(entry, f"technology_costs.{name}", result[name]))
    for name, entry in result.items():
        for key, value in entry.items():
            entry[key] = number(value, f"{name}.{key}", maximum=1e10)
            if key == "lifetime_years" and (entry[key] < 1 or not entry[key].is_integer() or entry[key] > 100):
                raise ValueError("lifetime_years must be an integer between 1 and 100")
            if key == "lifetime_years":
                entry[key] = int(entry[key])
    params = deepcopy(FINANCE_DEFAULTS)
    if finance is not None:
        params.update(mapping(finance, "finance", params))
    for key, value in params.items():
        if key == "currency":
            if not isinstance(value, str) or len(value) != 3 or not value.isalpha() or not value.isascii():
                raise ValueError("finance.currency must be a three-letter currency code")
            params[key] = value.upper()
        elif key == "project_years":
            numeric = number(value, key, minimum=1, maximum=100)
            if not numeric.is_integer():
                raise ValueError("project_years must be an integer")
            params[key] = int(numeric)
        else:
            params[key] = number(value, f"finance.{key}", minimum=-0.9 if key.endswith("rate") or "inflation" in key or "escalation" in key else 0.0,
                                 maximum=1.0 if key == "battery_subsidy_fraction" else 1e5 if key == "diesel_cost_per_kwh" else 1.0)
    return result, params


def normalize_options(options=None):
    if options is not None and not isinstance(options, dict):
        raise ValueError("options must be an object")
    result = dict(options or {})
    mapping(result, "options", {"selected_technologies", "max_capacities_kw", "max_battery_kwh", "candidate_budget", "max_results", "capacity_grid"})
    selected = result.get("selected_technologies", list(TECHNOLOGIES))
    if not isinstance(selected, list) or not selected or any(name not in TECHNOLOGIES for name in selected) or len(set(selected)) != len(selected):
        raise ValueError("selected_technologies must be a nonempty list of distinct supported technology names")
    result["selected_technologies"] = selected
    for key, default, maximum in (("candidate_budget", 64, 256), ("max_results", 5, 10)):
        numeric = number(result.get(key, default), key, minimum=1, maximum=maximum)
        if not numeric.is_integer():
            raise ValueError(f"{key} must be an integer")
        result[key] = int(numeric)
    if "max_battery_kwh" in result:
        result["max_battery_kwh"] = number(result["max_battery_kwh"], "max_battery_kwh", maximum=1e8)
    if "max_capacities_kw" in result:
        result["max_capacities_kw"] = {name: number(value, name, maximum=1e7) for name, value in mapping(result["max_capacities_kw"], "max_capacities_kw", TECHNOLOGIES).items()}
    if "capacity_grid" in result:
        grid = mapping(result["capacity_grid"], "capacity_grid", set(TECHNOLOGIES) | {"battery_kwh"})
        result["capacity_grid"] = {name: numeric_series(values, name, maximum=1e8).tolist() for name, values in grid.items()}
        if any(len(values) > 16 for values in result["capacity_grid"].values()):
            raise ValueError("capacity_grid may contain at most 16 values per dimension")
    return result
