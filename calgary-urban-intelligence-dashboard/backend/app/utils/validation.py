"""Validation shared by live queries and saved projects."""
import math

FILTER_KEYS = {
    'height_min', 'height_max', 'floors_min', 'floors_max', 'value_min', 'value_max',
    'building_type', 'building_types', 'zoning', 'zoning_types',
    'min_height', 'max_height', 'min_floors', 'max_floors', 'min_value', 'max_value',
}

def validate_bounds(value):
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('Bounds must contain south, west, north, east coordinates.')
    try:
        bounds = tuple(float(x) for x in value)
    except (ValueError, TypeError):
        raise ValueError('Bounds must contain four numbers.')
    south, west, north, east = bounds
    if not all(math.isfinite(x) for x in bounds) or not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError('Bounds must be finite, valid coordinates ordered south, west, north, east.')
    if north - south > 0.05 or east - west > 0.05:
        raise ValueError('Select a smaller area (at most 0.05 degrees on each side).')
    return bounds


def validate_filters(filters):
    if not isinstance(filters, dict) or not filters:
        raise ValueError('Provide at least one supported filter.')
    unknown = set(filters) - FILTER_KEYS
    if unknown:
        raise ValueError('Unsupported filters: ' + ', '.join(sorted(unknown)))
    for key, value in filters.items():
        if key.endswith('_types'):
            if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v.strip() for v in value):
                raise ValueError(f'{key} must be a nonempty list of strings.')
        elif key in {'building_type', 'zoning'}:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{key} must be a nonempty string.')
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{key} must be a finite, nonnegative number.')
    for kind in ['height', 'floors', 'value']:
        low = filters.get(f'{kind}_min', filters.get(f'min_{kind}'))
        high = filters.get(f'{kind}_max', filters.get(f'max_{kind}'))
        if low is not None and high is not None and low > high:
            raise ValueError(f'Minimum {kind} cannot exceed maximum {kind}.')
    return filters
