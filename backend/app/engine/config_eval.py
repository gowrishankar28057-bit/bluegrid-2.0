"""Orchestrate one configuration; retain exact hourly energy accounting."""
import numpy as np
from .bess import dispatch_hourly
from .economics import evaluate_economics
from .carbon import calculate_carbon


def evaluate_configuration(dataset, scenario, technology_costs, finance, *, fast=False):
    capacities = scenario["capacities_kw"]
    demand = np.asarray(scenario["demand_profile_kw"], dtype=float)
    generation_by_tech = {name: np.asarray(values) * capacities.get(name, 0.0)
                          for name, values in dataset["capacity_factors"].items()}
    generation = np.sum(list(generation_by_tech.values()), axis=0)
    dispatch = dispatch_hourly(generation, demand, scenario["battery_kwh"], **scenario["battery"], cyclic=True)
    metrics = {
        "demand_energy_kwh": float(demand.sum()), "generation_energy_kwh": float(generation.sum()),
        "energy_served_kwh": float(dispatch["served_kw"].sum()), "unmet_energy_kwh": float(dispatch["unmet_kw"].sum()),
        "curtailed_energy_kwh": float(dispatch["curtailed_kw"].sum()), "battery_loss_kwh": float(dispatch["loss_kwh"].sum()),
        "lpsp": float(dispatch["lpsp"]),
        "renewable_contribution": float(dispatch["served_kw"].sum() / demand.sum()) if demand.sum() else 0.0,
    }
    economics = evaluate_economics(capacities, scenario["battery_kwh"], metrics["energy_served_kwh"], metrics["unmet_energy_kwh"], technology_costs, finance)
    wind = capacities.get("onshore_wind", 0.0) + capacities.get("offshore_wind", 0.0)
    policy_ok = wind + 1e-8 >= scenario.get("min_wind_fraction", 0.0) * float(demand.max())
    result = {"configuration": {"capacities_kw": dict(capacities), "battery_kwh": scenario["battery_kwh"], "battery": dict(scenario["battery"])},
              "metrics": metrics, "economics": economics,
              "feasible": bool(metrics["lpsp"] <= scenario["max_lpsp"] + 1e-9 and policy_ok),
              "reliability_target": scenario["max_lpsp"], "wind_policy_satisfied": bool(policy_ok)}
    if fast:
        return result
    result["carbon"] = calculate_carbon(metrics["energy_served_kwh"], metrics["unmet_energy_kwh"])
    result["storage_boundary"] = {"cyclic": True, "initial_soc_kwh": float(dispatch["initial_soc_kwh"]), "final_soc_kwh": float(dispatch["final_soc_kwh"])}
    result["monthly"] = []
    month_index = np.asarray(dataset["month_index"])
    for month in sorted(set(month_index.tolist())):
        mask = month_index == month
        result["monthly"].append({"month": int(month) + 1, "hours": int(mask.sum()),
                                  "demand_kwh": float(demand[mask].sum()), "generation_kwh": float(generation[mask].sum()),
                                  "served_kwh": float(dispatch["served_kw"][mask].sum()), "unmet_kwh": float(dispatch["unmet_kw"][mask].sum()),
                                  "curtailed_kwh": float(dispatch["curtailed_kw"][mask].sum()),
                                  "by_technology_kwh": {name: float(values[mask].sum()) for name, values in generation_by_tech.items()}})
    result["hourly"] = {key: np.asarray(dispatch[key]).tolist() for key in (
        "demand_kw", "generation_kw", "served_kw", "unmet_kw", "curtailed_kw", "charge_kw", "discharge_kw", "soc_kwh", "loss_kwh")}
    result["hourly"]["timestamps"] = list(dataset["timestamps"])
    result["technology_contributions"] = [{"technology": name, "available_generation_kwh": float(values.sum())} for name, values in generation_by_tech.items()]
    return result
