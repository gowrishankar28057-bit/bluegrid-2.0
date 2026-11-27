"""Bounded capacity search; a monthly LP proposes, hourly dispatch decides.

The search is deterministic for fixed inputs. It does not certify a globally
optimal hourly design. All power variables in the LP are kW, storage is kWh,
and monthly durations are applied when converting power into energy.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from math import prod
from typing import Callable

import numpy as np
from scipy.optimize import linprog

from .economics import (
    annual_cost_coefficients,
    capital_recovery_factor,
    nominal_discount_rate,
    present_value_escalating,
)

TECHNOLOGIES = (
    "floating_solar", "onshore_solar", "onshore_wind", "offshore_wind", "otec", "wave"
)
WIND = ("onshore_wind", "offshore_wind")


def _finite_nonnegative(value, name):
    value = float(value)
    if not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _monthly_proposal(dataset, scenario, costs, finance, selected, maxima, max_battery):
    """Return sizing proposal and solver diagnostic, never hourly certification."""
    demand = np.asarray(scenario["demand_profile_kw"], dtype=float)
    month_index = np.asarray(dataset["month_index"])
    months = np.unique(month_index)
    groups = [month_index == month for month in months]
    hours = np.array([group.sum() for group in groups], dtype=float)
    load = np.array([demand[group].mean() for group in groups])
    cf = np.array([
        [np.asarray(dataset["capacity_factors"][tech])[group].mean() for group in groups]
        for tech in selected
    ])
    nt, nm = len(selected), len(months)
    # capacity, battery, generation, charge, discharge, SOC, unmet, curtailment
    battery_i = nt
    gen_start = nt + 1
    ch_start = gen_start + nt * nm
    dis_start = ch_start + nm
    soc_start = dis_start + nm
    unmet_start = soc_start + nm
    spill_start = unmet_start + nm
    count = spill_start + nm
    objective = np.zeros(count)
    coefficients = annual_cost_coefficients(costs, finance)
    for i, tech in enumerate(selected):
        objective[i] = coefficients[tech]
    objective[battery_i] = coefficients["battery"]
    rate = nominal_discount_rate(finance["real_discount_rate"], finance["general_inflation"])
    diesel = present_value_escalating(
        finance["diesel_cost_per_kwh"], finance["diesel_escalation"],
        rate, finance["project_years"],
    ) * capital_recovery_factor(rate, finance["project_years"])
    objective[unmet_start:spill_start] = diesel * hours
    battery = scenario["battery"]
    eta_c = battery.get("charge_efficiency", 0.95)
    eta_d = battery.get("discharge_efficiency", 0.95)
    dod = battery.get("depth_of_discharge", 0.8)
    c_rate = battery.get("c_rate", 0.5)
    self_discharge = battery.get("self_discharge_per_hour", 0.015)
    equalities, rhs, inequalities, upper = [], [], [], []
    for month in range(nm):
        balance = np.zeros(count)
        for tech_i in range(nt):
            gen_i = gen_start + tech_i * nm + month
            balance[gen_i] = 1
            availability = np.zeros(count)
            availability[gen_i] = 1
            availability[tech_i] = -cf[tech_i, month]
            inequalities.append(availability)
            upper.append(0.0)
        balance[ch_start + month] = -1
        balance[dis_start + month] = 1
        balance[unmet_start + month] = 1
        balance[spill_start + month] = -1
        equalities.append(balance)
        rhs.append(load[month])
        state = np.zeros(count)
        state[soc_start + month] += 1
        state[soc_start + (month - 1) % nm] -= (1 - self_discharge) ** hours[month]
        state[ch_start + month] -= eta_c * hours[month]
        state[dis_start + month] += hours[month] / eta_d
        equalities.append(state)
        rhs.append(0.0)
        for index, multiplier in (
            (ch_start + month, c_rate), (dis_start + month, c_rate),
            (soc_start + month, dod),
        ):
            limit = np.zeros(count)
            limit[index] = 1
            limit[battery_i] = -multiplier
            inequalities.append(limit)
            upper.append(0.0)
    reliability = np.zeros(count)
    reliability[unmet_start:spill_start] = hours
    inequalities.append(reliability)
    upper.append(float(scenario["max_lpsp"]) * demand.sum())
    min_wind = float(scenario.get("min_wind_fraction", 0)) * demand.max(initial=0)
    if min_wind:
        policy = np.zeros(count)
        for i, tech in enumerate(selected):
            if tech in WIND:
                policy[i] = -1
        inequalities.append(policy)
        upper.append(-min_wind)
    bounds = [(0, maxima[tech]) for tech in selected] + [(0, max_battery)]
    bounds.extend([(0, None)] * (count - len(bounds)))
    for month in range(nm):
        bounds[unmet_start + month] = (0, load[month])
    result = linprog(
        objective, A_ub=np.array(inequalities), b_ub=np.array(upper),
        A_eq=np.array(equalities), b_eq=np.array(rhs), bounds=bounds, method="highs",
    )
    diagnostic = {"status": int(result.status), "message": result.message,
                  "success": bool(result.success)}
    if not result.success:
        return None, diagnostic
    capacities = {tech: 0.0 for tech in TECHNOLOGIES}
    capacities.update({tech: max(0.0, float(result.x[i])) for i, tech in enumerate(selected)})
    return (capacities, max(0.0, float(result.x[battery_i]))), diagnostic


def optimize_configuration(
    dataset: dict, scenario: dict, technology_costs: dict, finance: dict,
    *, options: dict | None = None, evaluator: Callable | None = None,
) -> dict:
    """Search a bounded sample and rank hourly-feasible designs by LCOE/CAPEX.

    ``capacity_grid`` optionally specifies discrete axes by technology or
    ``battery_kwh``. Priority proposals are rounded upward to these axes. The
    candidate budget counts unique considered designs, including annual-energy
    pruning. It is an execution bound, not a promise to exhaust the search space.
    """
    options = options or {}
    if evaluator is None:
        from .config_eval import evaluate_configuration
        evaluator = evaluate_configuration
    demand = np.asarray(scenario["demand_profile_kw"], dtype=float)
    if demand.ndim != 1 or not len(demand) or not np.isfinite(demand).all() or (demand < 0).any():
        raise ValueError("demand_profile_kw must be a nonempty finite nonnegative vector")
    month_index = np.asarray(dataset["month_index"])
    if month_index.shape != demand.shape or not np.isfinite(month_index).all():
        raise ValueError("month_index must align with hourly demand")
    if ((month_index < 0) | (month_index > 11) | (month_index != month_index.astype(int))).any():
        raise ValueError("month_index must contain integer months from 0 to 11")
    for tech in TECHNOLOGIES:
        cf = np.asarray(dataset["capacity_factors"][tech], dtype=float)
        if cf.shape != demand.shape or not np.isfinite(cf).all() or ((cf < 0) | (cf > 1)).any():
            raise ValueError(f"Invalid hourly capacity factors for {tech}")
    selected = list(options.get("selected_technologies", TECHNOLOGIES))
    if len(selected) != len(set(selected)) or set(selected) - set(TECHNOLOGIES):
        raise ValueError("selected_technologies contains duplicate or unknown technologies")
    peak = float(demand.max(initial=0))
    maxima_input = options.get("max_capacities_kw", {})
    if set(maxima_input) - set(TECHNOLOGIES):
        raise ValueError("max_capacities_kw contains unknown technologies")
    maxima = {
        tech: _finite_nonnegative(maxima_input.get(tech, 10 * peak), f"max {tech}")
        if tech in selected else 0.0 for tech in TECHNOLOGIES
    }
    max_battery = _finite_nonnegative(options.get("max_battery_kwh", 50 * peak), "max_battery_kwh")
    budget = options.get("candidate_budget", 64)
    max_results = options.get("max_results", 5)
    if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= 256:
        raise ValueError("candidate_budget must be an integer from 1 to 256")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10:
        raise ValueError("max_results must be an integer from 1 to 10")
    epsilon = float(scenario["max_lpsp"])
    wind_fraction = float(scenario.get("min_wind_fraction", 0))
    if not np.isfinite(epsilon) or not 0 <= epsilon <= 1:
        raise ValueError("max_lpsp must be between 0 and 1")
    if not np.isfinite(wind_fraction) or not 0 <= wind_fraction <= 1:
        raise ValueError("min_wind_fraction must be between 0 and 1")
    explicit_grid = options.get("capacity_grid", {})
    if set(explicit_grid) - (set(TECHNOLOGIES) | {"battery_kwh"}):
        raise ValueError("capacity_grid contains unknown axes")
    limits = [maxima[tech] for tech in TECHNOLOGIES] + [max_battery]
    names = list(TECHNOLOGIES) + ["battery_kwh"]
    axes = []
    for name, limit in zip(names, limits):
        values = explicit_grid.get(name, [0.0, limit / 2, limit])
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError(f"capacity_grid[{name}] must be a nonempty list")
        axis = sorted({_finite_nonnegative(value, f"capacity_grid[{name}]") for value in values})
        if axis[-1] > limit + 1e-9:
            raise ValueError(f"capacity_grid[{name}] exceeds its capacity bound")
        axes.append(axis)
    proposal, lp_status = _monthly_proposal(
        dataset, scenario, technology_costs, finance, selected, maxima, max_battery,
    )
    diagnostics = {
        "lp_status": lp_status, "evaluated": 0, "pruned": 0, "infeasible": 0,
        "considered": 0, "truncated": False, "search_space_size": prod(map(len, axes)),
        "search_method": "monthly_highs_lp_and_bounded_candidates_with_hourly_filter",
        "global_optimum": False,
    }
    initial = [float(scenario["capacities_kw"].get(tech, 0)) for tech in TECHNOLOGIES]
    initial.append(float(scenario["battery_kwh"]))
    priorities = [initial]
    if proposal is not None:
        vector = [proposal[0][tech] for tech in TECHNOLOGIES] + [proposal[1]]
        # Place the LP ahead of input so budget=1 evaluates the sizing proposal.
        priorities.insert(0, vector)
        for scale in (1.1, 1.5, 2.0, 4.0):
            priorities.append([value * scale for value in vector[:-1]] + [vector[-1] * scale])
            priorities.append([value * scale for value in vector[:-1]] + [max_battery])
    priorities.extend([[0.0] * 7, limits])
    for index, limit in enumerate(limits[:-1]):
        if limit:
            vector = [0.0] * 7
            vector[index] = limit
            priorities.extend([vector, vector[:-1] + [max_battery]])
    seen, feasible = set(), []
    annual_cf = np.array([np.asarray(dataset["capacity_factors"][tech]).sum() for tech in TECHNOLOGIES])
    required = (1 - epsilon) * demand.sum()
    minimum_wind = wind_fraction * peak

    def normalized(values):
        result = []
        for name, value, limit, axis in zip(names, values, limits, axes):
            value = min(limit, max(0.0, float(value)))
            if name in explicit_grid:
                value = next((point for point in axis if point >= value - 1e-9), axis[-1])
            result.append(value)
        return tuple(round(value, 10) for value in result)

    def candidates():
        for values in priorities:
            yield normalized(values)
        yield from product(*axes)

    for vector in candidates():
        if vector in seen:
            continue
        if diagnostics["considered"] >= budget:
            diagnostics["truncated"] = True
            break
        seen.add(vector)
        diagnostics["considered"] += 1
        if vector[2] + vector[3] + 1e-8 < minimum_wind:
            diagnostics["infeasible"] += 1
            continue
        if np.dot(annual_cf, vector[:-1]) + 1e-8 < required:
            diagnostics["pruned"] += 1
            continue
        candidate = deepcopy(scenario)
        candidate["capacities_kw"] = dict(zip(TECHNOLOGIES, vector[:-1]))
        candidate["battery_kwh"] = vector[-1]
        result = evaluator(dataset, candidate, technology_costs, finance, fast=True)
        diagnostics["evaluated"] += 1
        metrics = result["metrics"]
        if result.get("feasible", False) and metrics["lpsp"] <= epsilon + 1e-8:
            feasible.append((result, candidate))
        else:
            diagnostics["infeasible"] += 1
    def ranking(item):
        economics = item[0]["economics"]
        lcoe = economics.get("lcoe")
        return (float(lcoe) if lcoe is not None and np.isfinite(lcoe) else float("inf"),
                float(economics["capex"]))
    feasible.sort(key=ranking)
    ranked = []
    for rank, (result, _) in enumerate(feasible[:max_results], 1):
        ranked.append({"rank": rank, "configuration": result["configuration"],
                       "metrics": result["metrics"], "economics": result["economics"],
                       "feasible": True})
    best = None
    if feasible:
        best = evaluator(dataset, feasible[0][1], technology_costs, finance, fast=False)
    return {"status": "feasible" if best is not None else "no_feasible_configuration",
            "best": best, "configurations": ranked, "diagnostics": diagnostics}
