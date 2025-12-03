import io
import csv
import requests
import jwt
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from common_helpers import extract_emails_from_website
from google_helpers import geocode_city, GOOGLE_API_KEY, fetch_businesses
from db_extentions import get_cursor, DB_CONN

load_dotenv()

app = Flask(__name__)
CORS(app)  # Needed for React frontend

bcrypt = Bcrypt(app)

SECRET = "YOUR_JWT_SECRET"   # Change this to a long random string

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
    next_token = request.args.get("next_page_token")


    try:
        businesses = fetch_businesses(lat, lng, business_type, radius, keyword, next_token)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(businesses)


# Export business list as CSV
@app.post("/api/export-csv")
def export_csv_post():
    data = request.json.get("businesses", [])
    if not data:
        return jsonify({"error": "No business data provided"}), 400

    output = io.StringIO()
    writer = csv.writer(output)

    # Add headers
    writer.writerow([
        "Name",
        "Address",
        "Phone",
        "Rating",
        "Reviews",
        "Website",
        "Google Maps URL",
        "Emails"
    ])

    # Add business rows
    for b in data:
        emails_str = ", ".join(b.get("emails", []))

        writer.writerow([
            b.get("name", ""),
            b.get("address", ""),
            b.get("phone", ""),
            b.get("rating", ""),
            b.get("reviews_count", ""),
            b.get("website", ""),
            b.get("maps_url", ""),
            emails_str
        ])

    output.seek(0)
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)

    return send_file(
        mem,
        mimetype="text/csv",
        download_name="businesses.csv",
        as_attachment=True
    )


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


@app.post("/api/save-business")
def save_business():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
        user_id = payload["id"]
    except:
        return {"error": "Invalid token"}, 401

    data = request.json

    cur = get_cursor()
    try:
        cur.execute("""
                INSERT INTO saved_businesses
                (user_id, name, address, phone, website, rating, reviews_count, maps_url, emails)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, name, address) DO NOTHING
                RETURNING id
            """, (
                user_id,
                data["name"],
                data.get("address"),
                data.get("phone"),
                data.get("website"),
                data.get("rating"),
                data.get("reviews_count"),
                data.get("maps_url"),
                ", ".join(data.get("emails", []))   # ⭐ convert list → string
            ))

        result = cur.fetchone()
        DB_CONN.commit()

        if result:
            return {"message": "Saved successfully"}
        else:
            return {"message": "Already saved"}

    except Exception as e:
        print(e)
        return {"error": "Failed to save business"}, 500


@app.get("/api/saved-businesses")
def get_saved_businesses():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
        user_id = payload["id"]
    except:
        return {"error": "Invalid token"}, 401

    cur = get_cursor()
    cur.execute("SELECT * FROM saved_businesses WHERE user_id=%s ORDER BY saved_at DESC", (user_id,))
    rows = cur.fetchall()
    # ⭐ Convert stored TEXT to list
    for row in rows:
        email_str = row.get("emails")
        if email_str:
            row["emails"] = [e.strip() for e in email_str.split(",")]
        else:
            row["emails"] = []

    return rows


@app.get("/api/scrape-email")
def scrape_email_api():
    url = request.args.get("url")
    if not url:
        return {"emails": []}

    try:
        emails = extract_emails_from_website(url)
        return {"emails": emails}
    except Exception as e:
        print("Scrape error:", e)
        return {"emails": []}


@app.post("/api/update-status")
def update_status():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
        user_id = payload["id"]
    except:
        return {"error": "Invalid token"}, 401

    data = request.json
    business_id = data.get("id")
    status = data.get("status")

    print(business_id)
    print(status)
    print(user_id)
    cur = get_cursor()
    try:
        cur.execute("""
            UPDATE saved_businesses
            SET status = %s
            WHERE id = %s AND user_id = %s
        """, (status, business_id, user_id))
        DB_CONN.commit()
    except Exception as e:
        print(e)

    return {"success": True}


@app.post("/api/update-notes")
def update_notes():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET, algorithms=["HS256"])
        user_id = payload["id"]
    except:
        return {"error": "Invalid token"}, 401

    data = request.json
    business_id = data.get("id")
    notes = data.get("notes")

    cur = get_cursor()
    cur.execute("""
        UPDATE saved_businesses
        SET notes = %s
        WHERE id = %s AND user_id = %s
    """, (notes, business_id, user_id))
    DB_CONN.commit()

    return {"success": True}



if __name__ == "__main__":
    app.run(debug=True, port=5000)
