from flask import Blueprint, current_app, jsonify, request, abort

from ..config import TECHNOLOGIES, LOCATIONS, BATTERY_DEFAULTS, FINANCE_DEFAULTS, ILLUSTRATIVE_COSTS, MODEL_WARNINGS
from ..data_loader import demo_dataset, parse_resource_data
from ..validation import mapping, normalize_scenario, normalize_costs, normalize_options
from ..engine.config_eval import evaluate_configuration
from ..engine.optimizer import optimize_configuration
from ..engine.scoring import rank_configurations

api = Blueprint("api", __name__, url_prefix="/api")


def prepare(body, *, extra=()):
    mapping(body, "request", {"scenario", "resource_data", "technology_costs", "finance", "include_hourly"} | set(extra))
    scenario = body.get("scenario", {})
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    location = scenario.get("location_id", "lakshadweep")
    if not isinstance(location, str) or not location or len(location) > 80:
        raise ValueError("location_id must be a nonempty string up to 80 characters")
    dataset = parse_resource_data(body["resource_data"], location) if "resource_data" in body else demo_dataset(location)
    normalized = normalize_scenario(scenario, dataset)
    costs, finance = normalize_costs(body.get("technology_costs"), body.get("finance"))
    if not isinstance(body.get("include_hourly", True), bool):
        raise ValueError("include_hourly must be a boolean")
    return dataset, normalized, costs, finance


def annotate(result, dataset, costs, finance):
    result["provenance"] = {key: dataset[key] for key in ("id", "location_id", "source", "synthetic", "data_validation")}
    result["provenance"]["hours"] = len(dataset["timestamps"])
    result["provenance"]["start"] = dataset["timestamps"][0]
    result["provenance"]["end"] = dataset["timestamps"][-1]
    result["economic_assumptions"] = {"technology_costs": costs, "finance": finance,
        "status": "Illustrative defaults with optional user overrides; no market cost verification.",
        "cash_flow_convention": "O&M and diesel inputs are first end-of-year costs.", "salvage_value": 0.0}
    result["carbon_assumptions"] = {"baseline_kg_co2_per_kwh": 0.7, "renewable_kg_co2_per_kwh": 0.0,
        "status": "Illustrative operational emissions only; excludes embodied and lifecycle emissions."}
    result["warnings"] = MODEL_WARNINGS + list(dataset.get("warnings", []))
    if dataset["synthetic"]:
        result["warnings"] = ["SYNTHETIC DEMONSTRATION RESOURCES: this is not a measured site assessment."] + result["warnings"]
    return result


def store_result(result, dataset, costs, finance):
    return current_app.extensions["run_cache"].put(annotate(result, dataset, costs, finance))


def response_result(result, include_hourly=True):
    if include_hourly:
        return result
    return {key: value for key, value in result.items() if key != "hourly"}


@api.get("/health")
def health():
    return jsonify(status="ok", service="BlueGrid scientific API", version="0.2.0", optimizer="scipy-highs-monthly-proposal-and-hourly-filter")


@api.get("/metadata")
def metadata():
    return jsonify(technologies=TECHNOLOGIES, locations=LOCATIONS, battery_defaults=BATTERY_DEFAULTS,
                   finance_defaults=FINANCE_DEFAULTS, illustrative_technology_costs=ILLUSTRATIVE_COSTS,
                   demo_data_synthetic=True, warnings=MODEL_WARNINGS)


@api.post("/evaluate")
def evaluate():
    body = request.get_json()
    dataset, scenario, costs, finance = prepare(body)
    result = store_result(evaluate_configuration(dataset, scenario, costs, finance), dataset, costs, finance)
    return jsonify(response_result(result, body.get("include_hourly", True)))


@api.post("/optimize")
def optimize():
    body = request.get_json()
    dataset, scenario, costs, finance = prepare(body, extra=("options",))
    options = normalize_options(body.get("options"))
    result = optimize_configuration(dataset, scenario, costs, finance, options=options)
    if result.get("best") is not None:
        best = store_result(result["best"], dataset, costs, finance)
        result["best"] = response_result(best, body.get("include_hourly", True))
    result["provenance"] = {key: dataset[key] for key in ("source", "synthetic", "data_validation")}
    result["interpretation"] = "Best feasible candidate found within the configured search; no global hourly optimum is claimed."
    return jsonify(result)


@api.post("/compare")
def compare():
    body = request.get_json()
    mapping(body, "request", {"scenarios", "resource_data", "technology_costs", "finance", "include_hourly"})
    scenarios = body.get("scenarios")
    if not isinstance(scenarios, list) or not 2 <= len(scenarios) <= 10:
        raise ValueError("scenarios must contain between 2 and 10 scenarios")
    prepared = []
    for index, scenario in enumerate(scenarios):
        single = {key: value for key, value in body.items() if key != "scenarios"}
        single["scenario"] = scenario
        dataset, normalized, costs, finance = prepare(single)
        prepared.append((index, dataset, normalized, costs, finance))
    locations = {entry[1]["location_id"] for entry in prepared}
    if len(locations) != 1:
        raise ValueError("compared scenarios must use the same location and resource dataset")
    demands = [entry[2]["demand_profile_kw"] for entry in prepared]
    if any((demands[0] != demand).any() for demand in demands[1:]):
        raise ValueError("compared scenarios must serve the same demand profile")
    results = []
    for index, dataset, scenario, costs, finance in prepared:
        result = store_result(evaluate_configuration(dataset, scenario, costs, finance), dataset, costs, finance)
        result["scenario_index"] = index
        results.append(response_result(result, body.get("include_hourly", False)))
    return jsonify(configurations=rank_configurations(results), ranking="LCOE ascending, then gross CAPEX; feasibility reported separately.")


@api.get("/runs/<run_id>")
def get_run(run_id):
    result = current_app.extensions["run_cache"].get(run_id)
    if result is None:
        abort(404, description="Run not found or expired")
    return jsonify(result)


@api.post("/resources/convert")
def resources():
    body = request.get_json()
    dataset = parse_resource_data(body)
    return jsonify(timestamps=dataset["timestamps"], capacity_factors={key: value.tolist() for key, value in dataset["capacity_factors"].items()},
                   provenance={key: dataset[key] for key in ("source", "synthetic", "data_validation")}, warnings=dataset["warnings"])
