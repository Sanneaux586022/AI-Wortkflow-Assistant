from flask import Flask, jsonify
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from app.core.config import Config
from app.db.database import db
from app.core.extensions import limiter
from app.models import User, BaseRequest, MailRequest, FotoRequest
import redis
from rq import Queue
from app.core.logger import setup_logging
setup_logging()
from app.api.request_routes import blp as RequestBlueprint
from app.api.user_routes import blp as UserBlueprint
from app.errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.redis = redis.from_url(Config.REDIS_URL)
    app.queue = Queue("users", connection=app.redis)

    # Inizializziamo il db
    db.init_app(app)
    migrate = Migrate(app, db)

    # Inizializziamo il rate limiter
    limiter.init_app(app)
    limiter._storage_uri = Config.REDIS_URL

    # Inizializziamo API Smorest
    api = Api(app)

    jwt = JWTManager(app)

    # ... tutti i tuoi jwt callbacks rimangono invariati ...

    # Registrazione Blueprint
    api.register_blueprint(RequestBlueprint)
    api.register_blueprint(UserBlueprint)
    register_error_handlers(app)

    return app, limiter  # ← restituiamo anche limiter

app, limiter = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)