from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

VALID_EMAIL = "test.user@example.com"
VALID_PASSWORD = "Secure123"


@app.get("/login")
def login_page():
    return render_template("login.html")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email:
        return jsonify(error="Email is required"), 400
    if not password:
        return jsonify(error="Password is required"), 400
    if email != VALID_EMAIL or password != VALID_PASSWORD:
        return jsonify(error="Invalid email or password"), 401
    return jsonify(message="ok"), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000)
