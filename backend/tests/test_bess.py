"""Battery conservation, physical bounds, and cyclic-inventory tests."""

import numpy as np
import pytest

from app.engine.bess import dispatch_hourly


def assert_energy_conservation(result):
    previous_soc = np.concatenate(([result["initial_soc_kwh"]], result["soc_kwh"][:-1]))
    np.testing.assert_allclose(
        result["generation_kw"] + previous_soc,
        result["served_kw"] + result["curtailed_kw"] + result["soc_kwh"] + result["loss_kwh"],
        rtol=1e-11,
        atol=1e-10,
    )
    np.testing.assert_allclose(result["demand_kw"], result["served_kw"] + result["unmet_kw"])


def test_no_battery_direct_supply_and_reliability():
    result = dispatch_hourly([0, 2, 5], [1, 3, 2], 0)
    np.testing.assert_allclose(result["served_kw"], [0, 2, 2])
    np.testing.assert_allclose(result["unmet_kw"], [1, 1, 0])
    np.testing.assert_allclose(result["curtailed_kw"], [0, 0, 3])
    assert result["lpsp"] == pytest.approx(2 / 6)
    assert result["initial_soc_kwh"] == result["final_soc_kwh"] == 0
    assert_energy_conservation(result)


def test_conversion_losses_have_analytic_energy_balance():
    result = dispatch_hourly(
        [10, 0], [0, 10], 10, charge_efficiency=0.8, discharge_efficiency=0.5,
        depth_of_discharge=1, c_rate=1, self_discharge_per_hour=0, cyclic=False,
    )
    np.testing.assert_allclose(result["soc_kwh"], [8, 0])
    np.testing.assert_allclose(result["charge_kw"], [10, 0])
    np.testing.assert_allclose(result["discharge_kw"], [0, 4])
    np.testing.assert_allclose(result["loss_kwh"], [2, 4])
    np.testing.assert_allclose(result["unmet_kw"], [0, 6])
    assert_energy_conservation(result)


def test_self_discharge_occurs_before_dispatch():
    result = dispatch_hourly(
        [0], [4], 10, initial_soc_kwh=4, self_discharge_per_hour=0.25,
        discharge_efficiency=1, cyclic=False,
    )
    np.testing.assert_allclose(result["discharge_kw"], [3])
    np.testing.assert_allclose(result["loss_kwh"], [1])
    np.testing.assert_allclose(result["unmet_kw"], [1])
    assert_energy_conservation(result)


def test_energy_capacity_and_power_limits_are_both_enforced():
    result = dispatch_hourly(
        [10, 0], [0, 10], 2, depth_of_discharge=0.5, c_rate=0.5,
        charge_efficiency=1, discharge_efficiency=1,
        self_discharge_per_hour=0, cyclic=False,
    )
    np.testing.assert_allclose(result["soc_kwh"], [1, 0])
    np.testing.assert_allclose(result["curtailed_kw"], [9, 0])
    np.testing.assert_allclose(result["unmet_kw"], [0, 9])
    assert_energy_conservation(result)


def test_cyclic_boundary_cannot_supply_free_initial_energy():
    result = dispatch_hourly([0, 0, 0], 2, 10, initial_soc_kwh=5)
    assert result["initial_soc_kwh"] == pytest.approx(0)
    assert result["final_soc_kwh"] == pytest.approx(0)
    assert result["lpsp"] == 1
    np.testing.assert_array_equal(result["served_kw"], [0, 0, 0])
    assert_energy_conservation(result)


def test_cyclic_inventory_supports_load_before_generation_without_net_gift():
    result = dispatch_hourly(
        [0, 1], [1, 0], 2, depth_of_discharge=1, c_rate=1,
        charge_efficiency=1, discharge_efficiency=1, self_discharge_per_hour=0,
    )
    assert result["initial_soc_kwh"] == pytest.approx(1)
    assert result["final_soc_kwh"] == pytest.approx(1)
    assert result["lpsp"] == 0
    assert_energy_conservation(result)


def test_bisection_fallback_resolves_slow_fixed_point():
    result = dispatch_hourly(
        [0.001], [0], 1000, depth_of_discharge=1, c_rate=1,
        charge_efficiency=1, self_discharge_per_hour=1e-6,
    )
    assert result["initial_soc_kwh"] == pytest.approx(1000, abs=1e-5)
    assert result["final_soc_kwh"] == pytest.approx(result["initial_soc_kwh"], abs=1e-6)
    assert_energy_conservation(result)


def test_annual_dispatch_is_deterministic_and_respects_all_bounds():
    hours = np.arange(8760)
    generation = np.maximum(0, 12 * np.sin(2 * np.pi * (hours % 24) / 24))
    demand = 3 + (hours % 24 >= 18)
    result = dispatch_hourly(generation, demand, 30)
    repeated = dispatch_hourly(generation, demand, 30)
    for key in result:
        np.testing.assert_array_equal(result[key], repeated[key])
    assert result["initial_soc_kwh"] == pytest.approx(result["final_soc_kwh"], abs=1e-7)
    assert np.all(result["soc_kwh"] >= 0)
    assert np.all(result["soc_kwh"] <= 24 + 1e-12)
    assert np.all(result["charge_kw"] <= 15)
    assert np.all(result["discharge_kw"] <= 15)
    assert not np.any((result["charge_kw"] > 0) & (result["discharge_kw"] > 0))
    assert result["lpsp"] == pytest.approx(result["unmet_kw"].sum() / demand.sum())
    assert_energy_conservation(result)


def test_zero_demand_has_defined_zero_lpsp_and_no_mutation():
    source = np.array([1.0, 2.0])
    original = source.copy()
    result = dispatch_hourly(source, 0, 1)
    assert result["lpsp"] == 0
    np.testing.assert_array_equal(source, original)
    assert_energy_conservation(result)


@pytest.mark.parametrize("efficiency", [1e-310, np.nextafter(0.0, 1.0)])
@pytest.mark.parametrize("cyclic", [True, False])
def test_tiny_positive_discharge_efficiency_is_finite_and_conserves_energy(efficiency, cyclic):
    result = dispatch_hourly(
        [1, 0], [0, 1], 1,
        charge_efficiency=1,
        discharge_efficiency=efficiency,
        depth_of_discharge=1,
        c_rate=1,
        cyclic=cyclic,
    )
    for value in result.values():
        assert np.all(np.isfinite(value))
    assert_energy_conservation(result)
    if cyclic:
        assert result["initial_soc_kwh"] == pytest.approx(result["final_soc_kwh"], abs=1e-10)
    # With effectively zero useful output, energy leaves storage as losses.
    assert result["loss_kwh"].sum() == pytest.approx(1.0)


@pytest.mark.parametrize("generation,demand,capacity,kwargs", [
    ([], [], 1, {}),
    ([1, 2], [1, 2, 3], 1, {}),
    ([[1]], [1], 1, {}),
    ([-1], [1], 1, {}),
    ([np.nan], [1], 1, {}),
    ([1], [np.inf], 1, {}),
    ([1], [-1], 1, {}),
    ([1], [1], -1, {}),
    ([1], [1], 1, {"charge_efficiency": 0}),
    ([1], [1], 1, {"discharge_efficiency": 1.1}),
    ([1], [1], 1, {"depth_of_discharge": 1.1}),
    ([1], [1], 1, {"c_rate": -0.1}),
    ([1], [1], 1, {"self_discharge_per_hour": -0.1}),
    ([1], [1], 1, {"self_discharge_per_hour": 1.1}),
    ([1], [1], 1, {"initial_soc_kwh": 1}),
    ([1], [1], 1, {"cyclic": "yes"}),
])
def test_invalid_profiles_and_parameters_raise(generation, demand, capacity, kwargs):
    with pytest.raises(ValueError):
        dispatch_hourly(generation, demand, capacity, **kwargs)
