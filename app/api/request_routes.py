from flask import request, current_app
from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint, abort
from werkzeug.exceptions import HTTPException

from app.api.schemas import FotoResponseSchema, MailRequestSchema, MailResponseSchema
from app.core.logger import get_logger
from app.db.database import db
from app.services.ai_service import AIService
from app.services.common_service import CommonService
from app.services.ingestion_service import IngestionService
from app.services.processing_service import ProcessingService
from app.core.extensions import limiter

logger = get_logger("request_routes")
blp = Blueprint(
    "requests", "requests", description="Operazioni requests", url_prefix="/requests"
)

ai_engine = AIService(logger=logger)
ingestion_service = IngestionService(db_session=db, logger=logger)
common_service = CommonService(db_session=db, logger=logger)
processing_service = ProcessingService(
    db_session=db, ai_service=ai_engine, logger=logger
)


@blp.route("")
class MailResource(MethodView):
    @jwt_required()
    @limiter.limit("5 per minute")
    @blp.arguments(MailRequestSchema)
    @blp.response(201, MailResponseSchema)
    def post(self, data):
        """
        Crea una richiesta mail da elaborare.
        """
        try:
            new_request = ingestion_service.create_mail_request(
                data["mail_text"], data["request_type"]
            )
            return new_request

        except Exception as e:
            abort(500, message=f"Errore durante la creazione della richiesta: {str(e)}")

    @jwt_required()
    @limiter.limit("20 per minute")
    @blp.response(200, MailResponseSchema(many=True))
    def get(self):
        """
        Ritorna la lista di tutte le richieste mail nel Database
        """
        requests = common_service.get_mail_request_all()
        return requests

    @jwt_required(fresh=True)
    def delete(self):
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        try:
            deleted = common_service.delete_mail_request_all()
            return {"message": f"Eliminati {deleted} record"}, 200
        except Exception as e:
            abort(500, message=f"Internal Server Error: {str(e)}")


@blp.route("/<int:request_id>")
class MailDetailResource(MethodView):
    @jwt_required()
    @limiter.limit("20 per minute")
    @blp.response(200, MailResponseSchema)
    def get(self, request_id):
        """Ottiene i dettagli di una singola richiesta mail"""
        try:
            request = common_service.get_mail_request(request_id)
            return request
        except Exception as e:
            abort(404, message=f"Errore: {str(e)}")

    @jwt_required(fresh=True)
    def delete(self, request_id):
        """
        Cancella una specifica richiesta mail.
        """
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        try:
            common_service.delete_mail_request(request_id)
            return {"message": "Richiesta correttamente cancellata."}
        except RuntimeError as e:
            abort(500, message=f"Errore durante la cancellazione: {str(e)}")
        except LookupError as e:
            abort(404, message=f"Errore durante la cancellazione: {str(e)}")


@blp.route("/<int:request_id>/process")
class ProcessMailResource(MethodView):
    @jwt_required(fresh=True)
    @limiter.limit("5 per minute")
    def post(self, request_id):
        """Scatena l'elaborazione AI per una richiesta Mail specifica"""

        try:
            request = common_service.get_mail_request(request_id)
        except LookupError as e:
            abort(404, message=str(e))

        if request.status == "processed":
            abort(400, message="Questa richiesta è già stata elaborata.")

        current_app.email_queue.enqueue(
            processing_service.process,
            request_id
        )
        return {"message": f"Richiesta {request_id} in elaborazione."}, 202


@blp.route("/foto")
class FotoResource(MethodView):
    @jwt_required()
    @limiter.limit("5 per minute")
    @blp.response(201, FotoResponseSchema)
    def post(self):
        """
        Crea una richiesta Foto da elaborare.
        """
        try:
            file = request.files.get("file")
            request_type = request.form.get("request_type")

            if file is None:
                abort(400, message="File mancante.")

            print("FILE RICEVUTO:", file.filename, file.content_type)

            new_request = ingestion_service.create_foto_request(file, request_type)
            return new_request
        except HTTPException:
            raise
        except Exception as e:
            abort(500, message=f"Errore durante la creazione della richiesta: {str(e)}")

    @jwt_required()
    @limiter.limit("20 per minute")
    @blp.response(200, FotoResponseSchema(many=True))
    def get(self):
        """
        Ritorna la lista di tutte le richieste Foto presenti nel Database.
        """
        foto_request_list = common_service.get_foto_request_all()
        return foto_request_list

    @jwt_required(fresh=True)
    def delete(self):
        """
        Cancella Tutte le richieste Foto presenti nel database.
        """
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        try:
            deleted = common_service.delete_foto_request_all()
            return {"message": f"Eliminati {deleted} record"}, 200
        except Exception as e:
            abort(500, message=f"Internal Server Error: {str(e)}")


@blp.route("/foto/<int:request_id>")
class FotoDetailResource(MethodView):
    @jwt_required()
    @limiter.limit("20 per minute")
    @blp.response(200, FotoResponseSchema)
    def get(self, request_id) -> FotoResponseSchema:
        """
        Ottiene i dettagli di una singola richiesta Foto.
        """
        try:
            foto_processed = common_service.get_foto_request(request_id)
            return foto_processed
        except LookupError as e:
            abort(404, message=str(e))

    @jwt_required(fresh=True)
    def delete(self, request_id):
        """
        Cancella una specifica richiesta foto.
        """
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        try:
            common_service.delete_foto_request(request_id)
            return {"message": "Richiesta correttamente cancellata."}
        except RuntimeError as e:
            abort(500, message=f"Errore durante la cancellazione: {str(e)}")
        except LookupError as e:
            abort(404, message=f"Errore durante la cancellazione: {str(e)}")


@blp.route("/foto/<int:request_id>/process")
class ProcessFotoResource(MethodView):
    @jwt_required(fresh=True)
    @limiter.limit("5 per minute")
    def post(self, request_id):
        """Scatena l'elaborazione AI per una richiesta Foto specifica"""
        try:
            foto = common_service.get_foto_request(request_id)
        except LookupError as e:
            abort(404, message=str(e))

        if foto.status == "processed":
            abort(400, message="Questa richiesta è gia stata processata.")

        current_app.foto_queue.enqueue(
            processing_service.predict,
            request_id
        )
        return {"message": f"Richiesta {request_id} in elaborazione."}, 202
