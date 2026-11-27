from flask import Blueprint, jsonify

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return jsonify(service="BlueGrid 2.0", version="0.2.0", api="/api/health", documentation="docs/API.md")
