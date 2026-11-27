import csv
import json
from copy import deepcopy
from io import StringIO
import numpy as np
import pytest

from app.cache import RunCache
from app.config import ILLUSTRATIVE_COSTS, FINANCE_DEFAULTS
from app.data_loader import demo_dataset, parse_resource_data
from app.engine.config_eval import evaluate_configuration


def example():
    return {"scenario": {"demand_kw": 100, "capacities_kw": {"floating_solar": 200, "onshore_wind": 200, "otec": 100},
                         "battery_kwh": 500}, "include_hourly": False}


def test_health_metadata_and_factory_isolation(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json["status"] == "ok"
    metadata = client.get("/api/metadata").json
    assert len(metadata["technologies"]) == 6
    assert metadata["demo_data_synthetic"] is True
    assert metadata["battery_defaults"]["self_discharge_per_hour"] == .015


def test_evaluate_annual_conservation_and_exports(client):
    response = client.post("/api/evaluate", json=example())
    assert response.status_code == 200, response.json
    result = response.json
    assert "hourly" not in result
    assert result["provenance"]["synthetic"] is True
    assert result["provenance"]["hours"] == 8760
    assert len(result["monthly"]) == 12
    metrics = result["metrics"]
    assert metrics["demand_energy_kwh"] == 876000
    assert metrics["energy_served_kwh"] + metrics["unmet_energy_kwh"] == pytest.approx(876000)
    assert metrics["generation_energy_kwh"] == pytest.approx(metrics["energy_served_kwh"] + metrics["curtailed_energy_kwh"] + metrics["battery_loss_kwh"], abs=.01)
    assert sum(month["served_kwh"] for month in result["monthly"]) == pytest.approx(metrics["energy_served_kwh"])
    assert sum(month["hours"] for month in result["monthly"]) == 8760
    assert result["monthly"][1]["hours"] == 28 * 24
    assert result["storage_boundary"]["initial_soc_kwh"] == pytest.approx(result["storage_boundary"]["final_soc_kwh"], abs=1e-5)
    run = client.get(f"/api/runs/{result['run_id']}")
    assert len(run.json["hourly"]["soc_kwh"]) == 8760
    prefix = f"/api/runs/{result['run_id']}/export"
    csv_response = client.get(prefix + ".csv")
    assert csv_response.status_code == 200
    rows = list(csv.reader(StringIO(csv_response.text)))
    assert len(rows) == 8765
    assert rows[4][0] == "timestamps"
    assert client.get(prefix + ".json").json["metrics"] == metrics
    pdf = client.get(prefix + ".pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF-")
    assert len(pdf.data) > 1000


def test_no_generation_and_battery_cannot_supply_free_energy(client):
    result = client.post("/api/evaluate", json={"scenario": {"demand_kw": 5, "battery_kwh": 1e6}, "include_hourly": False}).json
    assert result["metrics"]["energy_served_kwh"] == 0
    assert result["metrics"]["lpsp"] == 1
    assert result["economics"]["lcoe"] is None
    assert result["feasible"] is False


@pytest.mark.parametrize("body", [
    None, [], {"scenario": []}, {"scenario": {"demand_kw": 0}}, {"scenario": {"demand_kw": -1}},
    {"scenario": {"demand_kw": True}}, {"scenario": {"demand_kw": "100"}},
    {"scenario": {"demand_kw": float("nan")}}, {"scenario": {"demand_kw": float("inf")}}, {"scenario": {"demand_kw": 10**400}},
    {"scenario": {"capacities_kw": {"unknown": 5}}}, {"scenario": {"battery": {"charge_efficiency": 0}}},
    {"scenario": {"battery": {"self_discharge_per_hour": 2}}}, {"scenario": {"location_id": "unknown"}},
    {"finance": {"project_years": 1.5}}, {"finance": {"currency": "anything"}},
    {"include_hourly": "false"}, {"scenario": {"demand_profile_kw": [1, 2]}}, {"unexpected": 1},
])
def test_bad_inputs_return_json_400(client, body):
    response = client.post("/api/evaluate", data=json.dumps(body), content_type="application/json")
    assert response.status_code == 400, response.text
    assert "error" in response.json


def test_http_errors_and_cors(client):
    assert client.post("/api/evaluate", data="{").status_code == 415
    assert client.post("/api/evaluate", data="{", content_type="application/json").status_code == 400
    assert client.get("/missing").status_code == 404
    assert client.get("/api/runs/not-a-run/export.csv").status_code == 404
    assert client.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in client.get("/api/health", headers={"Origin": "https://unrelated.example"}).headers
    assert client.options("/api/evaluate", headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_comparison_same_demand_and_rank(client):
    first = example()["scenario"]
    second = deepcopy(first)
    second["capacities_kw"]["otec"] = 200
    response = client.post("/api/compare", json={"scenarios": [first, second]})
    assert response.status_code == 200, response.json
    assert len(response.json["configurations"]) == 2
    assert [item["rank"] for item in response.json["configurations"]] == [1, 2]
    second["demand_kw"] = 200
    assert client.post("/api/compare", json={"scenarios": [first, second]}).status_code == 400


def test_optimize_actual_hourly_filter(client):
    body = {"scenario": {"demand_kw": 10, "max_lpsp": .05}, "options": {"selected_technologies": ["otec"], "candidate_budget": 12}, "include_hourly": False}
    response = client.post("/api/optimize", json=body)
    assert response.status_code == 200, response.json
    result = response.json
    assert result["diagnostics"]["global_optimum"] is False
    assert result["best"] is not None
    assert result["best"]["feasible"] is True
    assert result["best"]["metrics"]["lpsp"] <= .05 + 1e-9
    assert result["best"]["run_id"]
    assert "hourly" not in result["best"]
    assert result["provenance"]["synthetic"] is True


@pytest.mark.parametrize("options", [[], {"candidate_budget": 9999}, {"max_results": 1.5}, {"selected_technologies": []}, {"capacity_grid": {"otec": [-1]}}])
def test_optimizer_options_validated(client, options):
    assert client.post("/api/optimize", json={"options": options}).status_code == 400


def test_custom_constant_dataset_and_invalid_calendar(client):
    demo = demo_dataset()
    data = {"timestamps": list(demo["timestamps"]), "capacity_factors": {"otec": [.5] * 8760},
            "provenance": {"source": "Analytic constant-CF test, not measured resources", "synthetic": True}}
    response = client.post("/api/evaluate", json={"resource_data": data, "scenario": {"location_id": "custom-site", "demand_kw": 10, "capacities_kw": {"otec": 20}}, "include_hourly": False})
    assert response.status_code == 200, response.json
    assert response.json["metrics"]["lpsp"] == pytest.approx(0)
    assert response.json["metrics"]["generation_energy_kwh"] == 87600
    data["timestamps"][10] = data["timestamps"][9]
    assert client.post("/api/resources/convert", json=data).status_code == 400


def test_raw_weather_conversion(client):
    n = 8760
    data = {"timestamps": list(demo_dataset()["timestamps"]), "weather": {"ghi_w_m2": [1000] * n, "air_temperature_c": [25] * n,
            "wind_speed_m_s": [11] * n, "significant_wave_height_m": [2] * n, "peak_period_s": [8] * n},
            "provenance": {"source": "Synthetic constant-weather verification", "synthetic": True}}
    response = client.post("/api/resources/convert", json=data)
    assert response.status_code == 200, response.json
    assert response.json["capacity_factors"]["floating_solar"][0] == pytest.approx(.8)
    assert response.json["capacity_factors"]["onshore_wind"][0] == pytest.approx(.88)
    assert response.json["warnings"]


def test_run_cache_expiry_and_eviction():
    now = [100.0]
    cache = RunCache(maximum=2, ttl_seconds=10, clock=lambda: now[0])
    first = cache.put({})["run_id"]
    second = cache.put({})["run_id"]
    third = cache.put({})["run_id"]
    assert cache.get(first) is None
    assert cache.get(second) is not None
    now[0] = 110.0
    assert cache.get(third) is None
