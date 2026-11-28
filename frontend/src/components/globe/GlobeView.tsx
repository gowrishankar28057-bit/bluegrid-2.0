import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber'
import {
  AdditiveBlending, BackSide, CanvasTexture, Quaternion, SRGBColorSpace,
  Spherical, TextureLoader, Vector3,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { Mesh } from 'three'
import { DEMO_LOCATIONS } from '../../data/locations'
import type { Location, LocationId } from '../../types/location'
import { GlobeFallback } from '../common/GlobeBoundary'
import { geographicPosition, graticulePositions, isSurfaceVisible } from './geo'
import earthMap from '../../assets/earth/daymap.jpg'

export interface ViewCommand { id: number; type: 'in' | 'out' | 'reset' | 'left' | 'right' | 'up' | 'down' }
interface Props {
  location: Location
  onSelect: (location: Location) => void
  rotating: boolean
  onInteract: () => void
  grid: boolean
  command: ViewCommand
  reducedMotion: boolean
}

const RADIUS = 1.8
const DISTANCE = 5.65
const MIN_DISTANCE = 4.25
const MAX_DISTANCE = 8.0
const ATMOSPHERE = {
  vertexShader: `varying vec3 vNormal; varying vec3 vPosition;
    void main(){ vec4 p=modelViewMatrix*vec4(position,1.0); vNormal=normalize(normalMatrix*normal); vPosition=p.xyz; gl_Position=projectionMatrix*p; }`,
  fragmentShader: `varying vec3 vNormal; varying vec3 vPosition;
    void main(){ float rim=pow(1.0-abs(dot(normalize(vNormal),normalize(-vPosition))),3.4); gl_FragColor=vec4(0.12,0.75,0.78,rim*0.57); }`,
}

function CameraRig({ location, rotating, onInteract, command, reducedMotion }: Omit<Props, 'onSelect' | 'grid'>) {
  const { camera, gl, invalidate } = useThree()
  const controls = useRef<OrbitControls | null>(null)
  const destination = useRef<Vector3 | null>(null)
  const currentLocation = useRef(location)
  useEffect(() => { currentLocation.current = location }, [location])
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement)
    orbit.enablePan = false
    orbit.enableDamping = true
    orbit.dampingFactor = 0.07
    orbit.rotateSpeed = 0.45
    orbit.zoomSpeed = 0.7
    orbit.minDistance = MIN_DISTANCE
    orbit.maxDistance = MAX_DISTANCE
    orbit.minPolarAngle = 0.15
    orbit.maxPolarAngle = Math.PI - 0.15
    orbit.autoRotateSpeed = 0.17
    const interact = () => { destination.current = null; onInteract() }
    const changed = () => invalidate()
    orbit.addEventListener('start', interact)
    orbit.addEventListener('change', changed)
    controls.current = orbit
    return () => {
      orbit.removeEventListener('start', interact)
      orbit.removeEventListener('change', changed)
      orbit.dispose()
      controls.current = null
    }
  }, [camera, gl, invalidate, onInteract])

  useEffect(() => {
    destination.current = geographicPosition(Math.min(location.latitude + 8, 70), location.longitude - 16, camera.position.length() || DISTANCE)
    invalidate()
  }, [location, camera, invalidate])

  useEffect(() => {
    const selected = currentLocation.current
    const distance = command.type === 'reset' ? DISTANCE
      : Math.min(MAX_DISTANCE, Math.max(MIN_DISTANCE, camera.position.length() * (command.type === 'in' ? 0.84 : 1.18)))
    if (['left', 'right', 'up', 'down'].includes(command.type)) {
      const spherical = new Spherical().setFromVector3(camera.position)
      if (command.type === 'left') spherical.theta -= .17
      if (command.type === 'right') spherical.theta += .17
      if (command.type === 'up') spherical.phi = Math.max(.15, spherical.phi - .13)
      if (command.type === 'down') spherical.phi = Math.min(Math.PI - .15, spherical.phi + .13)
      destination.current = new Vector3().setFromSpherical(spherical)
      invalidate()
      return
    }
    destination.current = command.type === 'reset'
      ? geographicPosition(Math.min(selected.latitude + 8, 70), selected.longitude - 16, distance)
      : camera.position.clone().normalize().multiplyScalar(distance)
    invalidate()
    // Selection has its own fly-to effect; view commands use the current selection.
  }, [command, camera, invalidate])

  useFrame((_, delta) => {
    const orbit = controls.current
    if (!orbit) return
    const target = destination.current
    if (target) {
      if (reducedMotion) camera.position.copy(target)
      else camera.position.lerp(target, 1 - Math.exp(-delta * 4))
      camera.lookAt(0, 0, 0)
      if (camera.position.distanceTo(target) < 0.003) destination.current = null
      invalidate()
    } else {
      orbit.autoRotate = rotating
      orbit.update(Math.min(delta, 0.05))
      if (rotating) invalidate()
    }
  })
  return null
}

function Earth({ grid, onReady }: { grid: boolean; onReady: () => void }) {
  const source = useLoader(TextureLoader, earthMap)
  const map = useMemo(() => {
    const image = source.image as HTMLImageElement
    // Limit GPU memory while preserving the unchanged, attributed source asset.
    const surface = document.createElement('canvas')
    surface.width = 2048
    surface.height = 1024
    const context = surface.getContext('2d')
    if (!context) return source
    context.drawImage(image, 0, 0, 2048, 1024)
    const texture = new CanvasTexture(surface)
    texture.colorSpace = SRGBColorSpace
    texture.anisotropy = 4
    return texture
  }, [source])
  const gridPositions = useMemo(() => graticulePositions(RADIUS + 0.006), [])
  useEffect(() => { onReady(); return () => { if (map !== source) map.dispose() } }, [map, source, onReady])
  return (
    <>
      <mesh>
        <sphereGeometry args={[RADIUS, 96, 64]} />
        <meshPhongMaterial map={map} color="#99bdc3" specular="#496e76" shininess={12} />
      </mesh>
      <mesh scale={1.022}>
        <sphereGeometry args={[RADIUS, 64, 48]} />
        <shaderMaterial {...ATMOSPHERE} side={BackSide} blending={AdditiveBlending} transparent depthWrite={false} />
      </mesh>
      {grid && <lineSegments>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[gridPositions, 3]} /></bufferGeometry>
        <lineBasicMaterial color="#a7eddf" transparent opacity={0.1} depthWrite={false} />
      </lineSegments>}
    </>
  )
}

function Stars() {
  const positions = useMemo(() => {
    const values = new Float32Array(520 * 3)
    let seed = 27
    const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 }
    for (let index = 0; index < 520; index++) {
      const y = random() * 2 - 1
      const theta = random() * Math.PI * 2
      const horizontal = Math.sqrt(1 - y * y)
      values.set([Math.cos(theta) * horizontal * 45, y * 45, Math.sin(theta) * horizontal * 45], index * 3)
    }
    return values
  }, [])
  return <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
    <pointsMaterial color="#a8c5cf" size={0.045} transparent opacity={0.48} depthWrite={false} />
  </points>
}

function LocationMarker({ location, selected, label, onSelect }: {
  location: Location; selected: boolean; label: HTMLButtonElement | null; onSelect: (location: Location) => void
}) {
  const { camera, size } = useThree()
  const pin = useRef<Mesh>(null)
  const position = useMemo(() => geographicPosition(location.latitude, location.longitude, RADIUS + 0.025), [location])
  const rotation = useMemo(() => new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), position.clone().normalize()), [position])
  const projected = useMemo(() => new Vector3(), [])
  useFrame(() => {
    if (!label) return
    projected.copy(position).project(camera)
    const visible = isSurfaceVisible(position, camera.position, RADIUS) && projected.z < 1
    label.hidden = !visible
    if (visible) {
      label.style.left = `${(projected.x * .5 + .5) * size.width}px`
      label.style.top = `${(-projected.y * .5 + .5) * size.height}px`
    }
  })
  return (
    <group position={position} quaternion={rotation}>
      <mesh ref={pin} onClick={event => {
        if (!isSurfaceVisible(position, camera.position, RADIUS)) return
        event.stopPropagation()
        onSelect(location)
      }}>
        <sphereGeometry args={[selected ? .027 : .02, 16, 12]} />
        <meshBasicMaterial color={selected ? '#a6ffe0' : '#b9d1df'} />
      </mesh>
      <mesh><ringGeometry args={[.043, .052, 40]} />
        <meshBasicMaterial color={selected ? '#a6ffe0' : '#a0bdce'} transparent opacity={selected ? .9 : .45} side={2} />
      </mesh>
      {selected && <mesh><ringGeometry args={[.075, .078, 40]} /><meshBasicMaterial color="#a6ffe0" transparent opacity={.32} side={2} /></mesh>}
    </group>
  )
}

function World({ labels, onReady, ...props }: Props & { labels: Record<LocationId, HTMLButtonElement | null>; onReady: () => void }) {
  return <>
    <ambientLight intensity={0.6} color="#92b5c9" />
    <directionalLight position={[-3, 5, -4]} intensity={2.7} color="#d8fff2" />
    <directionalLight position={[5, -1, 3]} intensity={0.18} color="#238dba" />
    <Stars />
    <Earth grid={props.grid} onReady={onReady} />
    {DEMO_LOCATIONS.map(location => <LocationMarker key={location.id} location={location} selected={location.id === props.location.id} label={labels[location.id]} onSelect={props.onSelect} />)}
    <CameraRig {...props} />
  </>
}

function UnsupportedCanvas({ onUnavailable }: { onUnavailable: () => void }) {
  useEffect(onUnavailable, [onUnavailable])
  return <GlobeFallback />
}

export default function GlobeView(props: Props) {
  const [ready, setReady] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  const [labels, setLabels] = useState<Record<LocationId, HTMLButtonElement | null>>({ lakshadweep: null, brest: null })
  const callbacks = useMemo(() => ({
    lakshadweep: (element: HTMLButtonElement | null) => setLabels(previous => previous.lakshadweep === element ? previous : { ...previous, lakshadweep: element }),
    brest: (element: HTMLButtonElement | null) => setLabels(previous => previous.brest === element ? previous : { ...previous, brest: element }),
  }), [])
  const onReady = useMemo(() => () => setReady(true), [])
  const onUnavailable = useMemo(() => () => setUnavailable(true), [])
  return (
    <div className="globe-renderer" data-ready={ready}>
      <Canvas frameloop="demand" dpr={[1, 1.5]} camera={{ position: [2.7, 1.75, -4.65], fov: 42, near: .1, far: 100 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }} fallback={<UnsupportedCanvas onUnavailable={onUnavailable} />}>
        <Suspense fallback={null}><World {...props} labels={labels} onReady={onReady} /></Suspense>
      </Canvas>
      {!ready && !unavailable && <div className="globe-loading" role="status"><span />Preparing your view of Earth</div>}
      {DEMO_LOCATIONS.map(location => <button key={location.id} ref={callbacks[location.id]} type="button"
        hidden={!ready} className={`map-label ${location.id === props.location.id ? 'is-selected' : ''}`}
        aria-label={`Select ${location.name}, ${location.country} on globe`} onClick={() => props.onSelect(location)}>
        <span className="map-label-line" /><span className="map-label-content"><strong>{location.name}</strong><small>{location.country}</small></span>
      </button>)}
    </div>
  )
}
