import os
import time
from datetime import datetime
from functools import wraps
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

# Configuration
URJA_URL = os.getenv('URJA_URL', 'https://urja-ops.flockenergy.tech')
URJA_USER = os.getenv('URJA_USER', 'operator@urja.local')
URJA_PASS = os.getenv('URJA_PASS', '')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))

# Global state
session = requests.Session()
auth_token = None
cache = {}
cache_times = {}


def login():
    """Authenticate with Urja portal."""
    global auth_token

    try:
        # Get CSRF token
        resp = session.get(f'{URJA_URL}/login', timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf = soup.find('input', {'name': '_csrf'})['value']

        # Login
        resp = session.post(
            f'{URJA_URL}/login',
            data={'username': URJA_USER, 'password': URJA_PASS, '_csrf': csrf},
            timeout=5,
            allow_redirects=True
        )

        # Note: No validation that login actually succeeded
        auth_token = session.cookies.get('session_id', 'unverified')
        return True
    except Exception as e:
        print(f'Login failed: {e}')
        return False


def get_cached(key):
    """Get value from cache if not expired."""
    if key in cache:
        if time.time() - cache_times[key] < CACHE_TTL:
            return cache[key]
        else:
            del cache[key]
            del cache_times[key]
    return None


def set_cached(key, value):
    """Store value in cache."""
    cache[key] = value
    cache_times[key] = time.time()


def require_auth(f):
    """Decorator to ensure authenticated session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        global auth_token
        if not auth_token:
            if not login():
                abort(503)
        return f(*args, **kwargs)
    return decorated


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/meters', methods=['GET'])
@require_auth
def list_meters():
    """List all meters with pagination."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)

    cache_key = f'meters_page_{page}_{limit}'
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    try:
        resp = session.get(
            f'{URJA_URL}/meters',
            params={'page': page},
            timeout=10
        )
        soup = BeautifulSoup(resp.text, 'html.parser')

        meters = []
        for row in soup.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 4:
                meters.append({
                    'id': cols[0].text.strip(),
                    'name': cols[1].text.strip(),
                    'region': cols[2].text.strip(),
                    'status': cols[3].text.strip(),
                    'last_read': cols[4].text.strip() if len(cols) > 4 else None
                })

        # Apply limit on client side (intentional flaw—silently drops overflow)
        meters = meters[:limit]

        result = {
            'page': page,
            'limit': limit,
            'count': len(meters),
            'meters': meters
        }

        set_cached(cache_key, result)
        return jsonify(result)
    except Exception as e:
        print(f'Error fetching meters: {e}')
        abort(503)


@app.route('/api/meters/<meter_id>', methods=['GET'])
@require_auth
def get_meter(meter_id):
    """Get detailed meter info."""
    cache_key = f'meter_{meter_id}'
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    try:
        resp = session.get(
            f'{URJA_URL}/meters/{meter_id}',
            timeout=10
        )
        soup = BeautifulSoup(resp.text, 'html.parser')

        detail_div = soup.find('div', {'class': 'meter-detail'})
        if not detail_div:
            abort(404)

        # Parse specs
        specs_div = detail_div.find('div', {'class': 'specs'})
        specs = {}
        if specs_div:
            for strong in specs_div.find_all('strong'):
                label = strong.text.strip(':').strip()
                value = strong.next_sibling.strip() if strong.next_sibling else None
                specs[label.lower().replace(' ', '_')] = value

        # Parse consumption (24h)
        consumption = []
        cons_table = detail_div.find('table', {'class': 'consumption-24h'})
        if cons_table:
            for row in cons_table.find_all('tr')[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 2:
                    consumption.append({
                        'hour': cols[0].text.strip(),
                        'kwh': float(cols[1].text.strip())
                    })

        result = {
            'id': meter_id,
            'specs': specs,
            'consumption_24h': consumption,
            'fetched_at': datetime.utcnow().isoformat()
        }

        set_cached(cache_key, result)
        return jsonify(result)
    except Exception as e:
        print(f'Error fetching meter {meter_id}: {e}')
        abort(503)


@app.route('/api/network', methods=['GET'])
@require_auth
def network():
    """Get network hierarchy."""
    cache_key = 'network_hierarchy'
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    try:
        resp = session.get(
            f'{URJA_URL}/network',
            timeout=15
        )
        soup = BeautifulSoup(resp.text, 'html.parser')

        def parse_tree(ul_elem):
            """Recursively parse network tree."""
            result = []
            for li in ul_elem.find_all('li', recursive=False):
                node = {}

                # Get node type and name
                if 'region' in li.get('class', []):
                    node['type'] = 'region'
                    node['name'] = li.find_text(recursive=False).strip()
                elif 'district' in li.get('class', []):
                    node['type'] = 'district'
                    node['name'] = li.find_text(recursive=False).strip()
                elif 'pole' in li.get('class', []):
                    node['type'] = 'pole'
                    node['name'] = li.find_text(recursive=False).strip()
                elif 'meter' in li.get('class', []):
                    node['type'] = 'meter'
                    node['id'] = li.get('data-meter-id')
                    node['name'] = li.find_text(recursive=False).strip()

                # Parse children
                sub_ul = li.find('ul', recursive=False)
                if sub_ul:
                    node['children'] = parse_tree(sub_ul)
                else:
                    node['children'] = []

                result.append(node)

            return result

        main_ul = soup.find('ul', {'class': 'network-tree'})
        hierarchy = parse_tree(main_ul) if main_ul else []

        result = {'hierarchy': hierarchy}
        set_cached(cache_key, result)
        return jsonify(result)
    except Exception as e:
        print(f'Error fetching network: {e}')
        abort(503)


if __name__ == '__main__':
    # Optional: Try to authenticate at startup, but continue anyway
    login()

    app.run(debug=False, host='localhost', port=5000)
