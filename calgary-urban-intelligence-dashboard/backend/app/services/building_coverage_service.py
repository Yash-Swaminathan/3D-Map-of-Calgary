"""Geographic density cells from live roof counts, with a short count cache."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
from time import monotonic
import requests

_cache = OrderedDict()
_lock = RLock()


def count_roofs(fetcher, bounds, refresh=False):
    key = (fetcher.base_url, tuple(bounds))
    with _lock:
        cached = _cache.get(key)
        if not refresh and cached and monotonic() - cached[0] < 300:
            _cache.move_to_end(key)
            return cached[1]
    south, west, north, east = bounds
    polygon = f'POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))'
    response = fetcher.session.get(f'{fetcher.base_url}/uc4c-6kbd.json', params={
        '$select': 'count(*) AS count', '$where': f"intersects(multipolygon, '{polygon}')"}, timeout=20)
    response.raise_for_status()
    count = int(response.json()[0]['count'])
    with _lock:
        _cache[key] = (monotonic(), count)
        while len(_cache) > 512:
            _cache.popitem(last=False)
    return count


def coverage_grid(fetcher, bounds, refresh=False):
    south, west, north, east = bounds
    cells = []
    for row in range(4):
        for column in range(4):
            cells.append([south + (north - south) * row / 4,
                          west + (east - west) * column / 4,
                          south + (north - south) * (row + 1) / 4,
                          west + (east - west) * (column + 1) / 4])
    def count_cell(cell):
        try:
            return {'bounds': cell, 'count': count_roofs(fetcher, cell, refresh)}
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return {'bounds': cell, 'count': None}
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(count_cell, cells))
