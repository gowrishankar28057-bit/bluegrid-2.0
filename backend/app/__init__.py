"""Flask application factory. Importing the package starts no server."""
import json
import os
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from .cache import RunCache


class StrictJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs.setdefault("allow_nan", False)
        return super().dumps(obj, **kwargs)

    def loads(self, value, **kwargs):
        def reject_constant(value):
            raise ValueError(f"Non-finite JSON value: {value}")
        kwargs.setdefault("parse_constant", reject_constant)
        return json.loads(value, **kwargs)


def create_app(test_config=None):
    app = Flask(__name__)
    app.json = StrictJSONProvider(app)
    app.json.sort_keys = False
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        MAX_RUNS=32, CACHE_TTL_SECONDS=3600,
        ALLOWED_ORIGINS=os.environ.get("BLUEGRID_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    )
    if test_config:
        app.config.update(test_config)
    app.extensions["run_cache"] = RunCache(app.config["MAX_RUNS"], app.config["CACHE_TTL_SECONDS"])
    from .routes.api import api
    from .routes.export import exports
    from .routes.main import main
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(exports)

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify(error={"code": "invalid_input", "message": str(error)}), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={"code": error.name.lower().replace(" ", "_"), "message": error.description}), error.code

    @app.after_request
    def cors(response):
        origin = request.headers.get("Origin")
        if origin in app.config["ALLOWED_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers.add("Vary", "Origin")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app
