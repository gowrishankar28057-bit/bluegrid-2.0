# BlueGrid 2.0 - Scientific Model Specification

This implementation follows *BlueGrid: Optimal Hybrid Renewable Energy Planner - System Architecture & Mathematical Formulation*, BlueGrid Development Team, 17 October 2026, pp. 4-6 and 8-10. The reference PDF is an engineering specification, not independent validation of this implementation. Equation numbers below refer to that document.

## Units and time boundaries

Generation and demand are kW; battery inventory is kWh. Every simulation step is exactly one hour, so step energy is power multiplied by one hour. The HTTP API accepts complete UTC calendar years: 8,760 hours, or 8,784 for a leap year. Monthly aggregation uses actual calendar boundaries. All rates and capacity factors are fractions, not percentages.

The system reports unmet energy explicitly. It does not dispatch a diesel generator. Diesel costs and emissions describe hypothetical coverage of unmet energy, separately from renewable energy served.

## Resource conversion

All conversion inputs must be finite. Negative irradiance, wind speed, wave height, and wave period are rejected. The model clamps generation capacity factors to [0, 1].

| Model | Implemented reference equation |
| --- | --- |
| Solar, Eq. 2 | `CF = clip((GHI / 1000) * 0.80 * (1 - 0.004 * max(T_air - 25, 0)), 0, 1)` |
| Wind, Eqs. 3-4 | Zero below 3 m/s or above 25 m/s; cubic `(v^3 - 3^3)/(11^3 - 3^3)` between 3 and 11 m/s; rated from 11 through 25 m/s; multiply by 0.88. |
| OTEC, Eqs. 5-8 | `x = max(T_surface - T_deep, 0)/22`; `CF = clip((x*x - 0.30*x)*0.92/0.70, 0, 1)`. |
| Wave, Eqs. 9-10 | `J = 0.49 * H_s^2 * T_p` kW/m; zero below 0.5 m or above 4 m; otherwise `CF = 0.85 * min(J/25, 1)`. |

Where measured surface temperature is absent, a causal, trailing 24-hour mean of air temperature supplies the PDF's SST proxy. The beginning of a series uses the available partial window. Deep-water temperature defaults to the reference's 7 degrees C. Both are simplifications; latitude, bathymetry, pipe losses, and marine engineering feasibility are not established by this formula.

Floating/onshore solar share the reference PV curve, and onshore/offshore wind share its turbine curve. Separate capacities and costs do not imply separately calibrated resource models. Parameterized pure functions support later calibration.

## Chronological battery dispatch

`B` is nominal battery kWh; usable inventory is `DoD * B`. Inventory is measured above the minimum allowable SOC, so its range is zero to usable inventory. Grid-side charge and load-side discharge are bounded by `C_rate * B` kW.

At the start of each hour:

```text
standing_loss = previous_inventory * hourly_self_discharge
available_inventory = previous_inventory - standing_loss
surplus = generation - demand
```

Surplus charges the battery up to the input-power and remaining-energy limits. A deficit discharges it up to the output-power and inventory limits. A step never both charges and discharges. Charge efficiency multiplies grid input; discharge output divides by discharge efficiency when reducing inventory. Remaining surplus is curtailed; remaining deficit is unmet.

The reference uses **0.015 self-discharge per hour** (p. 8). It is retained as a configurable reference default, with an explicit warning in API results. This is a large hourly loss and must not be confused with a monthly battery specification. Charge/discharge efficiencies 0.95, DoD 0.8, and C-rate 0.5 are implementation assumptions, not calibrated values established by the PDF.

Annual evaluations use a periodic inventory trajectory. A deterministic fixed-point calculation, with bounded iteration and bisection fallback, finds `initial_inventory = final_inventory`. This prevents an arbitrary initial charge from supplying free annual energy. The pure dispatch function also supports an explicitly noncyclic trajectory for numerical experiments.

Accounting identities, subject to floating-point tolerance:

```text
demand = renewable_energy_served + unmet_energy
generation = energy_served + curtailed_energy + storage_losses
             + final_inventory - initial_inventory
LPSP = unmet_energy / demand_energy
```

`loss_kwh` includes standing, charge-conversion, and discharge-conversion losses. Zero demand is defined as LPSP zero in the pure engine; the annual planning API requires positive total demand. Technology contributions describe available generation, not an attribution of battery losses or energy served to particular generators.

## Discounted cash flow

All monetary inputs use the declared currency. Default INR inputs are illustrative software assumptions, not quotations or extracted market prices. A project horizon, asset lifetimes, escalation rates, replacement fractions, and initial battery subsidy are explicit inputs.

The nominal rate follows Eq. 20:

```text
r_nom = (1 + r_real) * (1 + general_inflation) - 1
```

Eq. 21 is implemented with the O&M/diesel input interpreted as the **first end-of-year payment** `C1`. Payment in year `y` is `C1 * (1 + escalation)^(y-1)`.

```text
PV = C1 * [1 - ((1 + escalation)/(1 + r_nom))^n] / (r_nom - escalation)
PV = n*C1/(1 + r_nom)                         when r_nom = escalation
CRF = r_nom*(1 + r_nom)^n / [(1 + r_nom)^n - 1]
CRF = 1/n                                    when r_nom = 0
EAC = PV * CRF
```

Initial CAPEX is paid at time zero. Replacements occur at multiples of asset lifetime strictly before the project horizon. Generator replacement prices escalate with general inflation; battery replacement prices use the explicit battery-cost escalation rate. Battery subsidy applies once to initial battery CAPEX. Salvage value is zero. All asset costs are evaluated over the same project horizon, giving consistent coefficients for LP and scenario evaluation.

| Output | Definition |
| --- | --- |
| `capex` | Gross initial generation and storage investment. |
| `net_capex` | Initial investment after battery subsidy. |
| `project_npv` | Present cost of the renewable/storage system, excluding hypothetical diesel. |
| `annualized_cost` | Renewable/storage present cost multiplied by project CRF. |
| `lcoe` | Renewable/storage annualized cost divided by renewable energy served; `null` if no energy is served. |
| `diesel_backup_cost` | EAC of hypothetical diesel coverage for unmet energy. |
| `cost_of_service` | System EAC plus hypothetical diesel EAC, divided by total demand energy. |

Carbon output uses an illustrative baseline of 0.7 kg CO2/kWh and zero renewable operational emissions. It excludes lifecycle and embodied emissions. The pure carbon function accepts alternative factors and a carbon price; default carbon credits are zero.

## Two-tier optimization

1. A SciPy HiGHS LP proposes generation and storage capacities from monthly mean power and actual hours. Generation availability, bus balance, storage power/energy bounds, cyclic monthly SOC, annual unmet-energy allowance, and optional minimum combined wind capacity follow Eqs. 11-19. Average power terms are multiplied by month hours exactly once in SOC, reliability, and diesel cost calculations.
2. A deterministic, bounded candidate search examines the LP proposal, scaled and technology-specific alternatives, and a capacity grid. Candidates with insufficient theoretical annual generation are pruned. Every retained candidate undergoes the actual chronological hourly dispatch and wind-policy check.
3. Feasible candidates are ranked by LCOE, then gross CAPEX, as described on PDF p. 6. Full hourly output is retained for the best candidate.

Default upper bounds are ten times peak load per generator and fifty times peak load in battery kWh. They are search bounds, not engineering recommendations. Requests can override them or supply discrete axes. The API caps the candidate budget at 256 and reports how many candidates were considered, pruned, simulated, and accepted.

**Interpretation:** the output is the best feasible candidate found within the configured search. Neither a coarse monthly LP nor a truncated grid proves the global hourly optimum. No feasible candidate found does not prove that a site has no feasible design.

## Reference ambiguities resolved explicitly

- The expanded PDF formulation includes time factors; its canonical form omits some. The implementation uses explicit kW/kWh conversions consistently.
- The PDF's non-simultaneous LP charging/discharging argument does not exclude every degenerate optimum. The LP is a sizing heuristic; the implemented hourly dispatcher prohibits simultaneous flows directly.
- The historical NumPy version restriction in the PDF concerns its original environment. This implementation uses standard datetime processing and tests its own NumPy/SciPy environment rather than transferring that claim.
- The PDF's wave-cost correction and performance percentages are not used as validated cost inputs or performance guarantees.
- The synthetic Lakshadweep and Brest demonstrations establish no measured resource coverage or technology feasibility.
