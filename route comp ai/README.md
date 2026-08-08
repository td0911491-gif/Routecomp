# routecomp

Compares every realistic way to get between two places — shortest, cheapest,
and most luxurious — and asks an LLM (Groq) to parse free-text queries and
write a plain-English recommendation.

## What's real vs. estimated

- **Places** (geocoding): real, via OpenStreetMap Nominatim — free, no key.
- **Road distance/time**: real, via OSRM's public routing server — follows
  actual roads, not a straight line.
- **Flight distance**: real great-circle (haversine) math.
- **Prices**: transparent estimates (see the constants at the top of
  `backend/services/compare.py`), because live fare data for flights/trains/
  buses requires paid commercial APIs. The UI/footer says so explicitly —
  don't present these as live prices.
- **Query parsing & summary**: Groq (`llama-3.3-70b-versatile`). A regex
  handles simple "from X to Y" phrasing without spending an API call; Groq
  only kicks in for messier phrasing, and both the parser and the summary
  fall back to sane defaults if no key is set.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste in your Groq key:
# GROQ_API_KEY=gsk_...

python app.py
```

Open http://localhost:5000

## Project layout

```
backend/
  app.py                  Flask routes
  services/
    geocode.py             place name -> lat/lon (Nominatim)
    routing.py              road distance (OSRM) + great-circle distance
    compare.py              mode comparison logic (pure, no network) — tune prices here
    groq_ai.py               free-text parsing + AI summary (Groq)
  templates/index.html
  static/style.css
  static/script.js
```

## Notes for extending it

- To get real fares, swap the constants in `compare.py` for calls to a paid
  flight/rail API (e.g. Amadeus, Skyscanner, Rome2Rio) inside `get_transport_options`.
- `parse_query` and `generate_summary` in `groq_ai.py` are the only two
  places that call an LLM — easy to swap models or prompts independently.
