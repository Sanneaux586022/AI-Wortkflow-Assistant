
import os
from app.models.request import BaseRequest, FotoRequest, MailRequest
from sqlalchemy import text
from werkzeug.utils import secure_filename

class IngestionService:
    """
    Servizio responsabile della ricezione e della validazione iniziale
    delle richiestein ingresso.
    """
    def __init__(self, db_session, logger):
        
        self.db = db_session
        self.logger = logger
    
    def create_mail_request(self, mail_text: str, request_type: str)-> MailRequest:
        """
        Crea un'istanza del modello MailRequest partendo dal testo grezzo.
        L'oggetto viene salvato nel DB. sulle tabelle 
        BaseRequest, MailRequest
        """
        self.logger.info("📥 Creazione nuova richiesta nel database ...")
        new_mail_request = MailRequest(
            mail_text=mail_text,
            request_type = request_type,
            status="pending"
        )
        try:
            self.db.session.add(new_mail_request)
            self.db.session.commit()
            self.db.session.refresh(new_mail_request)
            self.logger.info(f"✅ Richiesta salvata con ID: {new_mail_request.id}")
            return new_mail_request
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"❎ Errore DB in IngestionService: {str(e)}")
            raise e       
    
    def create_foto_request(self, file, request_type: str)-> FotoRequest:
        """
        Crea un'istanza del modello FotoRequest partendo dalla path della foto.
        L'oggetto viene salvato nel DB.
        """
        self.logger.info("📥 Creazione nuova richiesta nel database ...")
        filename = secure_filename(file.filename)
        save_path = os.path.join("/app/multimedia/uploads", filename)
        file.save(save_path)
        new_foto_request = FotoRequest(
            foto_path = save_path,
            request_type = request_type,
            status="pending"
        )

        try:
            self.db.session.add(new_foto_request)
            self.db.session.commit()
            self.db.session.refresh(new_foto_request)
            self.logger.info(f"✅ Richiesta salvata con ID: {new_foto_request.id}")
            return new_foto_request

        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise ValueError(f"Errore durante la cancellazione: {str(e)}")
