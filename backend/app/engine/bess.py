"""Hourly battery dispatch with explicit energy accounting and cyclic boundaries."""

import numpy as np


def _scalar(value, name, *, minimum=0.0, maximum=None, positive=False):
    array = np.asarray(value, dtype=float)
    if array.ndim != 0 or not np.isfinite(array):
        raise ValueError(f"{name} must be a finite scalar")
    value = float(array)
    if value < minimum or (positive and value <= minimum):
        raise ValueError(f"{name} is outside its valid range")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} is outside its valid range")
    return value


def _profiles(generation_kw, demand_kw):
    generation = np.asarray(generation_kw, dtype=float)
    demand = np.asarray(demand_kw, dtype=float)
    if generation.ndim > 1 or demand.ndim > 1:
        raise ValueError("generation_kw and demand_kw must be scalars or one-dimensional series")
    try:
        generation, demand = np.broadcast_arrays(generation, demand)
    except ValueError as exc:
        raise ValueError("generation_kw and demand_kw must have compatible lengths") from exc
    generation = np.atleast_1d(generation).astype(float, copy=True)
    demand = np.atleast_1d(demand).astype(float, copy=True)
    if generation.size == 0:
        raise ValueError("hourly profiles must not be empty")
    for values, name in ((generation, "generation_kw"), (demand, "demand_kw")):
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError(f"{name} must contain finite nonnegative values")
    return generation, demand


def _cyclic_initial_soc(changes, usable_capacity, retention):
    """Find the smallest cyclic inventory, without gifting initial battery energy.

    The annual map is monotone and nonexpansive: each hourly map is a clipped
    affine transformation. Fixed-point iteration from zero finds the lowest
    root; bisection handles slow convergence in nearly lossless short profiles.
    """
    if usable_capacity == 0.0:
        return 0.0
    tolerance = 1e-10 * max(1.0, usable_capacity)

    def final_soc(initial):
        state = initial
        for change in changes:
            state = min(usable_capacity, max(0.0, retention * state + change))
        return state

    initial = 0.0
    for _ in range(16):
        updated = final_soc(initial)
        if abs(updated - initial) <= tolerance:
            return updated
        initial = updated

    lower, upper = 0.0, usable_capacity
    for _ in range(64):
        midpoint = (lower + upper) / 2.0
        residual = final_soc(midpoint) - midpoint
        if residual > 0.0:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= tolerance:
            break
    result = (lower + upper) / 2.0
    if abs(final_soc(result) - result) > 4.0 * tolerance:
        raise RuntimeError("cyclic battery boundary failed to converge")
    return result


def dispatch_hourly(
    generation_kw,
    demand_kw,
    battery_kwh,
    *,
    charge_efficiency=0.95,
    discharge_efficiency=0.95,
    depth_of_discharge=0.8,
    c_rate=0.5,
    self_discharge_per_hour=0.015,
    initial_soc_kwh=0.0,
    cyclic=True,
):
    """Dispatch a battery over equal one-hour steps.

    ``charge_kw`` is electricity entering the charger; ``discharge_kw`` is
    electricity delivered to the load. SOC is energy within the usable portion
    of the battery, from zero to ``depth_of_discharge * battery_kwh``. Losses
    include self-discharge and both conversion losses, in kWh per hourly step.

    Cyclic runs solve for initial SOC equal to final SOC and override the supplied
    initial state. Noncyclic runs use the explicit initial state. The reference's
    1.5% hourly self-discharge default is exposed for scientific review, not
    asserted to represent a particular commercial battery.
    """
    generation, demand = _profiles(generation_kw, demand_kw)
    capacity = _scalar(battery_kwh, "battery_kwh")
    charge_efficiency = _scalar(charge_efficiency, "charge_efficiency", maximum=1.0, positive=True)
    discharge_efficiency = _scalar(discharge_efficiency, "discharge_efficiency", maximum=1.0, positive=True)
    depth = _scalar(depth_of_discharge, "depth_of_discharge", maximum=1.0)
    c_rate = _scalar(c_rate, "c_rate")
    decay = _scalar(self_discharge_per_hour, "self_discharge_per_hour", maximum=1.0)
    initial = _scalar(initial_soc_kwh, "initial_soc_kwh")
    if not isinstance(cyclic, (bool, np.bool_)):
        raise ValueError("cyclic must be a boolean")
    usable_capacity = capacity * depth
    if not np.isfinite(usable_capacity) or not np.isfinite(capacity * c_rate):
        raise ValueError("battery capacity and power limits must be finite")
    if initial > usable_capacity:
        raise ValueError("initial_soc_kwh exceeds usable battery capacity")
    power_limit = capacity * c_rate
    retention = 1.0 - decay
    net = generation - demand
    charge_available = np.minimum(np.maximum(net, 0.0), power_limit)
    discharge_needed = np.minimum(np.maximum(-net, 0.0), power_limit)
    # Larger requests all empty the usable inventory. Clip before using this
    # energy in the annual map, including for valid, subnormal efficiencies.
    with np.errstate(over="ignore"):
        discharge_energy_needed = np.minimum(
            discharge_needed / discharge_efficiency, usable_capacity
        )
    if cyclic:
        changes = charge_available * charge_efficiency - discharge_energy_needed
        initial = _cyclic_initial_soc(changes, usable_capacity, retention)

    length = generation.size
    charge = np.zeros(length)
    discharge = np.zeros(length)
    soc = np.zeros(length)
    losses = np.zeros(length)
    state = initial
    for index in range(length):
        self_loss = state * decay
        state -= self_loss
        discharged_energy = 0.0
        if net[index] >= 0.0:
            charge[index] = min(charge_available[index], max(0.0, usable_capacity - state) / charge_efficiency)
            state += charge[index] * charge_efficiency
        else:
            discharged_energy = min(discharge_energy_needed[index], state)
            discharge[index] = discharged_energy * discharge_efficiency
            state -= discharged_energy
        # Remove floating-point drift only; physical limits are applied above.
        state = min(usable_capacity, max(0.0, state))
        soc[index] = state
        losses[index] = (
            self_loss
            + charge[index] * (1.0 - charge_efficiency)
            # Algebraically discharge / efficiency - discharge. Keeping the
            # consumed energy also preserves accounting if output underflows.
            + discharged_energy - discharge[index]
        )

    served = np.minimum(generation, demand) + discharge
    unmet = np.maximum(0.0, demand - served)
    curtailed = np.maximum(0.0, net - charge)
    demand_energy = float(np.sum(demand))
    return {
        "demand_kw": demand,
        "generation_kw": generation,
        "served_kw": served,
        "unmet_kw": unmet,
        "curtailed_kw": curtailed,
        "charge_kw": charge,
        "discharge_kw": discharge,
        "soc_kwh": soc,
        "loss_kwh": losses,
        "initial_soc_kwh": float(initial),
        "final_soc_kwh": float(soc[-1]),
        "lpsp": float(np.sum(unmet) / demand_energy) if demand_energy > 0.0 else 0.0,
    }
