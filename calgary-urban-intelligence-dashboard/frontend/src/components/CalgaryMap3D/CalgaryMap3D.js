import React, { useEffect, useRef, useState } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import BuildingMesh from './BuildingMesh';
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

function Controls({ destination, onViewportChange }) {
  const { camera, gl, size } = useThree();
  const controls = useRef();
  const timer = useRef();
  const report = React.useCallback(() => {
    camera.updateMatrixWorld();
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
  }, [camera, onViewportChange]);
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

export default function CalgaryMap3D({ buildings, selectedBuilding, onBuildingClick, isLoading, onViewportChange }) {
  const origin = ORIGIN;
  const [destination, setDestination] = useState({ lat: ORIGIN[0], lon: ORIGIN[1], distance: 800 });
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
  const validBuildings = buildings.filter(b => Number.isFinite(b.latitude) && Number.isFinite(b.longitude));
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
          <gridHelper args={[100000, 1000, '#b9c9ce', '#d0dadd']} position={[0, -0.1, 0]} />
          {validBuildings.map(building => <BuildingMesh key={building.building_id || building.id}
            building={building} origin={origin} isSelected={selectedBuilding?.id === building.id}
            onClick={onBuildingClick} />)}
          <Controls destination={destination} onViewportChange={onViewportChange} />
        </Canvas>
      </MapErrorBoundary>
      <div className="map-tools"><span className="north-indicator">N &uarr;</span>
        <button className="secondary-button" onClick={() => setDestination({ lat: ORIGIN[0], lon: ORIGIN[1], distance: 800 })}>Reset view</button>
        <button className="secondary-button" onClick={() => setDestination({ lat: 51.03, lon: -114.07, distance: 40000 })}>City overview</button>
        <form onSubmit={navigate} className="map-location">
          <input aria-label="Map latitude, longitude" value={coordinates} onChange={e => setCoordinates(e.target.value)} />
          <button className="secondary-button" type="submit">Go</button>
          {coordinateError && <span role="alert">{coordinateError}</span>}
        </form></div>
      <div className="map-help">Drag to orbit | Scroll to zoom | Right-drag to pan<br />
        Select a building for details | Grid: 100 m<br />Double-click the ground to explore that location.<br />Buildings load as you move. Unknown heights use a display placeholder.</div>
      {isLoading && <div className="map-loading" role="status"><span className="loading-spinner" />Loading building data...</div>}
    </div>
  );
}
