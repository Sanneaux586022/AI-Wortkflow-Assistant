from flask.views import MethodView
from flask import request
from flask_smorest import Blueprint, abort
from app.api.schemas import RequestSchema, ResponseSchema, FotoResponseSchema, RequestFotoSchema
from app.services.ingestion_service import IngestionService
from app.services.processing_service import ProcessingService
from app.services.ai_service import AIService
from app.models.request import CustomerRequest
from app.db.database import db
from flask_jwt_extended import jwt_required, get_jwt
from app.core.logger import get_logger

#TODO: Aggiungere ai servizi che necessitano il DB ed il logger.
logger = get_logger("request_routes")
blp = Blueprint("requests", "requests", description="Operazioni requests",
                url_prefix="/requests")

ai_engine = AIService(logger=logger)
ingestion_service = IngestionService(db_session=db, logger=logger)
processing_service = ProcessingService(db_session=db, ai_service=ai_engine, logger=logger)



@blp.route("")
class RequestsResource(MethodView):

    @jwt_required()
    @blp.arguments(RequestSchema)
    @blp.response(201, ResponseSchema)
    def post(self, data):
        try:
            new_request = ingestion_service.create_request_cr(data["text"])
            return new_request.to_dict()
        
        except Exception as e:
            abort(500, 
                message = f"Errore durante la creazione della richiesta: {str(e)}"
            )
    
    @jwt_required()
    @blp.response(200, ResponseSchema(many=True))
    def get(self):
        """ Ritorna la lista di tutte le richieste nel Database"""
        requests = ingestion_service.get_all_request_cr()
        if requests:
            return [req.to_dict() for req in requests]
        abort(400, message="Nessun record presente.")
    
    @jwt_required(fresh=True)
    def delete(self):
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        deleted = ingestion_service.cancel_all_record_cr()
        return {"message": f"Eliminati {deleted} record"}, 200

    
@blp.route("/<int:request_id>")
class RequestDetailResource(MethodView):

    @jwt_required()
    @blp.response(200, ResponseSchema)
    def get(self, request_id):
        """ Ottiene i dettagli di una singola richiesta"""
        request = CustomerRequest.query.get_or_404(request_id)

        return request.to_dict()
    
    @jwt_required(fresh=True)
    def delete(self, request_id):
        # Controllo se la richiesta esiste prima 
        # di provare a rimuoverla
        
        jwt = get_jwt()
        if not jwt.get("is_admin"):
            abort(401, message="Richiesti privileggi di Amministratore.")
        request = CustomerRequest.query.get_or_404(request_id)
        db.session.delete(request)
        db.session.commit()

        return {"message": "Richiesta correttamente cancellata."}

@blp.route("/<int:request_id>/process")
class ProcessResource(MethodView):

    @jwt_required(fresh=True)
    @blp.response(200, ResponseSchema)
    def post(self, request_id):
        """ Scatena l'elaborazione AI per una richiesta specifica"""
        # Verifichiamo che la richiesta esiste  
        request = CustomerRequest.query.get_or_404(request_id)

        if request.status == "processed":
            abort(400, message="Questa richiesta è già stata elaborata.")
        
        try:
            # Il processingService si occupa di chiamare l'AI Servicee aggiornare il DB
            processed_request = processing_service.process(request_id)
            return processed_request.to_dict()
        except Exception as e:
            abort( 500, message=f"Errore durante l'elaborazione AI : {str(e)}")

@blp.route("/foto")
class FotoResource(MethodView):

    @jwt_required()
    @blp.response(201, FotoResponseSchema)
    def post(self):
        try:
            file = request.files.get("file")
            
            if file is None:
                abort(400, message="File mancante.")
            
            print("FILE RICEVUTO:", file.filename, file.content_type)

            new_request = ingestion_service.create_request_ft(file)
            return new_request.to_dict()
        
        except Exception as e:
            abort(500, 
                message = f"Errore durante la creazione della richiesta: {str(e)}"
            )
    
    @jwt_required()
    @blp.response(200, FotoResponseSchema(many=True))
    def get(self):
        try:
            foto_request_list = processing_service.foto_req_list()
            return foto_request_list
        except ValueError as e:
            abort(400, message=f"Errore nel recupero delle richieste: {str(e)}")

@blp.route("/foto/<int:request_id>/process")
class ProcessFoto(MethodView):

    @jwt_required(fresh=True)
    @blp.response(200, FotoResponseSchema)
    def post(self, request_id):
        """ Scatena l'elaborazione AI per una richiesta Foto specifica"""
        
        try:
            # Il processingService si occupa di chiamare l'AI Servicee aggiornare il DB
            foto_processed = processing_service.predict(request_id)
            return foto_processed.to_dict()
        except Exception as e:
            abort( 500, message=f"Errore durante l'elaborazione AI : {str(e)}")
    
@blp.route("/foto/<int:request_id>")
class RequestFotoDetail(MethodView):

    @jwt_required()
    @blp.response(200, FotoResponseSchema)
    def get(self, request_id)-> FotoResponseSchema:
        try:
            foto_processed = processing_service.get_foto_req(request_id)
            return foto_processed
        except ValueError as e:
            abort(400, message=f"Errore nel recupero della richiesta: {str(e)}")
    



    

    



        