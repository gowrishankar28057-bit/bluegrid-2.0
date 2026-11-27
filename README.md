# BlueGrid 2.0

Physics-grounded renewable energy planning for island, coastal and regional energy systems.

## Problem

Choosing a renewable energy mix requires balancing investment cost, storage, seasonally changing resources, reliability and carbon impact. Ocean-energy resources may complement conventional renewable generation, but require location-specific validation.

## Architecture blueprint

The new implementation follows a modular system design informed by the team's previous scientific methodology. The code in this repository is newly authored; the previously handed-over project source is not included.

```text
frontend/       React + TypeScript + Vite (planning interface)
backend/        Flask application factory and REST APIs (next phase)
  app/
    engine/     generation, BESS, economics, carbon, scoring, configuration evaluation, optimization
    routes/     evaluation, optimization, comparison, reporting
  data/         resource datasets (source-provenance required)
  tests/        numerical and API verification
scripts/        data ingestion and preparation
docs/           engineering blueprint and modeling assumptions
```

## Approach

1. Select an explicitly supported geographic location.
2. Define target electrical load and candidate renewable/storage capacities.
3. Obtain traceable resource data; use prominently labeled synthetic inputs for demos.
4. Evaluate configurations with physics-based generation/storage models.
5. Optimize and report cost, unserved energy, reliability and carbon estimates with uncertainty disclosures.

The project targets solar, wind, OTEC, wave and BESS models, SciPy HiGHS optimization, 8,760-hour battery dispatch and exportable analytical reports. **Those backend engines are planned; do not confuse the UI-only preview with engineering validation.**

## Install and run

**Frontend (once the frontend phase is committed):**

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally http://localhost:5173/). Use `npm run build` for a production bundle.

**Backend (next development phase):**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Backend commands become operational **after** its implementation is committed. Current frontend uses an explicit synthetic demonstration preview and does not claim an operational Flask optimizer.

## Current status

- Folder structure and frontend: first development phase.
- Scientific backend, data validation, and real optimization: subsequent phases.
- Sample outputs: non-operational illustrations until connected to the tested backend.

## License

MIT, for the newly authored code in this repository. Third-party data/assets retain their separate terms.
