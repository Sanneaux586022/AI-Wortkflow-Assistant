
import os
from app.models.request import CustomerRequest, CustomerRequestFoto
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
    
    def create_request_cr(self, text: str)-> CustomerRequest:
        """
        Crea un'istanza del modello CustomerRequest partendo dal testo grezzo.
        L'oggetto viene salvato nel DB.
        """
        self.logger.info("📥 Creazione nuova richiesta nel database ...")
        new_request = CustomerRequest(
            text=text,
            status="pending"
        )
        try:
            self.db.session.add(new_request)
            self.db.session.commit()
            self.db.session.refresh(new_request)
            self.logger.info(f"✅ Richiesta salvata con ID: {new_request.id}")
            return new_request
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"❎ Errore DB in IngestionService: {str(e)}")
            raise e
        
    def get_all_request_cr(self):
        """
        Recupero tutte le richieste presenti nel database
        """
        return self.db.session.query(CustomerRequest).all()
    
    def cancel_all_record_cr(self):
        try:
            deleted = self.db.session.query(CustomerRequest).delete()
            self.db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='customer_requests'"))
            self.db.session.commit()
            self.logger.info(f"cancellati : {deleted}")
            return deleted
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise ValueError(f"Errore durante la cancellazione: {str(e)}")
        
    
    def create_request_ft(self, file)-> CustomerRequestFoto:
        """
        Crea un'istanza del modello CustomerRequestFoto partendo dalla path della foto.
        L'oggetto viene salvato nel DB.
        """
        self.logger.info("📥 Creazione nuova richiesta nel database ...")
        filename = secure_filename(file.filename)
        save_path = os.path.join("/app/multimedia/uploads", filename)
        file.save(save_path)
        new_request_foto = CustomerRequestFoto(
            foto_path = save_path,
            status="pending"
        )

        try:
            self.db.session.add(new_request_foto)
            self.db.session.commit()
            self.db.session.refresh(new_request_foto)
            return new_request_foto

        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise ValueError(f"Errore durante la cancellazione: {str(e)}")
