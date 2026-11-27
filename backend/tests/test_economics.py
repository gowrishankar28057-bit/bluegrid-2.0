import math

import pytest

from app.engine.economics import (
    annual_cost_coefficients,
    capital_recovery_factor,
    evaluate_economics,
    nominal_discount_rate,
    present_value_escalating,
)


@pytest.fixture
def finance():
    return {
        "real_discount_rate": 0.05,
        "general_inflation": 0.04,
        "opex_escalation": 0.04,
        "diesel_escalation": 0.05,
        "battery_cost_escalation": -0.02,
        "project_years": 25,
        "diesel_cost_per_kwh": 25,
        "battery_subsidy_fraction": 0,
        "currency": "INR",
    }


@pytest.fixture
def costs():
    return {
        "solar": {"capex_per_kw": 50000, "opex_per_kw_year": 1000, "lifetime_years": 20},
        "battery": {"capex_per_kwh": 15000, "opex_per_kwh_year": 100, "lifetime_years": 10, "replacement_fraction": 1},
    }


def test_nominal_rate_and_zero_rate_recovery():
    assert nominal_discount_rate(0.05, 0.04) == pytest.approx(0.092)
    assert capital_recovery_factor(0, 25) == 0.04
    assert capital_recovery_factor(1e-12, 25) == pytest.approx(0.04, rel=1e-10)


@pytest.mark.parametrize("escalation,discount", [(0, 0), (0.04, 0.092), (0.05, 0.05), (0.0500000000001, 0.05), (-0.02, 0.08), (0, -0.1)])
def test_growing_annuity_matches_explicit_end_year_cash_flows(escalation, discount):
    expected = math.fsum(100 * (1 + escalation) ** (year - 1) / (1 + discount) ** year for year in range(1, 26))
    assert present_value_escalating(100, escalation, discount, 25) == pytest.approx(expected, rel=1e-12)


def test_equal_escalation_discount_limit_has_no_extra_first_year_escalation():
    assert present_value_escalating(100, 0.05, 0.05, 10) == pytest.approx(1000 / 1.05)
    assert present_value_escalating(100, 0.1, 0.2, 1) == pytest.approx(100 / 1.2)


def test_zero_rate_project_replacements_subsidy_and_boundary(costs, finance):
    finance.update(real_discount_rate=0, general_inflation=0, opex_escalation=0, diesel_escalation=0, battery_cost_escalation=0, battery_subsidy_fraction=0.2, project_years=20)
    result = evaluate_economics({"solar": 2}, 3, 10000, 100, costs, finance)
    # A 20-year solar asset has no replacement at project closure; BESS is replaced once.
    capex = 2 * 50000 + 3 * 15000
    net_capex = capex - 3 * 15000 * 0.2
    annual_opex = 2 * 1000 + 3 * 100
    npv = net_capex + 3 * 15000 + 20 * annual_opex
    assert result["capex"] == capex
    assert result["net_capex"] == net_capex
    assert result["opex_year_one"] == annual_opex
    assert result["project_npv"] == pytest.approx(npv)
    assert result["annualized_cost"] == pytest.approx(npv / 20)
    assert result["diesel_backup_cost"] == pytest.approx(2500)
    assert result["lcoe"] == pytest.approx(npv / 20 / 10000)
    assert result["cost_of_service"] == pytest.approx((npv / 20 + 2500) / 10100)


def test_battery_replacement_deflation_uses_absolute_replacement_year(costs, finance):
    result = evaluate_economics({}, 1, 100, 0, costs, finance)
    nominal = nominal_discount_rate(0.05, 0.04)
    replacements = sum(15000 * 0.98**year / (1 + nominal) ** year for year in (10, 20))
    opex = sum(100 * 1.04 ** (year - 1) / (1 + nominal) ** year for year in range(1, 26))
    assert result["project_npv"] == pytest.approx(15000 + replacements + opex)


def test_lp_cost_coefficients_match_evaluated_system_cost(costs, finance):
    coefficients = annual_cost_coefficients(costs, finance)
    result = evaluate_economics({"solar": 3.5}, 8.25, 5000, 50, costs, finance)
    assert result["annualized_cost"] == coefficients["solar"] * 3.5 + coefficients["battery"] * 8.25


def test_zero_generation_and_zero_demand_are_defined_without_nans(costs, finance):
    result = evaluate_economics({}, 0, 0, 100, costs, finance)
    assert result["lcoe"] is None
    assert result["cost_of_service"] > 0
    assert result["annualized_cost"] == 0
    empty = evaluate_economics({}, 0, 0, 0, costs, finance)
    assert empty["lcoe"] is None
    assert empty["cost_of_service"] is None
    assert all(value is None or isinstance(value, str) or math.isfinite(value) for value in empty.values())


@pytest.mark.parametrize("rate", [-1, -2, float("nan"), float("inf"), True])
def test_invalid_rates_are_rejected(rate):
    with pytest.raises(ValueError):
        capital_recovery_factor(rate, 25)


@pytest.mark.parametrize("years", [0, -1, 2.5, True, float("inf")])
def test_invalid_years_are_rejected(years):
    with pytest.raises(ValueError):
        present_value_escalating(100, 0, 0, years)


@pytest.mark.parametrize("capacity", [-1, float("nan"), float("inf"), True])
def test_invalid_capacity_rejected(capacity, costs, finance):
    with pytest.raises(ValueError):
        evaluate_economics({"solar": capacity}, 0, 100, 0, costs, finance)


def test_invalid_cost_lifetime_subsidy_unknown_technology_rejected(costs, finance):
    costs["solar"]["lifetime_years"] = 2.5
    with pytest.raises(ValueError):
        annual_cost_coefficients(costs, finance)
    costs["solar"]["lifetime_years"] = 20
    costs["solar"]["capex_per_kw"] = -1
    with pytest.raises(ValueError):
        annual_cost_coefficients(costs, finance)
    costs["solar"]["capex_per_kw"] = 50000
    finance["battery_subsidy_fraction"] = 1.01
    with pytest.raises(ValueError):
        annual_cost_coefficients(costs, finance)
    finance["battery_subsidy_fraction"] = 0
    with pytest.raises(ValueError):
        evaluate_economics({"unknown": 1}, 0, 100, 0, costs, finance)


def test_overflow_raises_instead_of_returning_infinity():
    with pytest.raises(ValueError):
        present_value_escalating(1e308, 1, 0, 100)
