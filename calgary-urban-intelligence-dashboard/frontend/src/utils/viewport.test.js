import { tilesForBounds, unproject, intersectsView, matchesFilters, ORIGIN } from './viewport';

test('navigation requests different tiles and wider views include more tiles', () => {
  const initial = tilesForBounds([51.042, -114.075, 51.048, -114.065]);
  const moved = tilesForBounds([51.082, -114.105, 51.088, -114.095]);
  expect(moved).not.toEqual(initial);
  expect(tilesForBounds([51.035, -114.09, 51.06, -114.045]).length).toBeGreaterThan(initial.length);
  expect(unproject(0, 0)).toEqual(ORIGIN);
});
test('boundary-crossing footprint is visible even with center outside', () => {
  const b = { latitude: 51.041, longitude: -114.07, footprint: [[-114.071,51.041],[-114.069,51.041],[-114.069,51.043],[-114.071,51.043]] };
  expect(intersectsView(b, [51.042,-114.075,51.048,-114.065])).toBe(true);
  expect(intersectsView(b, [51.08,-114.075,51.09,-114.065])).toBe(false);
});
test('filters persist across incoming data and unknowns never match', () => {
  expect(matchesFilters({height: null}, {height_min: 10})).toBe(false);
  expect(matchesFilters({height: 0}, {height_max: 0})).toBe(true);
  expect(matchesFilters({height: 40, building_type: 'Mixed Use'}, {min_height: 30, building_type: 'mixed_use'})).toBe(true);
});
