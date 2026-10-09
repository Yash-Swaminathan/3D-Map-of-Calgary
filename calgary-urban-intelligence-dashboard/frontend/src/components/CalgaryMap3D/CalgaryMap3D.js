import React, { useMemo, useEffect, useRef, useState } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import BuildingMesh from './BuildingMesh';
import { mapOrigin, projectPoint } from '../../utils/mapCoordinates';

class MapErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div className="map-empty"><strong>3D rendering is unavailable</strong>
      <p>This browser could not create a WebGL context. Try a browser with hardware acceleration enabled.</p></div>;
    return this.props.children;
  }
}

function Controls({ distance, reset }) {
  const { camera, gl } = useThree();
  const controls = useRef();
  useEffect(() => {
    controls.current = new OrbitControls(camera, gl.domElement);
    controls.current.enableDamping = true;
    controls.current.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.current.minDistance = 30;
    controls.current.maxDistance = distance * 4;
    return () => controls.current.dispose();
  }, [camera, gl, distance]);
  useEffect(() => {
    camera.position.set(distance * 0.65, distance * 0.8, distance * 0.65);
    camera.lookAt(0, 0, 0);
    if (controls.current) {
      controls.current.target.set(0, 0, 0);
      controls.current.update();
    }
  }, [camera, distance, reset]);
  useFrame(() => controls.current?.update());
  return null;
}

export default function CalgaryMap3D({ buildings, selectedBuilding, onBuildingClick, isLoading, bounds }) {
  const origin = useMemo(() => mapOrigin(bounds), [bounds]);
  const [reset, setReset] = useState(0);
  const extent = useMemo(() => {
    const corner = projectPoint(bounds[3], bounds[2], origin);
    return Math.max(Math.abs(corner[0]) * 2, Math.abs(corner[2]) * 2, 300);
  }, [bounds, origin]);
  const validBuildings = buildings.filter(b => Number.isFinite(b.latitude) && Number.isFinite(b.longitude));
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#edf1f2' }}>
      <MapErrorBoundary>
        <Canvas camera={{ position: [600, 800, 600], fov: 42, near: 1, far: 10000 }} dpr={[1, 1.5]}>
          <color attach="background" args={['#edf1f2']} />
          <ambientLight intensity={0.85} />
          <directionalLight position={[400, 900, 300]} intensity={1.7} />
          <directionalLight position={[-200, 300, -100]} intensity={0.35} />
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.3, 0]}>
            <planeGeometry args={[extent * 1.5, extent * 1.5]} />
            <meshStandardMaterial color="#e2e8e9" roughness={1} />
          </mesh>
          <gridHelper args={[Math.ceil(extent / 100) * 100, Math.ceil(extent / 100), '#b9c9ce', '#d0dadd']} position={[0, -0.1, 0]} />
          {validBuildings.map(building => <BuildingMesh key={building.building_id || building.id}
            building={building} origin={origin} isSelected={selectedBuilding?.id === building.id}
            onClick={onBuildingClick} />)}
          <Controls distance={extent * 1.6} reset={reset} />
        </Canvas>
      </MapErrorBoundary>
      <div className="map-tools"><span className="north-indicator">N &uarr;</span>
        <button className="secondary-button" onClick={() => setReset(value => value + 1)}>Reset view</button></div>
      <div className="map-help">Drag to orbit | Scroll to zoom | Right-drag to pan<br />
        Select a building for details | Grid: 100 m<br />Unknown heights use a display placeholder.</div>
      {isLoading && <div className="map-loading" role="status"><span className="loading-spinner" />Loading building data...</div>}
    </div>
  );
}
