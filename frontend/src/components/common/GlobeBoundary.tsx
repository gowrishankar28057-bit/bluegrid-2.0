import { Component } from 'react'
import type { ReactNode } from 'react'

export function GlobeFallback() {
  return (
    <div className="globe-fallback" role="status">
      <div className="fallback-planet" aria-hidden="true" />
      <p>The 3D view is unavailable on this device.</p>
      <span>You can still choose a location and open its planner.</span>
    </div>
  )
}

export class GlobeBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <GlobeFallback /> : this.props.children }
}
