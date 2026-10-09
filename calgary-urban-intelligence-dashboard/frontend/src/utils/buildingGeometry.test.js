import { createBuildingGeometry } from './buildingGeometry';
import { mapOrigin, projectPoint } from './mapCoordinates';
import { formatFilters } from './formatFilters';

const building = { latitude: 51.045, longitude: -114.07, height: 40,
  footprint: [[-114.07005,51.04495],[-114.06995,51.04495],[-114.06995,51.04505],[-114.07005,51.04505],[-114.07005,51.04495]] };

test('extruded footprints sit on the ground and extend vertically by their meter height', () => {
  const geometry = createBuildingGeometry(building);
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  expect(box.min.y).toBeCloseTo(0, 4);
  expect(box.max.y).toBeCloseTo(40, 4);
  expect(box.max.x - box.min.x).toBeCloseTo(6.9985, 1);
  expect(box.max.z - box.min.z).toBeCloseTo(11.132, 2);
  geometry.dispose();
});

test('position projection uses a fixed area origin across filtering and respects north', () => {
  const origin = mapOrigin([51.042, -114.075, 51.048, -114.065]);
  expect(projectPoint(-114.07,51.045,origin)[0]).toBeCloseTo(0, 6);
  expect(projectPoint(-114.07,51.046,origin)[2]).toBeCloseTo(-111.32, 2);
});

test('unknown-height boxes use a stable display placeholder without changing source data', () => {
  const data = { latitude: 51.045, longitude: -114.07, height: null };
  const geometry = createBuildingGeometry(data);
  geometry.computeBoundingBox();
  expect(geometry.boundingBox.min.y).toBe(0);
  expect(geometry.boundingBox.max.y).toBe(8);
  expect(data.height).toBeNull();
  geometry.dispose();
});

test('filter labels show actual dictionary criteria with consistent height units and CAD values', () => {
  const text = formatFilters({ height_min: 30.48, value_max: 500000, zoning: 'CC-X' });
  expect(text).toContain('30.48 m');
  expect(text).toContain('500,000');
  expect(text).toContain('CC-X');
  expect(text).not.toContain('undefined');
});
