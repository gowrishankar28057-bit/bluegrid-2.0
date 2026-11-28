# BlueGrid 2.0 - Flask API

The API is a local scientific service for the separate React frontend. Model definitions and assumptions are in [MODELS.md](MODELS.md). Resources and default costs are synthetic/illustrative until replaced with documented site inputs.

## Setup and execution

From `backend/`, using Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. The server binds to `http://127.0.0.1:5000`, with debug mode disabled. An alternative WSGI command is:

```powershell
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:5000 --call app:create_app
```

Run `npm run dev` separately inside `frontend/`. CORS permits `http://localhost:5173` and `http://127.0.0.1:5173`. Set `BLUEGRID_ALLOWED_ORIGINS` to a comma-separated list for a different local frontend origin. The Earth explorer includes a planning form connected to `/api/evaluate` through Vite's local proxy; the full analytics and policy screens remain pending.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service/version status. |
| GET | `/api/metadata` | Technologies, locations, defaults, and warnings. |
| POST | `/api/evaluate` | Evaluate one annual configuration; cache a run. |
| POST | `/api/optimize` | Monthly LP plus bounded, hourly-checked candidate search. |
| POST | `/api/compare` | Rank 2-10 configurations for the same location and demand. |
| POST | `/api/resources/convert` | Validate annual resources or convert raw weather to capacity factors. |
| GET | `/api/runs/{run_id}` | Retrieve a cached full result. |
| GET | `/api/runs/{run_id}/export.json` | Download the full result and assumptions. |
| GET | `/api/runs/{run_id}/export.csv` | Download hourly values with provenance. |
| GET | `/api/runs/{run_id}/export.pdf` | Download a summary and modeling caveats. |

## Evaluate

Example request (`backend/data/example-request.json`):

```json
{
  "scenario": {
    "location_id": "lakshadweep",
    "demand_kw": 100,
    "capacities_kw": {"floating_solar": 200, "onshore_wind": 200, "otec": 50},
    "battery_kwh": 600,
    "max_lpsp": 0.05,
    "min_wind_fraction": 0,
    "battery": {"self_discharge_per_hour": 0.015}
  },
  "include_hourly": false
}
```

From the repository root in PowerShell:

```powershell
$body = Get-Content -Raw backend/data/example-request.json
$result = Invoke-RestMethod http://127.0.0.1:5000/api/evaluate -Method Post -ContentType application/json -Body $body
$result.metrics
```

Supported generator keys are `floating_solar`, `onshore_solar`, `onshore_wind`, `offshore_wind`, `otec`, and `wave`. Capacities are kW; `battery_kwh` is energy capacity. Omitted generator capacities are zero. Demand defaults to 100 kW; provide either constant `demand_kw` or a nonnegative `demand_profile_kw` array matching the resource year.

Battery options are `charge_efficiency`, `discharge_efficiency`, `depth_of_discharge`, `c_rate`, and `self_discharge_per_hour`. Efficiencies and DoD must be in (0, 1]; self-discharge is in [0, 1]. `max_lpsp` and `min_wind_fraction` are fractions in [0, 1]. The wind policy is combined onshore/offshore installed kW divided by peak demand kW.

Responses contain `run_id`, `configuration`, `metrics`, `economics`, `carbon`, `monthly`, `technology_contributions`, `storage_boundary`, `feasible`, `provenance`, `economic_assumptions`, `carbon_assumptions`, and `warnings`. Hourly arrays are included unless `include_hourly` is false. The full hourly run remains available for retrieval and exports either way.

## Optimization and comparison

`/api/optimize` accepts the same fields as evaluate plus:

```json
{
  "options": {
    "selected_technologies": ["floating_solar", "onshore_wind", "otec"],
    "max_capacities_kw": {"floating_solar": 1000, "onshore_wind": 1000, "otec": 300},
    "max_battery_kwh": 5000,
    "candidate_budget": 64,
    "max_results": 5
  }
}
```

Optional `capacity_grid` maps generator names and/or `battery_kwh` to explicit axes, with at most 16 values each. Bounds still apply. `candidate_budget` is 1-256; `max_results` is 1-10. Return fields include `status`, `best`, `configurations`, and `diagnostics`. The best result receives a run ID. `best: null` means no candidate passed within the search, not a proof of physical infeasibility. Inspect `truncated` and `global_optimum: false`.

`/api/compare` replaces `scenario` with `scenarios: [...]`. It accepts common `resource_data`, costs, finance, and `include_hourly`. Scenarios must use the same location and demand profile. LCOE/CAPEX rank and feasibility are reported separately, so a cheap unreliable design is never silently described as reliable.

## Custom resources

Provide `resource_data` with a complete calendar year of contiguous UTC ISO timestamps, exactly one resource representation, and provenance:

```text
resource_data:
  timestamps: ["2025-01-01T00:00:00Z", ... 8760 hourly timestamps ...]
  capacity_factors:
    floating_solar: [0.0, ... values in [0,1] ...]
  provenance:
    source: "Dataset owner, product, period, processing notes and access reference"
    synthetic: false
```

Alternatively, replace `capacity_factors` with `weather` arrays: `ghi_w_m2`, `air_temperature_c`, `wind_speed_m_s`, `significant_wave_height_m`, `peak_period_s`; optional `surface_temperature_c` and `deep_temperature_c`. Missing generator CF arrays are zero. Missing raw-weather requirements are errors. A false synthetic flag is a user declaration; it is not independent source verification.

Convert a prepared raw CSV with columns `timestamp` and the weather names above:

```powershell
.\backend\.venv\Scripts\python.exe scripts/prepare_resources.py --input weather.csv --output backend/data/resources.json --source "Dataset reference" --measured
```

To generate a reproducible demonstration input instead:

```powershell
.\backend\.venv\Scripts\python.exe scripts/prepare_resources.py --demo lakshadweep --output backend/data/demo.json
```

## Cost overrides and errors

`technology_costs` merges per-technology overrides into illustrative defaults. Generator fields are `capex_per_kw`, `opex_per_kw_year`, `lifetime_years`; battery fields are `capex_per_kwh`, `opex_per_kwh_year`, `lifetime_years`, `replacement_fraction`. Currency must be consistent across all entries.

`finance` accepts `real_discount_rate`, `general_inflation`, `opex_escalation`, `diesel_escalation`, `battery_cost_escalation`, `project_years`, `diesel_cost_per_kwh`, `battery_subsidy_fraction`, and `currency`. Full resolved assumptions accompany each run for reproducibility.

Validation failures return HTTP 400 with `{"error":{"code":"invalid_input","message":"..."}}`. Malformed JSON, incorrect content type, missing/expired runs, and requests above 8 MiB use the corresponding JSON HTTP error. Nonfinite numbers, unknown fields, negative capacities, invalid calendars, and mismatched series are rejected.

Runs are held in a bounded per-process memory cache (32 results, one-hour TTL by default). Restarting the process removes them; WSGI workers do not share them. Persistent jobs, authentication, calibrated site datasets, and a deployed multiuser service are separate deployment work.
