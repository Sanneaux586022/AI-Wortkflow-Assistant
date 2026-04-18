from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.core.config import Config
from app.core.logger import get_logger
from app.db.database import db
from app.services.ai_service import AIService
from app.services.common_service import CommonService
from app.services.processing_service import ProcessingService

blp = Blueprint("admin", "admin", url_prefix="/admin")
logger = get_logger("admin_routes")
ai_service = AIService(logger)
processing_service = ProcessingService(db, ai_service, logger)
common_service = CommonService(db, logger)


@blp.route("/process-pending/mail")
class MailProcessResource(MethodView):
    def post(self):
        # controllare il cron-secret
        cron_secret = request.headers.get("X-cron-secret")
        request_type = "mail"

        if cron_secret != Config.CRON_SECRET:
            abort(401, message="Non Autorizzato.")

        total, succeed, failed = processing_service.processing_pending_requests(request_type)

        return {
            "message": f"Processate {total} richieste mail.",
            "processed": succeed,
            "failed": failed,
        }, 200


@blp.route("/process-pending/foto")
class FotoProcessResource(MethodView):
    def post(self):
        # controllare il cron-secret
        cron_secret = request.headers.get("X-cron-secret")
        request_type = "foto"

        if cron_secret != Config.CRON_SECRET:
            abort(401, message="Non Autorizzato.")

        total, succeed, failed = processing_service.processing_pending_requests(request_type)

        return {
            "message": f"Processate {total} richieste foto.",
            "processed": succeed,
            "failed": failed,
        }, 200
