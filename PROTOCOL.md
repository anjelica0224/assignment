# Urja Meter Ops Portal - Reverse Engineering Notes

## Portal Layout & Authentication

Portal at `https://urja-ops.flockenergy.tech` uses form-based login (no API).

### Login Flow
1. GET `/login` → receive CSRF token in hidden field `_csrf`
2. POST `/login` with `username`, `password`, `_csrf`
3. Response redirect to `/dashboard` if successful
4. Session cookie `session_id` set for subsequent requests

### Session Behavior
- Session valid for ~30 minutes of inactivity
- No explicit logout endpoint
- No refresh token mechanism
- If session expires, portal returns 302 to `/login` (doesn't return 401)

## Data Endpoints

All GET requests after login work transparently. No JSON API—all data embedded in HTML.

### `/dashboard`
Home page. Lists links to:
- `/meters` - list view
- `/network` - hierarchy view  
- `/consumption` - analytics

### `/meters`
Table of all accessible meters. 
- Pagination: `?page=1` (1-indexed, default page 1)
- Shows up to 50 meters per page
- **Quirk**: Page 1 sometimes shows 51 rows due to off-by-one in portal; total count on page 2 header
- Each meter is a clickable link to `/meters/{id}`

Meter table columns: ID, Name, Region, Status (Active/Inactive), Last Read (date)

### `/meters/{meter_id}`
Detail page for one meter. Shows:
- Meter specs (model, serial, capacity)
- Current consumption (kWh, last updated)
- Hourly consumption data (last 24 hours) in a table
- Network path (region → district → pole)

### `/network`
Tree view of meter hierarchy.
- Regions expandable
- Districts under regions
- Poles under districts  
- Meters under poles
- No direct data download; pure visual tree

### `/consumption`
Analytics dashboard.
- Date range picker (GET `/consumption?start=2024-01-01&end=2024-12-31`)
- Summary stats by region
- Graph (rendered client-side, data injected as JS var `window.chartData`)

## HTML Structure Notes

Meter table uses standard `<table>` with `class="meter-table"`.
- Rows are `<tr>` with `data-meter-id="METER123"` attribute
- Columns: `<td>` without specific classes; order is fixed

Detail page: Main content in `<div class="meter-detail">`.
- Specs in `<div class="specs">` with labels as `<strong>` followed by values
- Consumption table: `<table class="consumption-24h">` with rows `<tr><td>hour</td><td>kwh</td>`

Network tree: Uses nested `<ul>` with items marked `class="region"`, `class="district"`, `class="pole"`, `class="meter"`.
- Meter nodes have `data-meter-id` attribute.

## Edge Cases & Quirks

1. **Offline meters**: Some meters show "Never" in "Last Read" column. Don't assume timestamps exist.
2. **Missing consumption**: Detail page may not have a consumption table if meter is brand new. Check for existence before parsing.
3. **Pagination bug**: Last page shows count differently. If you request page 100 and only 97 exist, portal still returns HTTP 200 with empty table.
4. **Region names**: Some regions have Unicode characters (°, µ) which can be corrupted if encoding not UTF-8.
5. **Stale cache**: Consumption graphs update hourly, not real-time. API mirrors this lag.

## Performance Observations

- `/meters` load time: ~800ms for full table (50 records)
- `/meters/{id}` load time: ~400ms
- `/network` load time: ~1.2s (large tree)
- Portal does not compress responses (gzip not enabled)

## MITM Notes

Portal uses HTTPS. Certificate is valid. No certificate pinning detected.
Traffic easily interceptable with proxy (Burp, mitmproxy) if needed for deeper inspection.

All requests are standard HTTP; no websockets or exotic protocols.
