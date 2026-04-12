from flask import jsonify
from sqlalchemy.exc import IntegrityError, ProgrammingError
from marshmallow import ValidationError

def register_error_handlers(app):

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(LookupError)
    def handle_lookup_error(e):
        return jsonify({"error": str(e)}), 404

    @app.errorhandler(RuntimeError)
    def handle_runtime_error(e):
        return jsonify({"error": str(e)}), 500

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        return jsonify({"error": "Dato duplicato o vincolo violato"}), 409

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"error": "Risorsa non trovata"}), 404

    @app.errorhandler(500)
    def handle_internal_error(e):
        return jsonify({"error": "Errore interno del server"}), 500

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"error": e.messages}), 422
    
    @app.errorhandler(ProgrammingError)
    def handle_programming_error(e):
        return jsonify({"error": "Errore del database — contattare l'amministratore"}),500