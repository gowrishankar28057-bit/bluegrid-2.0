"""Capacity search mechanics and dimensional monthly-LP checks."""
from copy import deepcopy

import numpy as np
import pytest

from app.engine.optimizer import TECHNOLOGIES, optimize_configuration


@pytest.fixture
def inputs():
    factors = {tech: np.zeros(24) for tech in TECHNOLOGIES}
    factors["onshore_solar"] = np.ones(24)
    dataset = {"id": "synthetic-test", "synthetic": True,
               "capacity_factors": factors, "month_index": np.zeros(24, dtype=int)}
    scenario = {
        "capacities_kw": {tech: 20.0 if tech == "onshore_solar" else 0.0 for tech in TECHNOLOGIES},
        "battery_kwh": 0.0, "demand_profile_kw": np.full(24, 10.0),
        "max_lpsp": 0.0, "min_wind_fraction": 0.0,
        "battery": {"charge_efficiency": .95, "discharge_efficiency": .95,
                    "depth_of_discharge": .8, "c_rate": .5, "self_discharge_per_hour": .015},
    }
    costs = {tech: {"capex_per_kw": 100.0, "opex_per_kw_year": 0.0,
                    "lifetime_years": 20} for tech in TECHNOLOGIES}
    costs["battery"] = {"capex_per_kwh": 100.0, "opex_per_kwh_year": 0.0,
                        "lifetime_years": 10, "replacement_fraction": 1.0}
    finance = {"real_discount_rate": .05, "general_inflation": .04,
               "opex_escalation": .04, "diesel_escalation": .05,
               "battery_cost_escalation": -.02, "project_years": 25,
               "diesel_cost_per_kwh": 25.0, "battery_subsidy_fraction": 0.0,
               "currency": "INR"}
    return dataset, scenario, costs, finance


def no_storage_evaluator(calls=None):
    """Hourly supply checker isolates search mechanics from battery physics."""
    def evaluate(dataset, scenario, costs, finance, *, fast=False):
        if calls is not None:
            calls.append((deepcopy(scenario["capacities_kw"]), scenario["battery_kwh"], fast))
        generation = sum(np.asarray(dataset["capacity_factors"][tech]) * capacity
                         for tech, capacity in scenario["capacities_kw"].items())
        demand = np.asarray(scenario["demand_profile_kw"])
        served = np.minimum(generation, demand).sum()
        unmet = demand.sum() - served
        lpsp = float(unmet / demand.sum()) if demand.sum() else 0.0
        capex = 100 * (sum(scenario["capacities_kw"].values()) + scenario["battery_kwh"])
        return {
            "configuration": {"capacities_kw": deepcopy(scenario["capacities_kw"]),
                              "battery_kwh": scenario["battery_kwh"]},
            "metrics": {"lpsp": lpsp, "demand_energy_kwh": float(demand.sum()),
                        "energy_served_kwh": float(served), "unmet_energy_kwh": float(unmet)},
            "economics": {"lcoe": capex / served if served else None, "capex": capex,
                          "annualized_cost": capex / 20},
            "feasible": lpsp <= scenario["max_lpsp"] + 1e-9,
            **({} if fast else {"hourly": {"generation_kw": generation.tolist()}}),
        }
    return evaluate


def solar_options(**changes):
    return {"selected_technologies": ["onshore_solar"],
            "max_capacities_kw": {"onshore_solar": 20}, "max_battery_kwh": 0,
            **changes}


def test_monthly_lp_sizes_constant_supply_in_kw(inputs):
    calls = []
    result = optimize_configuration(*inputs, options=solar_options(), evaluator=no_storage_evaluator(calls))
    assert result["status"] == "feasible"
    assert result["diagnostics"]["lp_status"]["success"]
    assert result["best"]["configuration"]["capacities_kw"]["onshore_solar"] == pytest.approx(10)
    assert result["best"]["metrics"]["energy_served_kwh"] == pytest.approx(240)
    assert "hourly" in result["best"]
    assert all("hourly" not in row for row in result["configurations"])
    assert calls[-1][2] is False
    assert result["diagnostics"]["global_optimum"] is False


def test_annual_pruning_avoids_evaluator_for_impossible_energy(inputs):
    dataset, scenario, costs, finance = inputs
    calls = []
    result = optimize_configuration(
        dataset, scenario, costs, finance,
        options=solar_options(max_capacities_kw={"onshore_solar": 0}),
        evaluator=no_storage_evaluator(calls),
    )
    assert result["status"] == "no_feasible_configuration"
    assert result["best"] is None
    assert result["diagnostics"]["evaluated"] == 0
    assert result["diagnostics"]["pruned"] == 1
    assert calls == []


def test_monthly_lp_success_does_not_bypass_hourly_reliability(inputs):
    dataset, scenario, costs, finance = inputs
    dataset["capacity_factors"]["onshore_solar"] = np.tile([0.0, 1.0], 12)
    result = optimize_configuration(
        dataset, scenario, costs, finance,
        options=solar_options(max_capacities_kw={"onshore_solar": 30}),
        evaluator=no_storage_evaluator(),
    )
    assert result["diagnostics"]["lp_status"]["success"]
    assert result["status"] == "no_feasible_configuration"
    assert result["diagnostics"]["infeasible"] > 0


def test_minimum_combined_wind_capacity_cannot_be_ignored(inputs):
    dataset, scenario, costs, finance = inputs
    scenario["min_wind_fraction"] = .2
    result = optimize_configuration(*inputs, options=solar_options(), evaluator=no_storage_evaluator())
    assert result["status"] == "no_feasible_configuration"
    assert result["diagnostics"]["evaluated"] == 0
    assert not result["diagnostics"]["lp_status"]["success"]


def test_budget_discrete_grid_and_determinism(inputs):
    options = solar_options(candidate_budget=2, capacity_grid={"onshore_solar": [0, 10, 20]})
    calls_a, calls_b = [], []
    a = optimize_configuration(*inputs, options=options, evaluator=no_storage_evaluator(calls_a))
    b = optimize_configuration(*inputs, options=options, evaluator=no_storage_evaluator(calls_b))
    assert a == b
    assert calls_a == calls_b
    assert a["diagnostics"]["truncated"]
    assert a["diagnostics"]["considered"] == 2
    assert a["diagnostics"]["evaluated"] <= 2
    assert all(call[0]["onshore_solar"] in [0, 10, 20] for call in calls_a)


def test_zero_demand_and_zero_capacity_are_defined(inputs):
    dataset, scenario, costs, finance = inputs
    scenario["demand_profile_kw"] = np.zeros(24)
    scenario["capacities_kw"] = {tech: 0.0 for tech in TECHNOLOGIES}
    result = optimize_configuration(dataset, scenario, costs, finance, evaluator=no_storage_evaluator())
    assert result["status"] == "feasible"
    assert result["best"]["metrics"]["lpsp"] == 0
    assert result["best"]["economics"]["lcoe"] is None


def test_month_hour_counts_preserve_annual_energy(inputs):
    dataset, scenario, costs, finance = inputs
    # Unequal represented-month durations catch accidental repeated hour factors.
    dataset["month_index"] = np.array([0] * 8 + [1] * 16)
    scenario["demand_profile_kw"] = np.array([5.0] * 8 + [10.0] * 16)
    result = optimize_configuration(*inputs, options=solar_options(), evaluator=no_storage_evaluator())
    assert result["best"]["configuration"]["capacities_kw"]["onshore_solar"] == pytest.approx(10)
    assert result["best"]["metrics"]["demand_energy_kwh"] == pytest.approx(200)


@pytest.mark.parametrize("options", [
    {"candidate_budget": 0}, {"candidate_budget": 257}, {"candidate_budget": True},
    {"max_results": 11}, {"selected_technologies": ["unknown"]},
    {"selected_technologies": ["otec", "otec"]},
    {"capacity_grid": {"onshore_solar": []}},
    {"capacity_grid": {"onshore_solar": [float("nan")]}},
    {"capacity_grid": {"onshore_solar": [201]}},
    {"max_battery_kwh": -1},
])
def test_invalid_search_options_fail_explicitly(inputs, options):
    with pytest.raises(ValueError):
        optimize_configuration(*inputs, options=options, evaluator=no_storage_evaluator())


def test_inputs_are_not_mutated(inputs):
    dataset, scenario, costs, finance = inputs
    capacities = deepcopy(scenario["capacities_kw"])
    battery = deepcopy(scenario["battery"])
    demand = scenario["demand_profile_kw"].copy()
    options = solar_options(capacity_grid={"onshore_solar": [0, 10, 20]})
    before_options = deepcopy(options)
    optimize_configuration(*inputs, options=options, evaluator=no_storage_evaluator())
    assert scenario["capacities_kw"] == capacities
    assert scenario["battery"] == battery
    np.testing.assert_array_equal(scenario["demand_profile_kw"], demand)
    assert options == before_options


def test_real_evaluator_returns_hourly_verified_best(inputs):
    dataset, scenario, costs, finance = inputs
    dataset["timestamps"] = [f"2025-01-01T{hour:02d}:00:00Z" for hour in range(24)]
    result = optimize_configuration(dataset, scenario, costs, finance, options=solar_options())
    best = result["best"]
    assert result["status"] == "feasible"
    assert best["metrics"]["lpsp"] == pytest.approx(0)
    assert best["metrics"]["energy_served_kwh"] == pytest.approx(240)
    assert len(best["hourly"]["soc_kwh"]) == 24
    assert best["storage_boundary"]["initial_soc_kwh"] == pytest.approx(
        best["storage_boundary"]["final_soc_kwh"], abs=1e-8)
