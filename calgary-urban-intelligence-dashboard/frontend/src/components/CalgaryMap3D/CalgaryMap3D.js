import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import BuildingMesh from './BuildingMesh';
import BuildingInstances from './BuildingInstances';
import { Color } from 'three';
import { Raycaster, Vector2, Vector3, Plane } from 'three';
import { ORIGIN, unproject } from '../../utils/viewport';
import { projectPoint } from '../../utils/mapCoordinates';

class MapErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div className="map-empty"><strong>3D rendering is unavailable</strong>
      <p>This browser could not create a WebGL context. Try a browser with hardware acceleration enabled.</p></div>;
    return this.props.children;
  }
}

function Controls({ destination, onViewportChange, onViewCenterChange }) {
  const { camera, gl, size } = useThree();
  const controls = useRef();
  const timer = useRef();
  const report = React.useCallback(() => {
    camera.updateMatrixWorld();
    if (controls.current) onViewCenterChange(unproject(controls.current.target.x, controls.current.target.z));
    const ray = new Raycaster();
    const ground = new Plane(new Vector3(0, 1, 0), 0);
    const points = [];
    for (const [x, y] of [[-1, -1], [-1, 1], [1, -1], [1, 1]]) {
      ray.setFromCamera(new Vector2(x, y), camera);
      const hit = ray.ray.intersectPlane(ground, new Vector3());
      if (hit) points.push(unproject(hit.x, hit.z));
    }
    if (points.length === 4) onViewportChange([
      Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1])),
      Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))
    ].map(v => Number(v.toFixed(6))));
  }, [camera, onViewportChange, onViewCenterChange]);
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement);
    controls.current = orbit;
    orbit.enableDamping = true;
    orbit.screenSpacePanning = false;
    orbit.maxPolarAngle = Math.PI / 3;
    orbit.minDistance = 60;
    orbit.maxDistance = 80000;
    const changed = () => { clearTimeout(timer.current); timer.current = setTimeout(report, 450); };
    orbit.addEventListener('change', changed);
    return () => { clearTimeout(timer.current); orbit.removeEventListener('change', changed); orbit.dispose(); };
  }, [camera, gl, report]);
  useEffect(() => {
    const target = projectPoint(destination.lon, destination.lat, ORIGIN);
    const d = destination.distance;
    camera.position.set(target[0] + d * 0.25, d, target[2] + d * 0.45);
    controls.current.target.set(...target);
    controls.current.update();
    report();
  }, [camera, destination, report]);
  useEffect(() => { report(); }, [size.width, size.height, report]);
  useFrame(() => controls.current?.update());
  return null;
}

export default function CalgaryMap3D({ buildings, selectedBuilding, onBuildingClick, isLoading, onViewportChange, densityCells = [] }) {
  const origin = ORIGIN;
  const viewCenter = useRef(ORIGIN);
  const onViewCenterChange = React.useCallback(center => { viewCenter.current = center; }, []);
  const [destination, setDestination] = useState({ lat: ORIGIN[0], lon: ORIGIN[1], distance: 2400 });
  const [coordinates, setCoordinates] = useState('51.045, -114.070');
  const [coordinateError, setCoordinateError] = useState('');
  const navigate = event => {
    event.preventDefault();
    const values = coordinates.split(',').map(Number);
    if (values.length !== 2 || !values.every(Number.isFinite) || values[0] < 50.8 || values[0] > 51.3 || values[1] < -114.4 || values[1] > -113.8) {
      setCoordinateError('Enter latitude, longitude within Calgary.'); return;
    }
    setCoordinateError('');
    setDestination({ lat: values[0], lon: values[1], distance: 800 });
  };
  const simplified = buildings.length > 2000;
  const validBuildings = useMemo(() => buildings.filter(b => Number.isFinite(b.latitude) && Number.isFinite(b.longitude)), [buildings]);
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#edf1f2' }}>
      <MapErrorBoundary>
        <Canvas camera={{ position: [600, 800, 600], fov: 42, near: 1, far: 200000 }} dpr={[1, 1.5]}>
          <color attach="background" args={['#edf1f2']} />
          <ambientLight intensity={0.85} />
          <directionalLight position={[400, 900, 300]} intensity={1.7} />
          <directionalLight position={[-200, 300, -100]} intensity={0.35} />
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.3, 0]} onDoubleClick={event => {
            const [lat, lon] = unproject(event.point.x, event.point.z);
            setDestination({ lat, lon, distance: 800 });
          }}>
            <planeGeometry args={[100000, 100000]} />
            <meshStandardMaterial color="#e2e8e9" roughness={1} />
          </mesh>
          {!densityCells.length && <gridHelper args={[100000, 1000, '#b9c9ce', '#d0dadd']} position={[0, -0.1, 0]} />}
          {simplified ? <BuildingInstances buildings={validBuildings} origin={origin} selectedBuilding={selectedBuilding} onBuildingClick={onBuildingClick} /> : validBuildings.map(building => <BuildingMesh key={building.building_id || building.id}
            building={building} origin={origin} isSelected={selectedBuilding?.id === building.id}
            onClick={onBuildingClick} />)}
          {densityCells.map((cell, index) => {
            const [south, west, north, east] = cell.bounds;
            const a = projectPoint(west, south, origin), b = projectPoint(east, north, origin);
            const fraction = cell.count == null ? 0 : cell.count / Math.max(1, ...densityCells.map(c => c.count || 0));
            const color = cell.count == null ? '#a9b4ba' : new Color('#d6e9ea').lerp(new Color('#19586f'), Math.sqrt(fraction));
            return <mesh key={index} position={[(a[0] + b[0]) / 2, 1, (a[2] + b[2]) / 2]} rotation={[-Math.PI / 2, 0, 0]}
              onClick={event => { event.stopPropagation(); setDestination({ lat: (south + north) / 2, lon: (west + east) / 2, distance: 2400 }); }}>
              <planeGeometry args={[Math.abs(b[0] - a[0]) * 0.96, Math.abs(b[2] - a[2]) * 0.96]} />
              <meshBasicMaterial color={color} transparent depthTest={false} depthWrite={false} opacity={cell.count === 0 ? 0.2 : 0.85} />
            </mesh>;
          })}
          <Controls destination={destination} onViewportChange={onViewportChange} onViewCenterChange={onViewCenterChange} />
        </Canvas>
      </MapErrorBoundary>
      <div className="map-tools"><span className="north-indicator">N &uarr;</span>
        <button className="secondary-button" onClick={() => setDestination({ lat: ORIGIN[0], lon: ORIGIN[1], distance: 2400 })}>Reset view</button>
        <button className="secondary-button" onClick={() => setDestination({ lat: viewCenter.current[0], lon: viewCenter.current[1], distance: 4000 })}>Wider area</button>
        <button className="secondary-button" onClick={() => setDestination({ lat: 51.03, lon: -114.07, distance: 40000 })}>City overview</button>
        <form onSubmit={navigate} className="map-location">
          <input aria-label="Map latitude, longitude" value={coordinates} onChange={e => setCoordinates(e.target.value)} />
          <button className="secondary-button" type="submit">Go</button>
          {coordinateError && <span role="alert">{coordinateError}</span>}
        </form></div>
      <div className="map-help">Drag to orbit | Scroll to zoom | Right-drag to pan<br />
        Select a building for details | Grid: 100 m<br />{simplified ? 'Simplified building shapes at this scale.' : densityCells.length ? 'Darker cells contain more roof records.' : 'Detailed building footprints.'}<br />Double-click the ground to explore that location.<br />Buildings load as you move. Unknown heights use a display placeholder.</div>
      {isLoading && <div className="map-loading" role="status"><span className="loading-spinner" />Loading building data...</div>}
    </div>
  );
}
