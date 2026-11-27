"""Deterministic resource-to-capacity-factor models from the BlueGrid reference.

These simplified screening models do not establish site feasibility. In particular,
OTEC needs measured sea temperatures; ``rolling_sst_proxy`` is an explicitly named
air-temperature proxy from the reference, rather than a measured SST dataset.
"""

import numpy as np


def _finite(value, name, *, nonnegative=False):
    result = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    if nonnegative and np.any(result < 0):
        raise ValueError(f"{name} must be nonnegative")
    return result


def _parameter(value, name, *, minimum=0.0, maximum=None, positive=False):
    result = _finite(value, name)
    if result.ndim != 0:
        raise ValueError(f"{name} must be a scalar")
    result = float(result)
    if result < minimum or (positive and result <= minimum):
        raise ValueError(f"{name} is outside its valid range")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} is outside its valid range")
    return result


def solar_capacity_factor(
    ghi_w_m2,
    air_temperature_c,
    performance_ratio=0.80,
    temperature_coefficient=0.004,
):
    """PV availability with a 25 C temperature baseline (reference p. 4).

    Inputs may be scalars or broadcast-compatible NumPy arrays. GHI is W/m2;
    negative temperatures are valid, while negative irradiance is rejected.
    """
    ghi = _finite(ghi_w_m2, "ghi_w_m2", nonnegative=True)
    temperature = _finite(air_temperature_c, "air_temperature_c")
    ratio = _parameter(performance_ratio, "performance_ratio", maximum=1.0)
    coefficient = _parameter(temperature_coefficient, "temperature_coefficient")
    derating = np.maximum(0.0, 1.0 - coefficient * np.maximum(0.0, temperature - 25.0))
    return np.clip((ghi / 1000.0) * ratio * derating, 0.0, 1.0)


def wind_capacity_factor(
    wind_speed_m_s,
    cut_in=3.0,
    rated=11.0,
    cut_out=25.0,
    loss_fraction=0.12,
):
    """Cubic wind curve, rated through the cut-out boundary (reference pp. 4-5)."""
    speed = _finite(wind_speed_m_s, "wind_speed_m_s", nonnegative=True)
    cut_in = _parameter(cut_in, "cut_in")
    rated = _parameter(rated, "rated", positive=True)
    cut_out = _parameter(cut_out, "cut_out", positive=True)
    loss = _parameter(loss_fraction, "loss_fraction", maximum=1.0)
    if not cut_in < rated <= cut_out:
        raise ValueError("wind thresholds require cut_in < rated <= cut_out")
    # Clip before cubing to keep extreme, finite resource inputs numerically safe.
    bounded = np.clip(speed, cut_in, rated)
    curve = (bounded**3 - cut_in**3) / (rated**3 - cut_in**3)
    operating = (speed >= cut_in) & (speed <= cut_out)
    return np.clip(np.where(operating, curve * (1.0 - loss), 0.0), 0.0, 1.0)


def otec_capacity_factor(
    surface_temperature_c,
    deep_temperature_c=7.0,
    availability=0.92,
    nominal_delta_c=22.0,
    parasitic_fraction=0.30,
):
    """Simplified OTEC screening curve, including pumping load (reference p. 5).

    Temperatures are degrees Celsius. A nonpositive thermal gradient yields no
    output. The default 7 C deep temperature is a reference assumption, not a
    globally applicable ocean temperature.
    """
    surface = _finite(surface_temperature_c, "surface_temperature_c")
    deep = _finite(deep_temperature_c, "deep_temperature_c")
    availability = _parameter(availability, "availability", maximum=1.0)
    nominal_delta = _parameter(nominal_delta_c, "nominal_delta_c", positive=True)
    parasitic = _parameter(parasitic_fraction, "parasitic_fraction", maximum=1.0)
    if parasitic == 1.0:
        raise ValueError("parasitic_fraction must be less than 1")
    delta = np.maximum(0.0, surface - deep)
    # Values beyond the saturation point return one after clipping; bounding the
    # normalized gradient avoids overflow for unrealistic but finite inputs.
    normalized = np.clip(delta / nominal_delta, 0.0, 1e6)
    net = normalized**2 - parasitic * normalized
    return np.clip(net * availability / (1.0 - parasitic), 0.0, 1.0)


def wave_capacity_factor(
    significant_wave_height_m,
    peak_period_s,
    rated_flux_kw_m=25.0,
    availability=0.85,
):
    """Deep-water wave flux approximation and operating envelope (reference p. 5)."""
    height = _finite(significant_wave_height_m, "significant_wave_height_m", nonnegative=True)
    period = _finite(peak_period_s, "peak_period_s", nonnegative=True)
    rated_flux = _parameter(rated_flux_kw_m, "rated_flux_kw_m", positive=True)
    availability = _parameter(availability, "availability", maximum=1.0)
    operating = (height >= 0.5) & (height <= 4.0)
    # Heights outside the operating envelope cannot contribute generation.
    bounded_height = np.where(operating, height, 0.0)
    with np.errstate(over="ignore"):
        flux_ratio = 0.49 * bounded_height**2 * period / rated_flux
    return np.clip(np.where(operating, np.minimum(1.0, flux_ratio) * availability, 0.0), 0.0, 1.0)


def rolling_sst_proxy(air_temperature_c, window=24):
    """Trailing mean air temperature as an SST proxy, with partial startup windows.

    A scalar stays scalar. A series must be one-dimensional and hourly; the
    caller is responsible for regular timestamps and data provenance.
    """
    temperature = _finite(air_temperature_c, "air_temperature_c")
    if isinstance(window, (bool, np.bool_)) or not isinstance(window, (int, np.integer)) or window < 1:
        raise ValueError("window must be a positive integer")
    if temperature.ndim == 0:
        return np.float64(temperature)
    if temperature.ndim != 1:
        raise ValueError("air_temperature_c must be a scalar or one-dimensional series")
    if temperature.size == 0:
        return temperature.copy()
    cumulative = np.concatenate(([0.0], np.cumsum(temperature, dtype=float)))
    end = np.arange(1, temperature.size + 1)
    start = np.maximum(0, end - window)
    return (cumulative[end] - cumulative[start]) / (end - start)
