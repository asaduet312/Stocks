from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return {
        "status":"running",
        "message":"PSXData package deployed successfully.",
        "note":"Replace this placeholder with your actual application routes."
    }

@app.get("/health")
def health():
    return jsonify({"ok":True})
