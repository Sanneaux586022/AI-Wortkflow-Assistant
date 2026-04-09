import os
from flask import Flask, jsonify
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from app.core.config import Config
from app.db.database import db
import redis
from rq import Queue
from app.core.logger import setup_logging
setup_logging()
from app.api.request_routes import blp as RequestBlueprint
from app.api.user_routes import blp as UserBlueprint

# from app.errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    # Carichiamo tutte le configurazioni dalla classe Config
    app.config.from_object(Config)
    app.redis = redis.from_url(Config.REDIS_URL)
    app.queue = Queue("users", connection=app.redis)


    # --- LOGICA PER DOCKER ---
    # Se DATABASE_URL punta a una cartella specifica, assicuriamoci che esista
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "/app/data" in db_url:
        os.makedirs("/app/data", exist_ok=True) # exist_ok evita se la cartella c'è gia
    # -----------------------

    # Inizializziamo il db
    db.init_app(app)
    # migrate = Migrate(app, db)

    # Inizializziamo API Smorest
    api = Api(app)

    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return app.redis.get(jti) is not None
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify({
                "description": "The token has been revoked.", "error": "token_revoked"
            }), 401
        )
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return (
            jsonify({
                "description": "The token is not fresh.",
                "error": "fresh_token_required."
            }), 401
        )

    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        # Look in the database and see wheter the user is an admin 
        if identity == "1":
            return {"is_admin": True}
        return {"is_admin": False}


    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return (
            jsonify({"message": "Il token è scaduto", "error": "token_scaduto"}),
            401
        )
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return (
            jsonify({"message": "Verifica della firma non riuscita", "error": "token_non_valido"}),
            401
        )
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return(
            jsonify(
                {
                    "description": "La richiesta non contiene un token di accesso.", 
                    "error": "Richiesta_autorizzazione."
                }
            ),
            401
        )

    with app.app_context():
        # Crea il file app.db se non esiste
        db.create_all()

    # Registrazione Blueprint delle rotte
    api.register_blueprint(RequestBlueprint)
    api.register_blueprint(UserBlueprint)
    # register_error_handlers(app)

    return app

app = create_app()

if __name__ == "__main__":
    # app.run(debug=True)
    # In Docker , host="0.0.0.0" è fondamentale perrendere l'app accessibile dall'esterno
    app.run(host="0.0.0.0", port=5000, debug=True)