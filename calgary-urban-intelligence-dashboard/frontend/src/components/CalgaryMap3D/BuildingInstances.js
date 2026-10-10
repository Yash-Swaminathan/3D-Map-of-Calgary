import React, { useLayoutEffect, useRef } from 'react';
import { Matrix4, Vector3, Quaternion, Color } from 'three';
import { projectPoint, buildingColor } from '../../utils/mapCoordinates';

// One draw call for thousands of buildings in wider views. Detailed footprints
// return automatically when fewer buildings are visible.
export default function BuildingInstances({ buildings, origin, selectedBuilding, onBuildingClick }) {
  const mesh = useRef();
  useLayoutEffect(() => {
    const matrix = new Matrix4(), rotation = new Quaternion();
    buildings.forEach((building, index) => {
      const points = building.footprint?.map(p => projectPoint(p[0], p[1], origin)) || [];
      const center = projectPoint(building.longitude, building.latitude, origin);
      const xs = points.map(p => p[0]), zs = points.map(p => p[2]);
      const left = points.length ? Math.min(...xs) : center[0] - 5;
      const right = points.length ? Math.max(...xs) : center[0] + 5;
      const front = points.length ? Math.min(...zs) : center[2] - 5;
      const back = points.length ? Math.max(...zs) : center[2] + 5;
      const height = building.height > 0 ? building.height : building.floors > 0 ? building.floors * 3.5 : 8;
      matrix.compose(new Vector3((left + right) / 2, height / 2, (front + back) / 2), rotation,
        new Vector3(Math.max(right - left, 1), height, Math.max(back - front, 1)));
      mesh.current.setMatrixAt(index, matrix);
      mesh.current.setColorAt(index, new Color(building.id === selectedBuilding?.id ? '#f3c568' : buildingColor(building.building_type)));
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true;
    mesh.current.computeBoundingSphere();
  }, [buildings, origin, selectedBuilding]);
  return <instancedMesh ref={mesh} args={[null, null, buildings.length]} onClick={event => {
    event.stopPropagation();
    if (event.instanceId != null) onBuildingClick(buildings[event.instanceId]);
  }}>
    <boxGeometry args={[1, 1, 1]} />
    <meshStandardMaterial roughness={0.85} />
  </instancedMesh>;
}
