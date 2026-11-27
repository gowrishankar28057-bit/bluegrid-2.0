# BlueGrid 2.0 — Engineering blueprint

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

The module separation follows the supplied technical project document. It is a blueprint, not a claim that these Python modules exist yet.

## Frontend scope

- Geographic site explorer: initial locations Lakshadweep, India and Brest, France.
- Planning inputs: electricity demand, renewables, battery.
- 3D Earth visualization and two pinned locations.
- Preview of a synthetic 24-hour energy balance, **not** backend optimization.
- Future integration point for `/api/evaluate`, `/api/optimize`, and reporting.

## Engineering guardrails

- Do not represent made-up inputs as measured site data.
- OTEC suitability must use site-appropriate temperature gradients.
- Battery self-discharge must be configurable with realistic documented defaults.
- Annual LPSP should equal unmet energy divided by demand energy, where defined.
- Determinism is reproducibility for fixed assumptions, not guaranteed predictive accuracy.
