export function formatFilters(filters) {
  if (!filters) return 'No filters';
  const labels = { height_min: 'Height >= ', min_height: 'Height >= ', height_max: 'Height <= ', max_height: 'Height <= ',
    value_min: 'Assessed value >= ', min_value: 'Assessed value >= ', value_max: 'Assessed value <= ', max_value: 'Assessed value <= ',
    floors_min: 'Floors >= ', min_floors: 'Floors >= ', floors_max: 'Floors <= ', max_floors: 'Floors <= ',
    building_type: 'Use:', building_types: 'Use:', zoning: 'Zoning:', zoning_types: 'Zoning:' };
  return Object.entries(filters).map(([key, value]) => {
    const formatted = key.includes('height') ? `${Number(value).toLocaleString('en-CA', { maximumFractionDigits: 2 })} m` :
      key.includes('value') ? new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(value) :
      Array.isArray(value) ? value.join(', ') : String(value).replaceAll('_', ' ');
    return `${labels[key] || key} ${formatted}`;
  }).join(' | ');
}
