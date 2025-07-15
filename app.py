from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/magic-response", methods=["POST"])
def magic_response():
    data = request.get_json()
    question = data.get("question", "no question given")

    return jsonify({
        "answer": f"🎩 Hello from Amir's Copilot Plugin! You asked: '{question}'. This response came directly from your plugin server."
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)