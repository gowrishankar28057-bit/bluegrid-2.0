import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowRight, BatteryMedium, Check, ChevronRight, ExternalLink, Globe2,
  Grid3X3, Info, LocateFixed, MapPin, Minus, MousePointer2, Pause, Play,
  Plus, Search, Sun, Waves, Wind, X,
} from 'lucide-react'
import { DEMO_LOCATIONS, findLocations, LAKSHADWEEP } from './data/locations'
import type { Location } from './types/location'
import type { ViewCommand } from './components/globe/GlobeView'
import { coordinateLabel } from './data/coordinates'
import { GlobeBoundary } from './components/common/GlobeBoundary'
import { useReducedMotion } from './hooks/useReducedMotion'

const GlobeView = lazy(() => import('./components/globe/GlobeView'))
const PlanningPanel = lazy(() => import('./components/planner/PlanningPanel'))

function AboutDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])
  return <dialog ref={dialog} className="about-dialog" aria-labelledby="about-title"
    onCancel={event => { event.preventDefault(); onClose() }}>
    <button className="icon-button about-close" aria-label="Close about BlueGrid" onClick={onClose}><X size={20} /></button>
    <p className="eyebrow">THE BLUEGRID APPROACH</p>
    <h2 id="about-title">A closer look at<br />a cleaner energy future.</h2>
    <p>BlueGrid connects land-based renewables, ocean energy, and battery storage in one research planning environment.</p>
    <div className="about-steps">
      <div><Globe2 /><strong>Explore a location</strong><span>Lakshadweep and Brest are the two supported demonstrations.</span></div>
      <div><Waves /><strong>Shape an energy mix</strong><span>Use the planning panel to evaluate capacities with the Flask scientific engine.</span></div>
      <div><Info /><strong>Understand the assumptions</strong><span>Resources are synthetic, default costs are illustrative, and modeled outcomes require engineering review.</span></div>
    </div>
    <a className="text-link" href="https://github.com/gowrishankar28057-bit/bluegrid-2.0/blob/main/docs/MODELS.md" target="_blank" rel="noreferrer">Read the engineering methodology <ExternalLink size={15} /></a>
  </dialog>
}

export default function App() {
  const reducedMotion = useReducedMotion()
  const [location, setLocation] = useState<Location>(LAKSHADWEEP)
  const [query, setQuery] = useState('')
  const [rotating, setRotating] = useState(!reducedMotion)
  const [grid, setGrid] = useState(false)
  const [command, setCommand] = useState<ViewCommand>({ id: 0, type: 'reset' })
  const [planning, setPlanning] = useState(false)
  const [about, setAbout] = useState(false)
  const results = findLocations(query)
  const pauseOnInteraction = useCallback(() => setRotating(false), [])
  const selectLocation = useCallback((next: Location) => {
    setLocation(next)
    setQuery('')
    setRotating(false)
    setCommand(previous => ({ id: previous.id + 1, type: 'reset' }))
  }, [])
  useEffect(() => { if (reducedMotion) setRotating(false) }, [reducedMotion])
  function changeView(type: ViewCommand['type']) {
    setCommand(previous => ({ id: previous.id + 1, type }))
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#location-search">Skip to location selection</a>
      <header className="site-header">
        <a className="brand" href="#" aria-label="BlueGrid home" onClick={event => { event.preventDefault(); selectLocation(LAKSHADWEEP) }}>
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <span>BLUEGRID<span className="brand-version">2.0</span></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <span className="nav-active" aria-current="page"><Globe2 size={16} /> Earth explorer</span>
          <button onClick={() => setAbout(true)}>Our approach <ChevronRight size={14} /></button>
        </nav>
        <a className="project-link" href="https://github.com/gowrishankar28057-bit/bluegrid-2.0" target="_blank" rel="noreferrer">Research project <ExternalLink size={14} /></a>
      </header>

      <main className="explorer-layout">
        <section className="intro-panel" aria-labelledby="hero-title">
          <p className="eyebrow"><span /> RENEWABLE ENERGY MEETS THE OCEAN</p>
          <h1 id="hero-title">A blue planet.<br /><em>A cleaner future.</em></h1>
          <p className="intro-copy">A new perspective on renewable energy.<br className="desktop-break" /> Explore our coastlines. Discover the possibilities.<br className="desktop-break" /> Start with a place.</p>
          <button className="approach-link" onClick={() => setAbout(true)}>Discover BlueGrid <ArrowRight size={16} /></button>
        </section>

        <section className="globe-stage" aria-label="Interactive 3D Earth. Drag to rotate, scroll to zoom, or use the view controls."
          tabIndex={0} onKeyDown={event => {
            const keys: Record<string, ViewCommand['type']> = { '+': 'in', '=': 'in', '-': 'out', '0': 'reset', ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' }
            if (event.target === event.currentTarget && keys[event.key]) { event.preventDefault(); pauseOnInteraction(); changeView(keys[event.key]) }
          }}>
          <div className="orbital-guide" aria-hidden="true" />
          <div className="globe-topline"><span>EARTH EXPLORER</span><span className="scene-index">3D / INTERACTIVE</span></div>
          <GlobeBoundary>
            <Suspense fallback={<div className="globe-loading" role="status"><span />Preparing your view of Earth</div>}>
              <GlobeView location={location} onSelect={selectLocation} rotating={rotating} onInteract={pauseOnInteraction}
                grid={grid} command={command} reducedMotion={reducedMotion} />
            </Suspense>
          </GlobeBoundary>
          <div className="north-indicator" aria-hidden="true"><span>N</span><i /><span>S</span></div>
          <div className="globe-caption"><MousePointer2 size={14} /><span>Drag to rotate <i /> Scroll to zoom</span></div>
          <div className="globe-controls" role="toolbar" aria-label="Globe view controls">
            <button className="icon-button" aria-label="Zoom in" title="Zoom in (+)" onClick={() => changeView('in')}><Plus size={18} /></button>
            <button className="icon-button" aria-label="Zoom out" title="Zoom out (-)" onClick={() => changeView('out')}><Minus size={18} /></button>
            <span className="control-divider" />
            <button className="icon-button" aria-label="Reset globe view" title="Reset view (0)" onClick={() => changeView('reset')}><LocateFixed size={18} /></button>
            <button className={`icon-button ${grid ? 'is-on' : ''}`} aria-label="Geographic grid" aria-pressed={grid} title="Geographic grid" onClick={() => setGrid(previous => !previous)}><Grid3X3 size={17} /></button>
            <button className={`icon-button ${rotating ? 'is-on' : ''}`} aria-label={rotating ? 'Pause globe rotation' : 'Start globe rotation'} aria-pressed={rotating} title={rotating ? 'Pause rotation' : 'Auto-rotate'} onClick={() => setRotating(previous => !previous)}>{rotating ? <Pause size={16} /> : <Play size={16} />}</button>
          </div>
          <div className="coordinate-readout" aria-live="polite"><MapPin size={13} /><span>{coordinateLabel(location.latitude, 'latitude')}</span><b>/</b><span>{coordinateLabel(location.longitude, 'longitude')}</span></div>
        </section>

        <section className="location-panel" aria-labelledby="location-title">
          <div className="section-heading"><h2 id="location-title">Where shall we begin?</h2><span>{DEMO_LOCATIONS.length} demo locations</span></div>
          <div className="search-box"><Search size={17} aria-hidden="true" /><input id="location-search" type="search" placeholder="Search a location or country" aria-label="Search demonstration locations"
            value={query} maxLength={80} onChange={event => setQuery(event.target.value)}
            onKeyDown={event => { if (event.key === 'Enter' && results.length) { event.preventDefault(); selectLocation(results[0]) } }} />
            {query && <button aria-label="Clear location search" onClick={() => setQuery('')}><X size={16} /></button>}</div>
          <ul className="location-list" aria-label="Supported demonstration locations">
            {results.map(item => <li key={item.id}><button className={`location-option ${item.id === location.id ? 'is-selected' : ''}`}
              aria-pressed={item.id === location.id} onClick={() => selectLocation(item)}>
              <span className="location-glyph"><MapPin size={17} /></span><span><strong>{item.name}</strong><small>{item.country} <i /> {item.region}</small></span>
              {item.id === location.id ? <Check className="selection-check" size={18} /> : <ChevronRight className="location-chevron" size={17} />}
            </button></li>)}
          </ul>
          {!results.length && <p className="no-results" role="status">No supported location found. Try Lakshadweep, India, Brest, or France.</p>}
          <div className="location-summary" aria-live="polite"><span className="summary-label">YOUR STARTING POINT</span><strong>{location.name}, {location.country}</strong>
            <div className="technology-categories" aria-label="Demonstration technology categories"><span><Sun />Solar</span><span><Wind />Wind</span><span><Waves />Ocean</span><span><BatteryMedium />Storage</span></div>
          </div>
          <button className="primary-button" onClick={() => setPlanning(true)}>Start planning <ArrowRight size={18} /></button>
          <p className="coverage-note"><Info size={13} /><span>Demonstration locations. Site suitability requires verified resource data and engineering review.</span></p>
        </section>
      </main>
      <footer className="site-footer"><span>LAND. OCEAN. ONE ENERGY FUTURE.</span><span className="footer-note">Designed for exploration. Grounded in science.</span>
        <a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/" target="_blank" rel="noreferrer">Earth imagery: NASA Blue Marble, 2004 <ExternalLink size={12} /></a></footer>
      {about && <AboutDialog onClose={() => setAbout(false)} />}
      {planning && <Suspense fallback={<div className="panel-loading" role="status">Opening energy planner…</div>}><PlanningPanel location={location} onClose={() => setPlanning(false)} /></Suspense>}
    </div>
  )
}
