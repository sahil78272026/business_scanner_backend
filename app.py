import os
import io
import csv
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import jwt
load_dotenv()


app = Flask(__name__)
CORS(app)  # Needed for React frontend

bcrypt = Bcrypt(app)

SECRET = "YOUR_JWT_SECRET"   # Change this to a long random string

DB_CONN = psycopg2.connect(
    host="localhost",
    database="business_scanner",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD")
)

def get_cursor():
    return DB_CONN.cursor(cursor_factory=RealDictCursor)

GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("Environment variable GOOGLE_MAPS_API_KEY is not set.")


# -----------------------------
# 📌 1. Convert city → lat,lng
# -----------------------------
def geocode_city(city: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": city, "key": GOOGLE_API_KEY}

    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") != "OK":
        return None

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


# ---------------------------------------
# 📌 2. Fetch businesses using Places API
# ---------------------------------------
def fetch_businesses(lat, lng, place_type=None, radius=2000, keyword=None):
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

    resp = requests.get(nearby_url, params=params)
    data = resp.json()

    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
        raise RuntimeError(data.get("error_message", "Google API Error"))

    results = data.get("results", [])
    results = results[:25]  # Limit to avoid too many API calls

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

        final_list.append({
            "name": details.get("name"),
            "address": details.get("formatted_address"),
            "phone": details.get("formatted_phone_number"),
            "rating": details.get("rating"),
            "reviews_count": details.get("user_ratings_total"),
            "website": details.get("website"),
            "maps_url": details.get("url"),
            "types": details.get("types", [])
        })

    return final_list


# --------------------------
# 📌 API ROUTES
# --------------------------

# Convert city name → lat,lng
@app.get("/api/geocode")
def api_geocode():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "City is required"}), 400

    coords = geocode_city(city)
    if not coords:
        return jsonify({"error": "Unable to geocode city"}), 404

    return jsonify({"lat": coords[0], "lng": coords[1]})


# Fetch nearby businesses
@app.get("/api/businesses")
def api_businesses():
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    if not lat or not lng:
        return jsonify({"error": "lat and lng are required"}), 400

    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return jsonify({"error": "lat and lng must be numbers"}), 400

    business_type = request.args.get("type")
    radius = int(request.args.get("radius", 2000))
    keyword = request.args.get("keyword")

    try:
        businesses = fetch_businesses(lat, lng, business_type, radius, keyword)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(businesses)


# Export business list as CSV
@app.get("/api/export-csv")
def export_csv():
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    if not lat or not lng:
        return jsonify({"error": "lat and lng required"}), 400

    lat = float(lat)
    lng = float(lng)

    business_type = request.args.get("type")
    radius = int(request.args.get("radius", 2000))
    keyword = request.args.get("keyword")

    businesses = fetch_businesses(lat, lng, business_type, radius, keyword)

    # Convert to CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Name", "Address", "Phone", "Rating", "Reviews", "Website", "Google Maps URL"])

    for b in businesses:
        writer.writerow([
            b.get("name", ""),
            b.get("address", ""),
            b.get("phone", ""),
            b.get("rating", ""),
            b.get("reviews_count", ""),
            b.get("website", ""),
            b.get("maps_url", "")
        ])

    output.seek(0)
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)

    return send_file(mem, mimetype="text/csv", download_name="businesses.csv", as_attachment=True)


@app.get("/api/autocomplete")
def autocomplete():
    query = request.args.get("query")
    if not query:
        return jsonify([])

    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "types": "(cities)",
        "key": GOOGLE_API_KEY
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    predictions = data.get("predictions", [])
    suggestions = [p["description"] for p in predictions]

    return jsonify(suggestions)


@app.post("/api/register")
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"error": "Email and password required"}, 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    try:
        cur = get_cursor()
        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id",
            (email, hashed),
        )
        user = cur.fetchone()
        DB_CONN.commit()

        return {"message": "User registered successfully", "user_id": user["id"]}

    except Exception as e:
        return {"error": "Email already in use"}, 400

@app.post("/api/login")
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        return {"error": "User not found"}, 400

    if not bcrypt.check_password_hash(user["password"], password):
        return {"error": "Incorrect password"}, 400

    token = jwt.encode(
        {"id": user["id"], "exp": datetime.utcnow() + timedelta(days=1)},
        SECRET,
        algorithm="HS256"
    )

    return {"token": token, "email": user["email"]}

@app.get("/api/profile")
def profile():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Missing token"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
        user_id = payload["id"]
    except:
        return {"error": "Invalid or expired token"}, 401

    cur = get_cursor()
    cur.execute("SELECT id, email, created_at FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    return user



if __name__ == "__main__":
    app.run(debug=True, port=5000)
