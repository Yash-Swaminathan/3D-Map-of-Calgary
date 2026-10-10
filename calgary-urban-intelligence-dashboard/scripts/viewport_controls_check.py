"""Check camera controls without downloading live building records."""
import argparse
import json
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://localhost:3006')
args = parser.parse_args()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True, args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/api/buildings/area*', lambda route: route.fulfill(content_type='application/json', body=json.dumps({
        'success': True, 'buildings': [], 'total_count': 0, 'next_offset': None,
        'version': 'test', 'cache_status': 'cached', 'fetched_at': '2026-10-09T00:00:00', 'warnings': []})))
    page.goto(args.url, wait_until='networkidle')
    page.wait_for_function("!document.querySelector('.map-loading')")
    page.get_by_label('Map latitude, longitude').fill('51.085, -114.105')
    page.get_by_role('button', name='Go', exact=True).click()
    page.wait_for_function("document.querySelector('.viewport-coordinates').textContent.includes('51.08')")
    page.wait_for_function("!document.querySelector('.map-loading')")
    page.get_by_role('button', name='Wider area', exact=True).click()
    page.wait_for_function("Number(document.querySelector('.viewport-coordinates').textContent.split('to ')[1].split(',')[0]) > 51.11")
    page.wait_for_function("!document.querySelector('.map-loading')")
    print('PASS: Wider area preserves the selected neighbourhood:', page.locator('.viewport-coordinates').inner_text())
    assert not errors, errors
    browser.close()
