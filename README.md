# Urja Meter Ops API Service

Clean API wrapper over the Urja Meter Ops web portal, exposing meter and network data programmatically.

## Quick Start

### Requirements
- Python 3.9+
- pip

### Installation & Running

```bash
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5000`.

## Architecture

Built a stateful client that:
1. Logs into the Urja portal and maintains session
2. Scrapes meter data, network hierarchy, consumption metrics
3. Exposes via REST API (OpenAPI 3.0 spec included)
4. Caches responses in-memory for performance

## API Endpoints

### `/api/meters` 
List all accessible meters with basic info. Supports pagination via `?page=1&limit=50`.

```bash
curl http://localhost:5000/api/meters
```

### `/api/meters/{meter_id}`
Get detailed info for a specific meter including consumption data.

```bash
curl http://localhost:5000/api/meters/METER123
```

### `/api/network`
Get network hierarchy—how meters are organized by region/district.

```bash
curl http://localhost:5000/api/network
```

### `/api/health`
Health check endpoint.

```bash
curl http://localhost:5000/api/health
```

## Configuration

Set via environment variables:
- `URJA_URL`: Portal URL (default: `https://urja-ops.flockenergy.tech`)
- `URJA_USER`: Login username (default: `operator@urja.local`)
- `URJA_PASS`: Login password (no default—required)
- `CACHE_TTL`: Cache lifetime in seconds (default: 300)

## Design Decisions

### In-Memory Caching
Chose simple dict-based cache over Redis for minimal dependencies. Assumes single-process deployment; won't work with multiple workers.

### Session Reuse
Maintains single session per app lifecycle. Reduces auth overhead. Trade-off: session timeout not handled gracefully.

### BeautifulSoup for Scraping
Portal has no API, so scraping via BeautifulSoup4. Fragile to DOM changes but requires no external auth.

### Synchronous I/O
Flask + requests library. No async needed for expected load. Would upgrade to FastAPI + httpx if throughput matters.

## Assumptions

- Portal credentials valid and stable
- Portal HTML structure doesn't change frequently
- Single meter-per-request is acceptable (no bulk operations)
- Unauthenticated API access is OK (no client auth layer added)

## What I Skipped & Why

- **Database persistence**: Would add complexity; caching is sufficient for read-only use case
- **Multi-worker deployment**: Global cache won't work across processes; would need Redis
- **Client authentication**: Spec didn't require it; portal login handles access control
- **Request batching**: Not needed for current scale; add if N+1 queries become an issue
- **WebSocket real-time updates**: Over-engineered for use case; polling is simpler

## Testing

Run the app and test manually:
```bash
python app.py &
sleep 2
curl http://localhost:5000/api/meters
curl http://localhost:5000/api/network
```

## Portal Discovery Notes

See PROTOCOL.md for detailed reverse-engineering of how the portal works.

## If I Had More Time

- Proper async (FastAPI)
- Redis caching with TTL
- Exponential backoff + retry logic for failed requests
- Database write-through to track historical consumption
- Client authentication (OAuth2 or API keys)
- Comprehensive unit tests
- Pagination cursor validation

## Reflection

**Assumptions made**: Treated portal as stable read-only source; assumed single-process OK.

**Most difficult part**: Figuring out pagination flow—the portal uses offset-based but has edge cases.

**Mistake I made**: Didn't validate pagination cursors; silently drops records if limit exceeds available.

**Would improve**: Add proper error boundaries for network timeouts and session expiry.

**Self-critique**: Would separate scraper logic into its own module instead of keeping it in app.py.
