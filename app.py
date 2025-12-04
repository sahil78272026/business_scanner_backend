import os
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
import bcrypt
import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Google token verify
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

load_dotenv()

app = Flask(__name__)
CORS(app)  # Needed for React frontend

bcrypt = Bcrypt(app)

APP_SECRET = os.getenv("APP_SECRET", "change-this-secret")
JWT_ALGO = "HS256"
JWT_EXP_DELTA_SECONDS = int(os.getenv("JWT_EXP", 60*60*24*7))  # one week
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # same as VITE_GOOGLE_CLIENT_ID
DB_URI = os.getenv("DATABASE_URL")  # e.g., postgres://user:pass@host:5432/dbname

def get_db():
    conn = psycopg2.connect(DB_URI)
    return conn

# JWT helpers
def generate_jwt(payload):
    payload_copy = payload.copy()
    payload_copy["exp"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    token = jwt.encode(payload_copy, APP_SECRET, algorithm=JWT_ALGO)
    # PyJWT 2.x returns bytes for encode in some versions; ensure str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def decode_jwt(token):
    return jwt.decode(token, APP_SECRET, algorithms=[JWT_ALGO])






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


# @app.post("/api/register")
# def register():
#     data = request.json
#     email = data.get("email")
#     password = data.get("password")

#     if not email or not password:
#         return {"error": "Email and password required"}, 400

#     hashed = bcrypt.generate_password_hash(password).decode("utf-8")

#     try:
#         cur = get_cursor()
#         cur.execute(
#             "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id",
#             (email, hashed),
#         )
#         user = cur.fetchone()
#         DB_CONN.commit()

#         return {"message": "User registered successfully", "user_id": user["id"]}

#     except Exception as e:
#         print(e)
#         return {"error": "Email already in use"}, 400

# @app.post("/api/login")
# def login():
#     data = request.json
#     email = data.get("email")
#     password = data.get("password")

#     cur = get_cursor()
#     cur.execute("SELECT * FROM users WHERE email = %s", (email,))
#     user = cur.fetchone()

#     if not user:
#         return {"error": "User not found"}, 400

#     if not bcrypt.check_password_hash(user["password"], password):
#         return {"error": "Incorrect password"}, 400

#     token = jwt.encode(
#         {"id": user["id"], "exp": datetime.utcnow() + timedelta(days=1)},
#         SECRET,
#         algorithm="HS256"
#     )

#     return {"token": token, "email": user["email"]}

@app.get("/api/profile")
def profile():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Missing token"}, 401

    try:
        payload = jwt.decode(token.replace("Bearer ", ""), APP_SECRET, algorithms=["HS256"])
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
        payload = jwt.decode(token.replace("Bearer ", ""), APP_SECRET, algorithms=["HS256"])
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
        payload = jwt.decode(token.replace("Bearer ", ""), APP_SECRET, algorithms=["HS256"])
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
        payload = jwt.decode(token.replace("Bearer ", ""), APP_SECRET, algorithms=["HS256"])
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
        payload = jwt.decode(token.replace("Bearer ", ""), APP_SECRET, algorithms=["HS256"])
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



# REGISTER (email/password)
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password required"}), 400

    cur = get_cursor()
    # Check if user exists
    cur.execute("SELECT id, provider FROM users WHERE email = %s", (email,))
    existing = cur.fetchone()
    if existing:
        # If user exists and provider is google, do not create password user
        if existing.get("provider") == "google":
            return jsonify({"error": "Account exists with Google Sign-in. Use Google login."}), 400
        return jsonify({"error": "User already exists"}), 400

    # Hash password
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Save user
    cur.execute(
        "INSERT INTO users (name, email, password, provider, created_at) VALUES (%s,%s,%s,%s,NOW()) RETURNING id",
        (name, email, hashed, "password")
    )
    user_id = cur.fetchone()["id"]
    DB_CONN.commit()

    token = generate_jwt({"id": user_id, "email": email})
    # DB_CONN.close()
    return jsonify({"token": token})

# LOGIN (email/password)
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    cur=get_cursor()
    cur.execute("SELECT id, password, provider FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    provider = user.get("provider") or "password"
    if provider == "google":
        # This account was created via Google
        return jsonify({"error": "This account uses Google Sign-in. Please use Google login."}), 400

    hashed = user.get("password")
    if not hashed:
        return jsonify({"error": "No password set for this account"}), 400

    # if not bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")):
    #     return jsonify({"error": "Invalid credentials"}), 401

    token = generate_jwt({"id": user["id"], "email": email})
    # DB_CONN.close()
    return jsonify({"token": token})

# GOOGLE SIGN-IN (credential from frontend)
@app.route("/api/auth/google", methods=["POST"])
def google_auth():
    data = request.json or {}
    credential = data.get("credential")
    if not credential:
        return jsonify({"error": "Missing credential"}), 400

    try:
        idinfo = id_token.verify_oauth2_token(credential, grequests.Request(), GOOGLE_CLIENT_ID)
        # idinfo contains 'email', 'email_verified', 'name', 'sub' (Google user id), etc.
        email = idinfo.get("email")
        name = idinfo.get("name") or ""
        if not email:
            return jsonify({"error": "Google did not provide email"}), 400
        cur= get_cursor()
        cur.execute("SELECT id, provider FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            # existing user
            user_id = user["id"]
            provider = user.get("provider") or "password"
            # If existing provider is 'password' we may optionally allow linking; for now we'll allow login
            # Optionally, if you want to auto-set provider to both, or mark linked, implement here.
            # We'll keep provider as-is (password) if password exists.
        else:
            # create new user with provider=google
            cur.execute(
                "INSERT INTO users (name, email, provider, created_at) VALUES (%s,%s,%s,NOW()) RETURNING id",
                (name, email, "google")
            )
            user_id = cur.fetchone()["id"]
            DB_CONN.commit()

        token = generate_jwt({"id": user_id, "email": email})
        # DB_CONN.close()
        return jsonify({"token": token})

    except ValueError as e:
        print("Google token verify error:", e)
        return jsonify({"error": "Invalid Google token"}), 400
    except Exception as e:
        print("Google auth error:", e)
        return jsonify({"error": "Google auth failed"}), 500

# Example protected route
@app.route("/api/me")
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}),
    token = auth.replace("Bearer ", "")
    try:
        payload = decode_jwt(token)
        user_id = payload.get("id")
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        # DB_CONN.close()
        return jsonify(user)
    except Exception as e:
        print("JWT error", e)
        return jsonify({"error": "Invalid token"}), 401



if __name__ == "__main__":
    app.run(debug=True, port=5000)
