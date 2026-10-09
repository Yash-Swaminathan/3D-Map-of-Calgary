// Scene units are meters for both building positions and footprints.
export function mapOrigin(bounds) {
  return [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2];
}
export function projectPoint(longitude, latitude, origin) {
  const x = (longitude - origin[1]) * 111320 * Math.cos(origin[0] * Math.PI / 180);
  const z = -(latitude - origin[0]) * 111320;
  return [x, 0, z];
}
export function buildingColor(type) {
  return ({ commercial: '#528fbc', residential: '#71a995', industrial: '#a093bf',
    'mixed use': '#d8ad66', mixed_use: '#d8ad66' })[type?.toLowerCase()] || '#a9b4ba';
}
