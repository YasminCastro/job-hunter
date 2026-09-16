import logging

from flask import Flask, jsonify, request

from services.analyze_service import handle_analyze_request
from services.jobspy_service import handle_jobspy_request

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.get("/")
def health_check():
    return jsonify({"message": "service online"})


@app.post("/jobspy")
def jobspy():
    data = request.get_json(silent=True) or {}

    body, status_code = handle_jobspy_request(data)

    return jsonify(body), status_code


@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}

    body, status_code = handle_analyze_request(data)

    return jsonify(body), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
