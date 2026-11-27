# BlueGrid 2.0

A renewable energy planning platform for island and coastal systems, integrating land-based renewables, ocean energy, and battery storage.

**Development stage:** project structure and frontend foundation. The planning screens and scientific backend are scheduled for subsequent implementation. Licensed under [MIT](LICENSE).

## Problem Statement

Solar, wind, and ocean resources vary over time. Selecting a renewable energy mix requires balancing those resources against electricity demand, storage losses, investment costs, and reliability requirements.

BlueGrid 2.0 will help engineers, researchers, investors, and policymakers compare scenarios through a geographic explorer, planning workspace, analytics, and policy workspace. Planned technologies include floating solar, onshore solar, onshore wind, offshore wind, ocean thermal energy conversion (OTEC), wave energy, and battery energy storage systems (BESS).

The engineering reference, *BlueGrid: Optimal Hybrid Renewable Energy Planner - System Architecture & Mathematical Formulation* (BlueGrid Development Team, 17 October 2026), describes a Lakshadweep-focused system. Lakshadweep, India, and Brest, France, are planned BlueGrid 2.0 demonstration locations, subject to data and feasibility checks. Worldwide resource coverage is not established.

## Architecture Blueprint

The repository separates presentation, scientific computation, data preparation, and documentation. The frontend will collect inputs and display API responses; the future backend will own physical models, dispatch, economics, reliability checks, and optimization.

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
│   │   ├── engine/                # Reserved for physics and economics modules
│   │   └── routes/                # Reserved for Flask API routes
│   ├── data/                      # Reserved for traceable resource datasets
│   └── tests/                     # Reserved for numerical and API verification
├── scripts/                       # Future ingestion and preprocessing utilities
├── docs/
│   └── BLUEPRINT.md               # Engineering boundaries and planned modules
├── .gitignore
├── README.md
└── LICENSE
```

Empty directories contain `.gitkeep` files so Git retains the structure. These placeholders do not implement backend services or scientific models.

| Area | Responsibility |
| --- | --- |
| `frontend/` | Inputs, navigation, and visualizations. |
| `backend/` | Future calculations, validation, and API responses. |
| `scripts/` | Future data preparation with recorded provenance. |
| `docs/` | Architecture and modeling assumptions. |

Frontend images belong in `frontend/src/assets/`; assets requiring a stable public URL belong in `frontend/public/`.

## Engineering Approach

The planned engineering workflow follows the reference architecture and modeling discussion (pp. 3-6 and 8-10):

1. Select a supported location and obtain traceable resource and technology inputs.
2. Define electricity demand in kW, candidate generation capacities in kW, battery energy in kWh, and reliability preferences.
3. Convert resource time series into technology-specific generation availability.
4. Evaluate generation and chronological battery dispatch, including energy limits, conversion losses, curtailment, and unmet demand.
5. Propose capacity mixes through monthly linear programming and screen alternatives using hourly dispatch over a defined year.
6. Compare costs, energy served, unmet energy, renewable contribution, and carbon estimates with explicit assumptions.

Planned economic outputs include capital expenditure (CAPEX), operating expenditure (OPEX), and levelized cost of energy (LCOE). The reference expresses loss of power supply probability (LPSP) as unmet energy divided by demand energy. These models and their units, defaults, and numerical behavior require verification before operational use in BlueGrid 2.0.

Future previews will label synthetic data and distinguish it from optimized configurations or validated assessments. The [engineering blueprint](docs/BLUEPRINT.md) records implementation boundaries.

## Technology Stack

| Layer | Technology | Status |
| --- | --- | --- |
| Frontend | React, TypeScript, [Vite](https://vite.dev/guide/) | Starter foundation |
| Styling | [Tailwind CSS](https://tailwindcss.com/docs/installation/using-vite) | Foundation configuration |
| 3D geographic interface | React Three Fiber and Three.js | Planned |
| Charts | Recharts | Planned |
| Icons | Lucide React | Planned |
| Scientific API | Python and Flask | Planned |
| Numerical processing | NumPy and Pandas | Planned |
| Optimization | SciPy with the HiGHS solver | Planned |

The reference used Flask templates and vanilla JavaScript. BlueGrid 2.0 adopts a separate React frontend. Backend dependency versions will be verified during implementation.

## Installation

Install Git, Node.js 24 LTS, and npm, then clone the repository:

```bash
git clone https://github.com/gowrishankar28057-bit/bluegrid-2.0.git
cd bluegrid-2.0/frontend
npm ci
```

For an existing checkout, run `npm ci` inside `frontend/`. The lockfile keeps installations reproducible. No backend or API credentials are required for the starter.

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
| Repository organization | Frontend structure and existing backend placeholders organized. |
| Documentation | Project purpose, folder responsibilities, and development boundaries documented. |
| Frontend foundation | Minimal application entry point and development/build configuration. |
| Visual design | Detailed screen design and implementation are pending. |
| Earth explorer, planner, analytics, and policy workspace | Planned; not implemented in this foundation step. |
| Scientific engine and Flask API | Placeholder directories only; no connected optimizer. |
| Resource datasets and engineering results | No validated site dataset or scientific results delivered in this step. |

The next frontend phase will implement the explorer, planning, analytics, and policy screens within this structure. Backend work will follow with documented assumptions, data provenance, numerical verification, and tested service contracts.
