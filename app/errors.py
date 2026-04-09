from flask import jsonify
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError

def register_error_handlers(app):

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return {"error": str(e)}, 409

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        return {"error": "Dato duplicato o vincolo violato"}, 409

    @app.errorhandler(404)
    def handle_not_found(e):
        return {"error": "Risorsa non trovata"}, 404

    @app.errorhandler(500)
    def handle_internal_error(e):
        return {"error": "Errore interno del server"}, 500
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return {"error": e.message}, 422