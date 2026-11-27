# BlueGrid 2.0

A renewable energy planning platform for island and coastal systems, integrating land-based renewables, ocean energy, and battery storage.

**Development stage:** Flask scientific backend and React frontend foundation. The core planning screens are the next interface phase. Licensed under [MIT](LICENSE).

## Problem Statement

Solar, wind, and ocean resources vary over time. Selecting a renewable energy mix requires balancing those resources against electricity demand, storage losses, investment costs, and reliability requirements.

BlueGrid 2.0 will help engineers, researchers, investors, and policymakers compare scenarios through a geographic explorer, planning workspace, analytics, and policy workspace. Planned technologies include floating solar, onshore solar, onshore wind, offshore wind, ocean thermal energy conversion (OTEC), wave energy, and battery energy storage systems (BESS).

The engineering reference, *BlueGrid: Optimal Hybrid Renewable Energy Planner - System Architecture & Mathematical Formulation* (BlueGrid Development Team, 17 October 2026), describes a Lakshadweep-focused system. Lakshadweep, India, and Brest, France, are planned BlueGrid 2.0 demonstration locations, subject to data and feasibility checks. Worldwide resource coverage is not established.

## Architecture Blueprint

The repository separates presentation, scientific computation, data preparation, and documentation. The Flask backend implements physical models, dispatch, economics, reliability checks, optimization, and exports. The separate React frontend will collect planning inputs and display API responses.

```text
bluegrid-2.0/
├── frontend/
│   ├── public/                    # Assets served without bundler processing
│   ├── src/
│   │   ├── assets/                # Images, illustrations, and local visual assets
│   │   ├── components/
│   │   │   ├── common/            # Shared controls and interface elements
│   │   │   ├── globe/             # Future Earth explorer components
│   │   │   ├── planner/           # Future scenario and capacity controls
│   │   │   └── charts/            # Future analytical visualizations
│   │   ├── pages/                 # Screen-level views
│   │   ├── hooks/                 # Reusable React state and behavior
│   │   ├── services/              # Future API client and integration boundary
│   │   ├── types/                 # Shared TypeScript domain models
│   │   ├── data/                  # Explicitly labeled demonstration fixtures
│   │   ├── App.tsx                # Application root and starter view
│   │   ├── main.tsx               # React entry point
│   │   └── index.css              # Global styles and Tailwind integration
│   ├── index.html                 # Browser document entry
│   ├── package.json               # Frontend dependencies and commands
│   ├── package-lock.json          # Reproducible dependency resolution
│   ├── tsconfig.json              # Application TypeScript configuration
│   ├── tsconfig.node.json         # Build-tool TypeScript configuration
│   └── vite.config.ts             # Vite development and build configuration
├── backend/
│   ├── app/
│   │   ├── __init__.py            # Flask application factory
│   │   ├── config.py              # Explicit modeling and cost assumptions
│   │   ├── data_loader.py         # Annual datasets and resource conversion
│   │   ├── validation.py          # Request and unit validation
│   │   ├── cache.py               # Bounded, expiring analysis runs
│   │   ├── engine/
│   │   │   ├── generation.py      # Solar, wind, OTEC, and wave availability
│   │   │   ├── bess.py            # Hourly dispatch and cyclic SOC
│   │   │   ├── economics.py       # Nominal DCF, replacements, and LCOE
│   │   │   ├── carbon.py          # Explicit operational emissions assumptions
│   │   │   ├── scoring.py         # LCOE/CAPEX ranking
│   │   │   ├── config_eval.py     # Configuration orchestration and analytics
│   │   │   └── optimizer.py       # Monthly LP and hourly candidate screening
│   │   └── routes/                # Evaluation, optimization, comparison, exports
│   ├── data/                      # Example request and future sourced datasets
│   ├── tests/                     # Numerical invariants and API integration
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── run.py
├── scripts/
│   └── prepare_resources.py        # CSV conversion or synthetic resource export
├── docs/
│   ├── BLUEPRINT.md               # Engineering boundaries
│   ├── MODELS.md                  # Equations, units, assumptions, limitations
│   └── API.md                     # Setup, requests, responses, and exports
├── .github/workflows/backend.yml  # Automated backend verification
├── .gitignore
├── README.md
└── LICENSE
```

Reserved frontend directories contain `.gitkeep` files so Git retains the structure. The backend contains implemented Python modules and numerical tests.

| Area | Responsibility |
| --- | --- |
| `frontend/` | Inputs, navigation, and visualizations. |
| `backend/` | Scientific calculations, validation, and API responses. |
| `scripts/` | Resource preparation with recorded provenance. |
| `docs/` | Architecture and modeling assumptions. |

Frontend images belong in `frontend/src/assets/`; assets requiring a stable public URL belong in `frontend/public/`.

## Engineering Approach

The implemented backend workflow follows the reference architecture and modeling discussion (pp. 3-6 and 8-10):

1. Select a supported location and obtain traceable resource and technology inputs.
2. Define electricity demand in kW, candidate generation capacities in kW, battery energy in kWh, and reliability preferences.
3. Convert resource time series into technology-specific generation availability.
4. Evaluate generation and chronological battery dispatch, including energy limits, conversion losses, curtailment, and unmet demand.
5. Propose capacity mixes through monthly linear programming and screen alternatives using hourly dispatch over a defined year.
6. Compare costs, energy served, unmet energy, renewable contribution, and carbon estimates with explicit assumptions.

Economic outputs include capital expenditure (CAPEX), operating expenditure (OPEX), equivalent annual cost, levelized cost of energy (LCOE), and cost of service. LPSP is unmet energy divided by demand energy. Hourly battery dispatch enforces a cyclic boundary, so a charged initial battery cannot supply free annual energy.

The bundled annual resource series are explicitly synthetic and default costs are illustrative. Optimization reports the best feasible candidate found within a bounded search; it does not claim a global hourly optimum. [Model documentation](docs/MODELS.md) records the reference's unit ambiguities, the configurable 1.5% hourly self-discharge assumption, and numerical conventions. Calibrated site data and independent engineering validation remain necessary.

## Technology Stack

| Layer | Technology | Status |
| --- | --- | --- |
| Frontend | React, TypeScript, [Vite](https://vite.dev/guide/) | Starter foundation |
| Styling | [Tailwind CSS](https://tailwindcss.com/docs/installation/using-vite) | Foundation configuration |
| 3D geographic interface | React Three Fiber and Three.js | Planned |
| Charts | Recharts | Planned |
| Icons | Lucide React | Planned |
| Scientific API | Python and [Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) | Implemented |
| Numerical processing | NumPy and standard-library datetime | Implemented |
| Optimization | [SciPy HiGHS](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) | Implemented |
| Exports | ReportLab, CSV, and JSON | Implemented |
| Verification | pytest and GitHub Actions | Numerical and API test suite |

The reference used Flask templates and vanilla JavaScript. BlueGrid 2.0 exposes a separate JSON API for the React frontend. Python dependencies are declared in `backend/requirements.txt` and test dependencies in `backend/requirements-dev.txt`.

## Installation

Install Git, Node.js 24 LTS, and npm, then clone the repository:

```bash
git clone https://github.com/gowrishankar28057-bit/bluegrid-2.0.git
cd bluegrid-2.0/frontend
npm ci
```

For an existing checkout, run `npm ci` inside `frontend/`. The lockfile keeps installations reproducible.

For the backend, install Python 3.11 or newer. From the repository root on Windows:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

On macOS/Linux, use `.venv/bin/python`. The API starts at `http://127.0.0.1:5000`. No API credentials or external data downloads are required for the synthetic demonstration. [API documentation](docs/API.md) includes sample evaluation requests, optimization controls, custom resource ingestion, and WSGI execution.

## Running the Frontend

From `frontend/`, start the development server:

```bash
npm run dev
```

Open the address printed by Vite. The starter displays frontend development status. The core planning screens are scheduled for the next implementation phase.

```bash
npm run typecheck  # Check TypeScript types
npm run build      # Create the production bundle in frontend/dist/
npm run preview    # Serve the built bundle locally
```

Run `npm run build` before `npm run preview`. Stop a running server with `Ctrl+C`.

## Current Development Status

| Component | Current state |
| --- | --- |
| Repository organization | Separate frontend, Flask backend, resource script, and documentation. |
| Documentation | Project purpose, folder responsibilities, and development boundaries documented. |
| Frontend foundation | Minimal application entry point and development/build configuration. |
| Visual design | Detailed screen design and implementation are pending. |
| Earth explorer, planner, analytics, and policy workspace | Planned; not implemented in this foundation step. |
| Scientific engine and Flask API | Generation, cyclic BESS dispatch, economics, carbon, evaluation, comparison, and exports implemented. |
| Optimization | Monthly HiGHS proposals and bounded hourly-checked candidate search. |
| Resource datasets | Synthetic annual demonstrations and validated input structure for user-provided annual series; no verified site dataset bundled. |
| Frontend/API integration | HTTP contracts documented; interactive planning screens are pending. |

The next interface phase will connect the explorer, planning, analytics, and policy screens to the API. Further scientific work includes calibrated marine inputs, equipment-specific curves, lifecycle emissions, and independently reviewed site assessments.
