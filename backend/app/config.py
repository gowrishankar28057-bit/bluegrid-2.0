"""Explicit reference assumptions and illustrative, non-market cost inputs."""

TECHNOLOGIES = (
    "floating_solar", "onshore_solar", "onshore_wind", "offshore_wind", "otec", "wave",
)

BATTERY_DEFAULTS = {
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
    "depth_of_discharge": 0.8,
    "c_rate": 0.5,
    "self_discharge_per_hour": 0.015,
}

FINANCE_DEFAULTS = {
    "real_discount_rate": 0.05,
    "general_inflation": 0.04,
    "opex_escalation": 0.04,
    "diesel_escalation": 0.05,
    "battery_cost_escalation": -0.02,
    "project_years": 25,
    "diesel_cost_per_kwh": 25.0,
    "battery_subsidy_fraction": 0.0,
    "currency": "INR",
}

# Software demonstration assumptions, not quotations, published costs, or site estimates.
ILLUSTRATIVE_COSTS = {
    "floating_solar": {"capex_per_kw": 80000.0, "opex_per_kw_year": 1200.0, "lifetime_years": 25},
    "onshore_solar": {"capex_per_kw": 60000.0, "opex_per_kw_year": 900.0, "lifetime_years": 25},
    "onshore_wind": {"capex_per_kw": 100000.0, "opex_per_kw_year": 2500.0, "lifetime_years": 20},
    "offshore_wind": {"capex_per_kw": 180000.0, "opex_per_kw_year": 5000.0, "lifetime_years": 20},
    "otec": {"capex_per_kw": 400000.0, "opex_per_kw_year": 12000.0, "lifetime_years": 25},
    "wave": {"capex_per_kw": 350000.0, "opex_per_kw_year": 10000.0, "lifetime_years": 20},
    "battery": {"capex_per_kwh": 18000.0, "opex_per_kwh_year": 300.0, "lifetime_years": 10, "replacement_fraction": 1.0},
}

LOCATIONS = {
    "lakshadweep": {"name": "Lakshadweep, India", "latitude": 10.57, "longitude": 72.64},
    "brest": {"name": "Brest, France", "latitude": 48.39, "longitude": -4.49},
}

MODEL_WARNINGS = [
    "The reference self-discharge assumption is 1.5% per hour, not per month; verify it for the selected battery.",
    "OTEC uses the reference's simplified temperature-gradient model, not a detailed plant feasibility assessment.",
    "Technology variants share reference curves; site-specific equipment and loss parameters require calibration.",
    "Monthly LP solutions are sizing proposals. Only chronological hourly dispatch establishes modeled reliability.",
    "Unmet demand is reported explicitly. Diesel backup costs and emissions are hypothetical and do not simulate a diesel generator.",
    "Cost, carbon, and resource assumptions require independent engineering validation before investment use.",
]
