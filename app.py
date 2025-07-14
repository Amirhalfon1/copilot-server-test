from flask import Flask, jsonify, send_file

app = Flask(__name__)

@app.route("/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello from Copilot Plugin!"})

@app.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    return send_file("openapi.yaml", mimetype="text/yaml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
