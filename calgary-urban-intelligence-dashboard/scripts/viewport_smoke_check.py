"""Live regression: complete pages, navigation, zoom and persistent filters."""
from pathlib import Path
from playwright.sync_api import sync_playwright

output = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True, args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors, requests = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: requests.append(r.url) if '/buildings/area' in r.url else None)
    page.goto('http://localhost:3006', wait_until='domcontentloaded')
    page.wait_for_selector('canvas')
    page.wait_for_function("!document.querySelector('.map-loading') && document.querySelector('.map-heading span').textContent.includes('mapped')", timeout=300000)
    initial = page.locator('.map-heading > span').inner_text()
    coords = page.locator('.viewport-coordinates').inner_text()
    print('INITIAL:', initial, coords, flush=True)
    assert int(initial.split()[0].replace(',', '')) > 2000
    assert float(coords.split('to ')[1].split(',')[1]) - float(coords.split(',')[1].split(' to')[0]) > .04
    page.screenshot(path=str(output / 'dashboard-desktop.png'), full_page=True)
    page.get_by_label('Building question').fill('buildings over 100 feet')
    page.get_by_role('button', name='Search', exact=True).click()
    page.get_by_text('Height >=', exact=False).first.wait_for()
    page.screenshot(path=str(output / 'dashboard-filtered.png'), full_page=True)
    print('FILTER:', page.locator('.map-heading > span').inner_text(), flush=True)
    before = len(requests)
    page.get_by_label('Map latitude, longitude').fill('51.085, -114.105')
    page.get_by_role('button', name='Go', exact=True).click()
    page.wait_for_function("document.querySelector('.viewport-coordinates').textContent.includes('51.08')", timeout=20000)
    page.wait_for_function("!document.querySelector('.map-loading')", timeout=300000)
    assert len(requests) > before
    assert page.locator('.viewport-coordinates').inner_text() != coords
    page.get_by_text('Height >=', exact=False).first.wait_for()
    print('MOVED WITH FILTER:', page.locator('.map-heading > span').inner_text(), flush=True)
    page.get_by_role('button', name='Clear', exact=True).click()
    page.screenshot(path=str(output / 'dashboard-navigation.png'), full_page=True)
    print('MOVED:', page.locator('.map-heading > span').inner_text(), flush=True)
    # Right-drag the actual canvas; camera movement changes request bounds.
    before_coords = page.locator('.viewport-coordinates').inner_text()
    page.mouse.move(920,600)
    page.mouse.down(button='right')
    page.mouse.move(700,600,steps=12)
    page.mouse.up(button='right')
    page.wait_for_function("document.querySelector('.viewport-coordinates').textContent !== " + repr(before_coords), timeout=20000)
    page.wait_for_function("!document.querySelector('.map-loading')", timeout=300000)
    print('PAN:', page.locator('.viewport-coordinates').inner_text(), flush=True)
    page.get_by_role('button', name='City overview', exact=True).click()
    page.get_by_role('heading', name='Calgary overview').wait_for()
    page.wait_for_function("!document.querySelector('.map-loading') && /^[0-9,]+ roof records/.test(document.querySelector('.map-heading > span').textContent)", timeout=180000)
    assert page.locator('.overview-note').is_visible()
    assert page.locator('.map-help').inner_text().find('Darker cells') >= 0
    print('DENSITY OVERVIEW:', page.locator('.map-heading > span').inner_text(), flush=True)
    page.screenshot(path=str(output / 'dashboard-overview.png'), full_page=True)
    page.mouse.click(1040, 480)
    page.get_by_role('heading', name='Current map area').wait_for()
    page.wait_for_function("!document.querySelector('.map-loading')", timeout=300000)
    print('DENSITY CELL CLICK:', page.locator('.map-heading > span').inner_text(), flush=True)
    page.get_by_role('button', name='Reset view', exact=True).click()
    page.get_by_role('heading', name='Current map area').wait_for()
    page.wait_for_function("!document.querySelector('.map-loading')", timeout=300000)
    assert page.locator('.map-heading > span').inner_text() == initial
    page.get_by_role('button', name='Wider area', exact=True).click()
    page.wait_for_function("Number(document.querySelector('.viewport-coordinates').textContent.split('to ')[1].split(',')[0]) - Number(document.querySelector('.viewport-coordinates').textContent.split(': ')[1].split(',')[0]) > .045", timeout=20000)
    page.wait_for_function("!document.querySelector('.map-loading')", timeout=600000)
    wider = page.locator('.map-heading > span').inner_text()
    assert int(wider.split()[0].replace(',', '')) > int(initial.split()[0].replace(',', ''))
    page.screenshot(path=str(output / 'dashboard-wide-area.png'), full_page=True)
    print('WIDER AREA:', wider, flush=True)
    assert not errors, errors
    print('PASS: More than 500 live buildings; navigation and pan change bounds; filters persist; overview returns to cached detail.', flush=True)
    browser.close()
