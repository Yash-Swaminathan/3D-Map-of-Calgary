import React, { useMemo, useState, useEffect } from 'react';
import { createBuildingGeometry } from '../../utils/buildingGeometry';
import { projectPoint, buildingColor } from '../../utils/mapCoordinates';

export default function BuildingMesh({ building, origin, isSelected, onClick }) {
  const [hovered, setHovered] = useState(false);
  const position = useMemo(() => projectPoint(building.longitude, building.latitude, origin), [building.longitude, building.latitude, origin]);
  const geometry = useMemo(() => createBuildingGeometry(building),
    [building]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => { document.body.style.cursor = ''; }, []);
  return (
    <mesh position={position} geometry={geometry}
      onClick={event => { event.stopPropagation(); onClick(building); }}
      onPointerOver={event => { event.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = ''; }}>
      <meshStandardMaterial color={isSelected ? '#e49d62' : hovered ? '#79c5d2' : buildingColor(building.building_type)}
        roughness={0.72} metalness={0.05} />
    </mesh>
  );
}
