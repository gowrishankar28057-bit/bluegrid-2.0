# BlueGrid Earth Explorer

The Earth explorer is a JavaScript/WebGL interface authored in React and TypeScript. React Three Fiber renders a real Three.js sphere with locally served NASA imagery, atmospheric shading, geographically positioned markers, and a selectable latitude/longitude grid.

## Running the interface

Install Node.js 24 LTS, then run `npm ci` and `npm run dev` inside `frontend/`. Open the URL printed by Vite, normally `http://127.0.0.1:5173`.

For configuration evaluation, start the Flask backend separately using the commands in [API.md](API.md). Vite forwards `/api` requests to `http://127.0.0.1:5000`. The planning panel displays an explicit error if that service is unavailable; it does not substitute fabricated results.

## Interaction

- Drag the Earth to rotate it; use the wheel, pinch gesture, or zoom buttons to change distance.
- Select a globe marker or a location in the list. Search accepts place names, countries, and regions. Enter selects the first matching supported location.
- Reset returns the camera to the selected location. The rotation control pauses or resumes orbiting. The grid control toggles geographic reference lines.
- With the globe region focused, arrow keys rotate, `+`/`-` zoom, and `0` resets. Location selection and all toolbar controls are also available through the keyboard.
- Automatic rotation starts paused when the device requests reduced motion. Selecting a location or dragging also pauses it.
- Start planning opens a keyboard-accessible modal for demand, solar, wind, OTEC, and battery inputs. Its results come from `/api/evaluate`, with the synthetic resource and illustrative cost labels preserved.

WebGL2 support is required for the 3D view. A fallback message leaves the location list and planner usable when rendering is unavailable. Mobile layouts preserve the same selection and planning interactions.

## Scope and assets

Lakshadweep and Brest are the supported demonstration locations. The navigable Earth is geographic context, not evidence of worldwide resource coverage. Technology categories do not establish site feasibility.

The map is the historical NASA Blue Marble July 2004 composite, served locally rather than fetched at runtime. Its exact source, original credits, and usage notes are in [the asset source record](../frontend/src/assets/earth/SOURCE.md). The renderer limits texture upload to 2048 x 1024 pixels to bound GPU memory while retaining the unchanged source file. The Manrope font is served locally through Fontsource; its OFL license is included in `frontend/public/licenses/`.

The 3D renderer and planning panel load in separate JavaScript chunks. Rendering stops when the camera is idle and automatic rotation is paused. Device pixel ratio is capped at 1.5. No resource measurements are fetched by the globe itself.

## Verification

From `frontend/`:

```bash
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser suite starts Vite and the backend when they are not already running. Install backend requirements first; `BLUEGRID_PYTHON` can select a Python interpreter, otherwise an existing backend virtual environment is preferred. Unit tests cover geographic alignment, search, request validation, accessible planning controls, real response rendering, and error/cancellation behavior. Browser tests cover actual WebGL rendering, dragging, geographic selection, view controls, mobile/reduced-motion behavior, and a real Flask evaluation.

Full analytics and policy screens remain a subsequent interface phase.
