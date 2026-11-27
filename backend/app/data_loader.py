"""Deterministic demo resources and strict hourly dataset ingestion."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import numpy as np

from .config import LOCATIONS, TECHNOLOGIES
from .engine.generation import (
    solar_capacity_factor, wind_capacity_factor, otec_capacity_factor,
    wave_capacity_factor, rolling_sst_proxy,
)


def numeric_series(values, name, *, length=None, maximum=None, minimum=0.0):
    if not isinstance(values, (list, tuple, np.ndarray)):
        raise ValueError(f"{name} must be an array")
    if any(isinstance(value, (bool, str)) for value in values):
        raise ValueError(f"{name} must contain numbers")
    try:
        array = np.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain numbers") from exc
    if array.ndim != 1 or not len(array) or (length is not None and len(array) != length):
        raise ValueError(f"{name} has an invalid length")
    if not np.all(np.isfinite(array)) or np.any(array < minimum):
        raise ValueError(f"{name} must contain finite values >= {minimum}")
    if maximum is not None and np.any(array > maximum):
        raise ValueError(f"{name} must contain values <= {maximum}")
    return array


def calendar(timestamps):
    if not isinstance(timestamps, list) or len(timestamps) not in (8760, 8784):
        raise ValueError("timestamps must describe a complete hourly calendar year (8760 or 8784 hours)")
    try:
        dates = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("timestamps must be ISO 8601 strings") from exc
    if any(date.utcoffset() != timedelta(0) for date in dates):
        raise ValueError("timestamps must use UTC (Z or +00:00)")
    start = datetime(dates[0].year, 1, 1, tzinfo=timezone.utc)
    stop = datetime(dates[0].year + 1, 1, 1, tzinfo=timezone.utc)
    if dates[0] != start or dates[-1] + timedelta(hours=1) != stop:
        raise ValueError("timestamps must cover January 1 through December 31 of one year")
    if any(b - a != timedelta(hours=1) for a, b in zip(dates, dates[1:])):
        raise ValueError("timestamps must be contiguous, unique hourly UTC values")
    return np.array([date.month - 1 for date in dates], dtype=int)


def convert_weather(weather, length):
    required = {"ghi_w_m2", "air_temperature_c", "wind_speed_m_s", "significant_wave_height_m", "peak_period_s"}
    allowed = required | {"surface_temperature_c", "deep_temperature_c"}
    if not isinstance(weather, dict) or not required <= weather.keys() or weather.keys() - allowed:
        raise ValueError(f"weather requires {sorted(required)} and optional surface_temperature_c/deep_temperature_c")
    fields = {
        key: numeric_series(value, key, length=length, minimum=-80.0 if "temperature" in key else 0.0)
        for key, value in weather.items()
    }
    proxy = "surface_temperature_c" not in fields
    surface = fields.get("surface_temperature_c", rolling_sst_proxy(fields["air_temperature_c"]))
    deep = fields.get("deep_temperature_c", 7.0)
    solar = solar_capacity_factor(fields["ghi_w_m2"], fields["air_temperature_c"])
    wind = wind_capacity_factor(fields["wind_speed_m_s"])
    factors = {
        "floating_solar": solar, "onshore_solar": solar.copy(),
        "onshore_wind": wind, "offshore_wind": wind.copy(),
        "otec": otec_capacity_factor(surface, deep_temperature_c=deep),
        "wave": wave_capacity_factor(fields["significant_wave_height_m"], fields["peak_period_s"]),
    }
    warnings = ["Air temperature with a causal 24-hour rolling mean is being used as an SST proxy."] if proxy else []
    return factors, warnings


def parse_resource_data(data, location_id="custom"):
    if not isinstance(data, dict) or set(data) - {"timestamps", "capacity_factors", "weather", "provenance"}:
        raise ValueError("resource_data contains unsupported fields")
    timestamps = data.get("timestamps")
    months = calendar(timestamps)
    provenance = data.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
        raise ValueError("resource_data.provenance.source is required")
    if not isinstance(provenance.get("synthetic"), bool):
        raise ValueError("resource_data.provenance.synthetic must be a boolean")
    if len(provenance["source"]) > 2000:
        raise ValueError("provenance.source is too long")
    if ("weather" in data) == ("capacity_factors" in data):
        raise ValueError("provide exactly one of weather or capacity_factors")
    warnings = []
    if "weather" in data:
        factors, warnings = convert_weather(data["weather"], len(timestamps))
    else:
        supplied = data["capacity_factors"]
        if not isinstance(supplied, dict) or not supplied or set(supplied) - set(TECHNOLOGIES):
            raise ValueError("capacity_factors must map supported technology names to hourly arrays")
        factors = {
            name: numeric_series(supplied[name], name, length=len(timestamps), maximum=1.0)
            if name in supplied else np.zeros(len(timestamps))
            for name in TECHNOLOGIES
        }
    return {"id": "custom", "location_id": location_id, "name": "User-provided hourly resources",
            "timestamps": tuple(timestamps), "month_index": months, "capacity_factors": factors,
            "synthetic": provenance["synthetic"], "source": provenance["source"],
            "warnings": warnings, "data_validation": "Structure checked; source and physical accuracy are not independently verified."}


@lru_cache(maxsize=2)
def demo_dataset(location_id="lakshadweep"):
    if location_id not in LOCATIONS:
        raise ValueError("location_id must be lakshadweep or brest unless resource_data is provided")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = [start + timedelta(hours=hour) for hour in range(8760)]
    hours = np.arange(8760, dtype=float)
    season = np.cos(2 * np.pi * (hours / 24 - 200) / 365)
    sunlight = np.maximum(0.0, np.sin(np.pi * ((hours % 24) - 6) / 12))
    tropical = location_id == "lakshadweep"
    temperature = (28.0 + 1.5 * season) if tropical else (12.0 + 7.0 * season)
    weather = {
        "ghi_w_m2": (850 * sunlight * (0.85 + 0.1 * season)).tolist(),
        "air_temperature_c": temperature.tolist(),
        "wind_speed_m_s": (7.0 + 2 * np.sin(2 * np.pi * hours / (24 * 9)) + (1.5 if tropical else -1.5) * season).tolist(),
        "significant_wave_height_m": (1.5 + 0.5 * np.sin(2 * np.pi * hours / (24 * 6))).tolist(),
        "peak_period_s": (7.0 + np.sin(2 * np.pi * hours / (24 * 8))).tolist(),
    }
    factors, warnings = convert_weather(weather, len(hours))
    for factor in factors.values():
        factor.setflags(write=False)
    return {"id": f"demo-{location_id}-2025", "location_id": location_id, "name": LOCATIONS[location_id]["name"],
            "timestamps": tuple(date.isoformat().replace("+00:00", "Z") for date in dates),
            "month_index": np.array([date.month - 1 for date in dates]), "capacity_factors": factors,
            "synthetic": True, "source": "Deterministic synthetic annual demonstration; no measured site data.",
            "warnings": warnings, "data_validation": "Synthetic interface and engine demonstration only."}
