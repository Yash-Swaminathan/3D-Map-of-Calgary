"""Exercise the running local app in Chrome/Edge and capture real UI screenshots."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:3000')
    args = parser.parse_args()
    candidates = [
        Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
        Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),
    ]
    executable = next((str(path) for path in candidates if path.exists()), None)
    output = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable, headless=True, args=['--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        errors, failures = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failures.append((response.status, response.url))
                if response.status >= 400 else None)
        page.goto(args.url, wait_until='networkidle', timeout=180000)
        page.wait_for_selector('canvas')
        page.wait_for_function("!document.querySelector('.map-loading')", timeout=180000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(output / 'dashboard-desktop.png'), full_page=True)
        total = page.locator('.map-heading > span').inner_text()
        assert '0 mapped' not in total, 'Load real building data before running this workflow.'

        page.get_by_label('Building question').fill('buildings over 100 feet')
        page.get_by_role('button', name='Search', exact=True).click()
        page.wait_for_function("!document.querySelector('.map-loading')")
        page.get_by_text('Height >=', exact=False).first.wait_for()
        result = page.locator('.map-heading > span').inner_text()
        page.screenshot(path=str(output / 'dashboard-filtered.png'), full_page=True)
        print('Query:', total, '->', result)

        page.get_by_role('button', name='Saved projects', exact=True).click()
        page.get_by_label('Enter your name to continue:').fill('Browser Preview')
        page.get_by_role('button', name='Continue to projects').click()
        page.get_by_role('button', name='Save Current Analysis').click()
        page.get_by_label('Project Name *', exact=True).fill('Tall downtown buildings - browser check')
        page.get_by_label('Description (optional)').fill('Browser verification of height filters and persistence.')
        page.get_by_role('button', name='Save Project', exact=True).click()
        page.get_by_role('button', name='Load', exact=True).wait_for()
        page.screenshot(path=str(output / 'dashboard-projects.png'), full_page=True)
        page.get_by_label('Close saved projects').click()
        page.get_by_role('button', name='Clear', exact=True).click()
        assert page.locator('.map-heading > span').inner_text() == total
        page.get_by_role('button', name='Saved projects', exact=False).click()
        page.get_by_role('button', name='Load', exact=True).click()
        page.wait_for_selector('[aria-label="Saved projects"]', state='hidden')
        assert page.locator('.map-heading > span').inner_text() == result
        print('PASS: Identity, save, list, clear, and load restore the same results.')

        page.get_by_role('button', name='Saved projects', exact=False).click()
        page.once('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Delete', exact=True).click()
        page.get_by_text('No saved projects yet.', exact=False).wait_for()
        page.get_by_label('Close saved projects').click()
        page.get_by_role('button', name='Clear', exact=True).click()
        for x, y in [(880, 480), (950, 520), (800, 550), (1000, 600), (740, 650), (900, 650)]:
            page.mouse.click(x, y)
            if page.get_by_role('dialog', name='Building details').count():
                break
        assert page.get_by_role('dialog', name='Building details').count() == 1
        page.screenshot(path=str(output / 'dashboard-building-details.png'), full_page=True)
        page.keyboard.press('Escape')
        print('PASS: Building selection and Escape dismissal.')

        mobile = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(args.url, wait_until='networkidle', timeout=180000)
        mobile.wait_for_function("!document.querySelector('.map-loading')", timeout=180000)
        mobile.wait_for_timeout(700)
        mobile.screenshot(path=str(output / 'dashboard-mobile.png'), full_page=True)
        assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        print('PASS: Mobile layout has no horizontal overflow.')

        # Deliberately simulate an upstream failure, then verify retry against the real API.
        failure_page = browser.new_page()
        failure_page.on('pageerror', lambda error: errors.append(str(error)))
        failure_page.route('**/api/buildings/area*', lambda route: route.fulfill(
            status=502, content_type='application/json', body='{"error":"Test source outage"}'))
        failure_page.goto(args.url, wait_until='networkidle')
        failure_page.get_by_text('Test source outage', exact=False).wait_for()
        failure_page.unroute('**/api/buildings/area*')
        failure_page.get_by_role('button', name='Retry loading area').click()
        failure_page.wait_for_function("!document.querySelector('.map-loading')")
        assert failure_page.locator('.map-heading > span').inner_text() == total
        print('PASS: Visible error state and successful retry.')
        print('JavaScript errors:', errors, 'unexpected HTTP failures:', failures)
        assert not errors and not failures
        browser.close()


if __name__ == '__main__':
    main()
