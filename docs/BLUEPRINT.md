# BlueGrid 2.0 - Engineering blueprint

## System boundary

- Site selection with explicit geographical coverage.
- Site load in kW; time-series demand when available.
- Physical resource conversion models (solar, wind, OTEC, wave).
- Battery energy storage chronological dispatch, 8,760-hour year.
- Economic analysis (CAPEX, OPEX, LCOE) and reliability (energy-not-served fraction/LPSP).
- SciPy HiGHS LP, candidate enumeration and hourly feasibility screening.
- React planning UI and Flask service interface.

## Backend reference modules

```text
backend/run.py
backend/app/__init__.py
backend/app/config.py
backend/app/data_loader.py
backend/app/engine/generation.py
backend/app/engine/bess.py
backend/app/engine/economics.py
backend/app/engine/carbon.py
backend/app/engine/scoring.py
backend/app/engine/config_eval.py
backend/app/engine/optimizer.py
backend/app/routes/api.py
backend/app/routes/export.py
backend/app/routes/main.py
backend/tests/
```

The scientific engine modules, application factory, configuration, data loader, and route modules above are implemented. Request validation and a bounded run cache provide the HTTP integration boundary. Detailed formulas, assumptions, and departures from the reference notation are recorded in [MODELS.md](MODELS.md); service contracts are in [API.md](API.md).

## Frontend scope

- Geographic site explorer: initial locations Lakshadweep, India and Brest, France.
- Planning inputs: electricity demand, renewables, battery.
- 3D Earth visualization and two pinned locations.
- Interactive Earth with attributed NASA imagery and two selectable demonstration locations.
- A connected planning form evaluates synthetic annual configurations through the Flask engine; full chart and policy screens remain pending.
- Implemented service endpoints `/api/evaluate`, `/api/optimize`, `/api/compare`, and cached JSON/CSV/PDF exports; frontend forms remain pending.

## Engineering guardrails

- Do not represent made-up inputs as measured site data.
- OTEC suitability must use site-appropriate temperature gradients.
- Battery self-discharge must be configurable with realistic documented defaults.
- Annual LPSP should equal unmet energy divided by demand energy, where defined.
- Determinism is reproducibility for fixed assumptions, not guaranteed predictive accuracy.
