import uuid

from flask import Flask, jsonify, request

from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.offerings import offerings_bp
from blueprints.pages import pages_bp
from blueprints.uploads import uploads_bp
from config import Config
from db import init_db
from logging_config import configure_logging
from routes.health import bp as health_bp
from routes.metrics import bp as metrics_bp
from routes.opportunities import bp as opportunities_bp
from security import register_error_handlers, register_security_headers

app = Flask(__name__)
app.config.from_object(Config)
app.config["REQUEST_COUNT"] = 0

app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(offerings_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(health_bp)
app.register_blueprint(metrics_bp)
app.register_blueprint(opportunities_bp)

configure_logging(app)
register_security_headers(app)
register_error_handlers(app)


@app.before_request
def assign_request_id():
    app.config["REQUEST_COUNT"] += 1
    request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    init_db()


@app.after_request
def add_request_id(response):
    response.headers["X-Request-ID"] = request.request_id
    return response


with app.app_context():
    init_db()


@app.get("/")
def index():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
