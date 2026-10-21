# Urja Meter Ops API Service

Clean API wrapper over the Urja Meter Ops web portal, exposing meter and network data programmatically.

## Quick Start

### Requirements
- Python 3.9+
- pip

### Installation & Running

```bash
pip install -r requirements.txt
URJA_PASS=urja-ops-2026 python app.py
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
Chose simple dict-based cache over Redis for minimal dependencies. Sufficient for single-instance deployment.

### Session Management
Maintains single session per app lifecycle. Reduces auth overhead by avoiding repeated login calls.

### BeautifulSoup for Scraping
Portal has no API, so scraping via BeautifulSoup4. Parses HTML tables and tree structures to extract data.

### Synchronous I/O
Flask + requests library. Simpler than async for this use case.

## Assumptions

- Portal credentials valid and remain unchanged
- Portal HTML structure remains stable
- Unauthenticated API access acceptable
- Single process deployment (no multi-worker scaling required)

## What I Skipped

- Database persistence (cache sufficient for read-only use)
- Multi-worker support (would need Redis)
- Client authentication layer
- Request batching
- Async I/O with FastAPI

## Testing

Run the app and test manually:
```bash
python app.py &
sleep 2
curl http://localhost:5000/api/meters
curl http://localhost:5000/api/network
```

See PROTOCOL.md for portal reverse-engineering details. OpenAPI spec available at openapi.json.

## Reflection

See REFLECTION.md for detailed reflection on assumptions, design decisions, and lessons learned.
