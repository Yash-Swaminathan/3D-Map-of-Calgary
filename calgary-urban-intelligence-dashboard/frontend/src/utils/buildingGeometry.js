import * as THREE from 'three';
import { projectPoint } from './mapCoordinates';

export function createBuildingGeometry(building) {
    // Unknown heights use a visible placeholder; they are never stored as measurements.
    const height = Math.max(building.height ?? (building.floors ? building.floors * 3.5 : 8), 1);
    const footprint = building.footprint?.filter(p => Array.isArray(p) && p.length >= 2 && p.every(Number.isFinite));
    if (footprint?.length >= 3) {
      const localOrigin = [building.latitude, building.longitude];
      const points = footprint.map(p => {
        const projected = projectPoint(p[0], p[1], localOrigin);
        return new THREE.Vector2(projected[0], -projected[2]);
      });
      const shape = new THREE.Shape(points);
      const extruded = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false });
      // GeoJSON lies in the XY plane; rotate so roofs are horizontal and height points up.
      extruded.rotateX(-Math.PI / 2);
      return extruded;
    }
    const box = new THREE.BoxGeometry(10, height, 10);
    box.translate(0, height / 2, 0);
    return box;
}
