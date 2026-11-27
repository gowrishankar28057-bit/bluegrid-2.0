"""Analytic checks for the resource conversion models."""

import numpy as np
import pytest

from app.engine.generation import (
    otec_capacity_factor,
    rolling_sst_proxy,
    solar_capacity_factor,
    wave_capacity_factor,
    wind_capacity_factor,
)


def test_solar_reference_values_and_broadcasting():
    np.testing.assert_allclose(
        solar_capacity_factor([0, 1000, 1000], [25, 25, 35]),
        [0, 0.8, 0.768],
    )
    np.testing.assert_allclose(solar_capacity_factor([500, 1000], 10), [0.4, 0.8])
    assert solar_capacity_factor(10000, 25) == 1
    assert solar_capacity_factor(1000, 500) == 0


def test_wind_curve_boundaries_and_losses():
    speeds = [0, 2.99, 3, 7, 11, 25, 25.01]
    expected = [0, 0, 0, ((7**3 - 3**3) / (11**3 - 3**3)) * 0.88, 0.88, 0.88, 0]
    np.testing.assert_allclose(wind_capacity_factor(speeds), expected)
    assert wind_capacity_factor(11, loss_fraction=0) == 1


def test_otec_reference_nominal_gradient_and_cutoff():
    np.testing.assert_allclose(otec_capacity_factor([0, 7, 10, 29, 60]), [0, 0, 0, 0.92, 1])
    gradient_ratio = (24 - 7) / 22
    expected = (gradient_ratio**2 - 0.3 * gradient_ratio) * 0.92 / 0.70
    assert otec_capacity_factor(24) == pytest.approx(expected)
    np.testing.assert_allclose(otec_capacity_factor([29, 30], [7, 8]), [0.92, 0.92])


def test_wave_flux_and_operating_envelope():
    np.testing.assert_allclose(
        wave_capacity_factor([0.49, 0.5, 1, 4, 4.01], 8),
        [0, 0.49 * 0.5**2 * 8 / 25 * 0.85, 0.49 * 8 / 25 * 0.85, 0.85, 0],
    )
    assert wave_capacity_factor(2, 0) == 0


def test_rolling_temperature_proxy_uses_partial_startup_windows():
    np.testing.assert_allclose(rolling_sst_proxy([10, 20, 30, 40], window=3), [10, 15, 20, 30])
    np.testing.assert_allclose(rolling_sst_proxy([1, 2], window=24), [1, 1.5])
    assert rolling_sst_proxy(-2) == -2


@pytest.mark.parametrize("function,args,kwargs", [
    (solar_capacity_factor, (-1, 25), {}),
    (solar_capacity_factor, (1000, np.nan), {}),
    (solar_capacity_factor, (1000, 25), {"performance_ratio": 1.1}),
    (solar_capacity_factor, (1000, 25), {"temperature_coefficient": -0.1}),
    (wind_capacity_factor, (-1,), {}),
    (wind_capacity_factor, (np.inf,), {}),
    (wind_capacity_factor, (5,), {"rated": 3}),
    (wind_capacity_factor, (5,), {"cut_out": 10}),
    (wind_capacity_factor, (5,), {"loss_fraction": -0.1}),
    (otec_capacity_factor, (np.inf,), {}),
    (otec_capacity_factor, (25,), {"nominal_delta_c": 0}),
    (otec_capacity_factor, (25,), {"parasitic_fraction": 1}),
    (wave_capacity_factor, (-1, 8), {}),
    (wave_capacity_factor, (1, -1), {}),
    (wave_capacity_factor, (1, np.nan), {}),
    (wave_capacity_factor, (1, 8), {"rated_flux_kw_m": 0}),
    (rolling_sst_proxy, ([10, 20],), {"window": 0}),
    (rolling_sst_proxy, ([10, 20],), {"window": 1.5}),
    (rolling_sst_proxy, ([[10, 20]],), {}),
])
def test_invalid_resources_and_parameters_raise(function, args, kwargs):
    with pytest.raises(ValueError):
        function(*args, **kwargs)
