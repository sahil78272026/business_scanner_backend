import os
import requests


GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("Environment variable GOOGLE_MAPS_API_KEY is not set.")


def geocode_city(city: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city, "key": GOOGLE_API_KEY}

    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") != "OK":
        return None

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]

def fetch_businesses(lat, lng, place_type=None, radius=2000, keyword=None, next_token=None):
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "key": GOOGLE_API_KEY,
    }

    if place_type:
        params["type"] = place_type
    if keyword:
        params["keyword"] = keyword
    if next_token:
        params["pagetoken"]= next_token


    resp = requests.get(nearby_url, params=params)
    data = resp.json()

    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
        raise RuntimeError(data.get("error_message", "Google API Error"))


    results = data.get("results", [])
    results = results[:25]  # Limit to avoid too many API calls
    next_page_token = data.get("next_page_token")  # ⭐ NEW

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
            "key": GOOGLE_API_KEY,
        }

        details_resp = requests.get(details_url, params=details_params)
        details = details_resp.json().get("result", {})

        emails = []
        # website = details.get("website")
        # if website:
        #     emails = extract_emails_from_website(website)


        final_list.append({
            "name": details.get("name"),
            "address": details.get("formatted_address"),
            "phone": details.get("formatted_phone_number"),
            "rating": details.get("rating"),
            "reviews_count": details.get("user_ratings_total"),
            "website": details.get("website"),
            "maps_url": details.get("url"),
            "emails":emails,
            "types": details.get("types", [])
        })

    return {
        "businesses": final_list,
        "next_page_token": next_page_token   # ⭐ RETURN IT
    }