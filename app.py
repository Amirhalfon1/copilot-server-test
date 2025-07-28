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

# Step 1: Show login form
@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    if request.method == "GET":
        # Params passed by Copilot
        client_id = request.args.get("client_id")
        redirect_uri = request.args.get("redirect_uri")
        scope = request.args.get("scope")
        state = request.args.get("state", "")

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
    print("AAAAAA CODES:", CODES)

    return redirect(f"{redirect_uri}?code={code}&state={state}")

# Step 2: Token exchange
@app.route("/token", methods=["POST"])
def token():
    form = request.form
    print("🔁 FORM =", dict(form), flush=True)
    code = form.get("code")
    print("🧪 RAW CODE VALUE:", code, flush=True)

    code = form.get("code")
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")
    grant_type = form.get("grant_type")

    if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400
    print("BBBBBBB CODES:", CODES)
    email = CODES.get(code)
    print("CCCCCCC email:", email)
    if not email:
        return jsonify({"error": "invalid_grant"}), 400

    # Now pop the code AFTER we validate it
    del CODES[code]

    # Create JWT token
    payload = {
        "sub": email,
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
    except Exception:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    question = data.get("question", "no question given")
    user = payload.get("sub", "unknown user")

    return jsonify({
        "answer": f"🎩 Hello {user}, you asked: '{question}' and I'm your authenticated Copilot Plugin!"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)