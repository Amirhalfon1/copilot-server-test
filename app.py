from flask import Flask, request, jsonify, redirect, render_template_string
import time
import jwt

app = Flask(__name__)

# In-memory store
USERS = {"admin@example.com": "1234"}
CODES = {}  # auth_code -> email
SECRET_KEY = "super-secret-key"
CLIENT_ID = "magic-client"
CLIENT_SECRET = "magic-secret"
REDIRECT_URI = "https://europe.token.botframework.com/.auth/web/redirect"

# Add a simple endpoint to check if server is working
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "OAuth server is running"})

# Add logging for all requests
@app.before_request
def log_request():
    print(f"🌐 {request.method} {request.path} - Content-Type: {request.content_type}")
    if request.args:
        print(f"📥 Query params: {dict(request.args)}")
    if request.form:
        print(f"📝 Form data: {dict(request.form)}")
    if request.is_json:
        print(f"📋 JSON data: {request.get_json()}")

# Step 1: Show login form
@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    if request.method == "GET":
        # Params passed by Copilot
        client_id = request.args.get("client_id")
        redirect_uri = request.args.get("redirect_uri")
        scope = request.args.get("scope")
        state = request.args.get("state", "")

        print("🚀 AUTHORIZE GET - Received params:")
        print(f"   client_id: {client_id}")
        print(f"   redirect_uri: {redirect_uri}")
        print(f"   scope: {scope}")
        print(f"   state: {state}")

        html = f"""
        <form method="POST">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state}">
            <label>Email: <input name="email"></label><br>
            <label>Password: <input name="password" type="password"></label><br>
            <button type="submit">Login</button>
        </form>
        """
        return render_template_string(html)

    # POST: handle login
    email = request.form.get("email")
    password = request.form.get("password")
    redirect_uri = request.form.get("redirect_uri")
    state = request.form.get("state", "")

    if USERS.get(email) != password:
        return "Invalid credentials", 401

    code = f"code-{int(time.time())}-{email}"
    CODES[code] = email
    print("✅ GENERATED CODE:", code)
    print("📝 CODES STORE:", CODES)
    print("🔄 REDIRECTING TO:", f"{redirect_uri}?code={code}&state={state}")

    return redirect(f"{redirect_uri}?code={code}&state={state}")

# Step 2: Token exchange - Handle both form data, JSON, and query parameters
@app.route("/token", methods=["POST"])
def token():
    print("📨 TOKEN REQUEST - Content-Type:", request.content_type)

    # Try JSON first, then form data, then query string
    if request.is_json:
        data = request.get_json()
        code = data.get("code")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        grant_type = data.get("grant_type")
        print("📝 JSON DATA =", data, flush=True)
    else:
        code = request.form.get("code") or request.args.get("code")
        client_id = request.form.get("client_id") or request.args.get("client_id")
        client_secret = request.form.get("client_secret") or request.args.get("client_secret")
        grant_type = request.form.get("grant_type") or request.args.get("grant_type")
        print("🔁 FORM =", dict(request.form), flush=True)
        print("🔁 ARGS =", dict(request.args), flush=True)

    print("🧪 EXTRACTED VALUES:")
    print(f"   code: {code}")
    print(f"   client_id: {client_id}")
    print(f"   client_secret: {client_secret}")
    print(f"   grant_type: {grant_type}")

    # Check if we got the literal string instead of the actual code
    if code == "{authCode}":
        print("❌ Received literal '{authCode}' - check your Copilot Studio configuration!")
        return jsonify({"error": "invalid_grant", "description": "Received literal placeholder instead of actual authorization code"}), 400

    if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    print("BBBBBBB CODES:", CODES)
    email = CODES.get(code)
    print("CCCCCCC email:", email)

    if not email:
        return jsonify({"error": "invalid_grant", "description": f"Code '{code}' not found or expired"}), 400

    # Now pop the code AFTER we validate it
    del CODES[code]

    # Create JWT token
    payload = {
        "sub": email,
        "ks": "djJ8MzgzfF2m9Zt2-xdNRz6ERea44FCy5YgpWvfWYMBGbU_uS-19tO1Ag6eVHXAqTUxyO1Yatu5zBw6Tu6yNq30Hg4DSAi7b3QxnCB7Dy1lUvo0BDWmJZdhnUOtZFF7sD5zqSKU3ZA==",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600
    })

# Step 3: Protected API
@app.route("/magic-response", methods=["POST"])
def magic_response():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        print("🔓 Decoded JWT payload:", payload)
    except Exception:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    question = data.get("question", "no question given")
    user = payload.get("sub", "unknown user")

    return jsonify({
        "answer": f"🎩 Hello {user}, you asked: '{question}' and I'm your authenticated Copilot Plugin!"
    })


import requests

# Step 4: Kaltura Entries API
@app.route("/kaltura/entries", methods=["GET"])
def get_kaltura_entries():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        ks = payload.get("ks")

        if not ks:
            return jsonify({"error": "No Kaltura Session found in token"}), 400

        # Call Kaltura API with the KS
        kaltura_response = requests.get(
            "https://api.nvq2.ovp.kaltura.com/api_v3/service/media/action/list",
            params={
                "format": 1,  # JSON format
                "pager:objectType": "KalturaFilterPager",
                "pager:pageSize": 500,  # Limit to 10 entries
                "ks": ks
            }
        )
        # Add logging to print response information
        print(f"📊 Kaltura API Response Status: {kaltura_response.status_code}")
        print(f"📊 Kaltura API Response Headers: {kaltura_response.headers}")
        print(f"📊 Kaltura API Response Content: {kaltura_response.text}")

        if kaltura_response.status_code != 200:
            return jsonify({"error": "Kaltura API error", "details": kaltura_response.text}), 500

        return jsonify(kaltura_response.json())

    except Exception as e:
        return jsonify({"error": "unauthorized", "details": str(e)}), 401

# Step 5: Kaltura Captions API
@app.route("/kaltura/captions/<entry_id>", methods=["GET"])
def get_kaltura_captions(entry_id):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        ks = payload.get("ks")

        if not ks:
            return jsonify({"error": "No Kaltura Session found in token"}), 400

        # Call Kaltura API to get captions for the specified entry
        kaltura_response = requests.get(
            "https://api.nvq2.ovp.kaltura.com/api_v3/service/caption_captionasset/action/list",
            params={
                "format": 1,  # JSON format
                "ks": ks,
                "filter:entryIdEqual": entry_id
            }
        )

        # Log response information
        print(f"📊 Kaltura Captions API Response Status: {kaltura_response.status_code}")
        print(f"📊 Kaltura Captions API Response Headers: {kaltura_response.headers}")
        print(f"📊 Kaltura Captions API Response Content: {kaltura_response.text}")

        if kaltura_response.status_code != 200:
            return jsonify({"error": "Kaltura API error", "details": kaltura_response.text}), 500

        return jsonify(kaltura_response.json())

    except Exception as e:
        return jsonify({"error": "unauthorized", "details": str(e)}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)