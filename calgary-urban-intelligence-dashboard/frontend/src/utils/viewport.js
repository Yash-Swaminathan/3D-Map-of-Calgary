// One stable projection for the whole session; camera movement never shifts buildings.
export const ORIGIN = [51.045, -114.07];
export const TILE_SIZE = 0.01;
export function unproject(x, z) {
  return [ORIGIN[0] - z / 111320, ORIGIN[1] + x / (111320 * Math.cos(ORIGIN[0] * Math.PI / 180))];
}
export function tilesForBounds(bounds) {
  const [s, w, n, e] = bounds;
  const tiles = [];
  for (let y = Math.floor(s / TILE_SIZE); y < Math.ceil(n / TILE_SIZE); y++) {
    for (let x = Math.floor(w / TILE_SIZE); x < Math.ceil(e / TILE_SIZE); x++) {
      tiles.push([y, x, y + 1, x + 1].map(v => Number((v * TILE_SIZE).toFixed(5))));
    }
  }
  return tiles;
}
export function matchesFilters(building, filters) {
  if (!filters) return true;
  const normalized = v => String(v || '').toLowerCase().replace(/[_-]/g, ' ').trim();
  for (const [field, kind] of [['height', 'height'], ['floors', 'floors'], ['assessed_value', 'value']]) {
    const low = filters[`${kind}_min`] ?? filters[`min_${kind}`];
    const high = filters[`${kind}_max`] ?? filters[`max_${kind}`];
    if (low != null && (building[field] == null || building[field] < low)) return false;
    if (high != null && (building[field] == null || building[field] > high)) return false;
  }
  for (const [field, plural] of [['building_type', 'building_types'], ['zoning', 'zoning_types']]) {
    const choices = filters[field] != null ? [filters[field]] : filters[plural];
    if (choices?.length && !choices.map(normalized).includes(normalized(building[field]))) return false;
  }
  return true;
}
export function intersectsView(building, bounds) {
  const [s, w, n, e] = bounds;
  const points = building.footprint || [];
  if (points.length < 3) return building.latitude >= s && building.latitude <= n && building.longitude >= w && building.longitude <= e;
  if (points.some(([x, y]) => x >= w && x <= e && y >= s && y <= n)) return true;
  // Ray crossing for a rectangle corner inside the footprint.
  for (const [x, y] of [[w, s], [w, n], [e, s], [e, n]]) {
    let inside = false;
    for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
      const [xi, yi] = points[i], [xj, yj] = points[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    if (inside) return true;
  }
  // Footprint edges crossing a rectangle edge, including long thin polygons.
  for (let i = 0; i < points.length; i++) {
    const [x, y] = points[i], [xx, yy] = points[(i + 1) % points.length];
    for (const edge of [w, e]) {
      const t = (edge - x) / (xx - x);
      if (t >= 0 && t <= 1 && y + t * (yy - y) >= s && y + t * (yy - y) <= n) return true;
    }
    for (const edge of [s, n]) {
      const t = (edge - y) / (yy - y);
      if (t >= 0 && t <= 1 && x + t * (xx - x) >= w && x + t * (xx - x) <= e) return true;
    }
  }
  return false;
}
