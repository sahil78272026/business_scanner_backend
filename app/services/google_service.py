"""
Google Maps / Places service — geocoding, nearby search, place details, autocomplete.
"""

import requests
import json
from app.core.config import get_settings


def geocode_city(city: str) -> tuple[float, float] | None:
    """
    Convert a city name to (lat, lng) coordinates using Google Geocoding API.
    Returns None if the city cannot be resolved.
    """
    settings = get_settings()
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city, "key": settings.GOOGLE_MAPS_API_KEY}

    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") != "OK":
        return None

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


DEFAULT_RESULTS_LIMIT = 10  # Keep low to control Google API costs


def fetch_businesses(
    conn,
    lat: float,
    lng: float,
    place_type: str | None = None,
    radius: int = 2000,
    keyword: str | None = None,
    next_token: str | None = None,
    limit: int = DEFAULT_RESULTS_LIMIT,
) -> dict:
    """
    Search for nearby businesses using Google Places Nearby Search,
    then enrich each result with Place Details.
    Returns {"businesses": [...], "next_page_token": ...}.

    `limit` controls how many Place Details calls are made (default 10).
    """
    
    # ── 1. Check Database Cache ─────────────────────────────────────
    lat_round = round(lat, 3)
    lng_round = round(lng, 3)
    
    cur = conn.cursor()
    cur.execute("""
        SELECT response_data FROM search_cache
        WHERE lat_round = %s AND lng_round = %s AND radius = %s
          AND type IS NOT DISTINCT FROM %s
          AND keyword IS NOT DISTINCT FROM %s
          AND next_token IS NOT DISTINCT FROM %s
          AND created_at > NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC LIMIT 1
    """, (lat_round, lng_round, radius, place_type, keyword, next_token))
    
    cached_row = cur.fetchone()
    if cached_row:
        cur.close()
        return cached_row[0]
        
    # ── 2. Cache Miss: Call Google APIs ──────────────────────────────
    settings = get_settings()
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "key": settings.GOOGLE_MAPS_API_KEY,
    }

    if place_type:
        params["type"] = place_type
    if keyword:
        params["keyword"] = keyword
    if next_token:
        params["pagetoken"] = next_token

    resp = requests.get(nearby_url, params=params)
    data = resp.json()

    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
        raise RuntimeError(data.get("error_message", "Google API Error"))

    results = data.get("results", [])[:limit]  # Capped to control API costs
    next_page_token = data.get("next_page_token")

    final_list = []

    for place in results:
        place_id = place.get("place_id")
        if not place_id:
            continue

        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,website,"
                      "rating,user_ratings_total,url,types",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }

        details_resp = requests.get(details_url, params=details_params)
        details = details_resp.json().get("result", {})

        final_list.append({
            "name": details.get("name"),
            "address": details.get("formatted_address"),
            "phone": details.get("formatted_phone_number"),
            "rating": details.get("rating"),
            "reviews_count": details.get("user_ratings_total"),
            "website": details.get("website"),
            "maps_url": details.get("url"),
            "emails": [],
            "types": details.get("types", []),
        })

    result_dict = {
        "businesses": final_list,
        "next_page_token": next_page_token,
    }

    # ── 3. Save to Cache ─────────────────────────────────────────────
    cur.execute("""
        INSERT INTO search_cache 
        (lat_round, lng_round, radius, type, keyword, next_token, response_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (lat_round, lng_round, radius, place_type, keyword, next_token, json.dumps(result_dict)))
    
    cur.close()

    return result_dict


def autocomplete_city(query: str) -> list[str]:
    """
    Return city name suggestions using Google Places Autocomplete.
    """
    settings = get_settings()
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "types": "(cities)",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    predictions = data.get("predictions", [])
    return [p["description"] for p in predictions]
