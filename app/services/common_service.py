from app.models.request import MailRequest, FotoRequest, BaseRequest
from sqlalchemy import text

class CommonService:
    def __init__(self, db_session, logger):
        
        self.db = db_session
        self.logger = logger
    # Tutte le richieste.
    def get_all_request(self)-> list[BaseRequest]:
        requests = self.db.session.query(BaseRequest).all()

        return requests
    
    # FOTO request methods

    def get_foto_request_all(self)-> list[FotoRequest]:
        """
        Recupero tutte le richieste  elaborazione Foto presenti nel database.
        """
        return self.db.session.query(FotoRequest).all()
        
    def get_foto_request(self, request_id) -> FotoRequest:
        
        request_foto = self.db.session.query(FotoRequest).filter(
            FotoRequest.id == request_id
        ).first()

        if not request_foto:
            raise LookupError(f"Richiesta foto {request_id} non trovata.")
        
        return request_foto
    
    def delete_foto_request_all(self):
        """
        Cancella tutte le richieste Mail nel database.
        """
        try:
            records = self.db.session.query(FotoRequest).all()
            deleted = len(records)

            for record in records:
                self.db.session.delete(record)
            self.db.session.commit()
            # resetta id foto request
            self._reset_foto_db_counter()

            
            self.logger.info(f"cancellati : {deleted}")
            return deleted
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}", exc_info=True)
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")
        
    def delete_foto_request(self, request_id):

        """
        Cancella la singola reques partendo dal request_id
        """

        deleted = self.db.session.query(FotoRequest).filter(MailRequest.id == request_id).first()
        
        if not deleted:
            self.logger.info(f"Richiesta {request_id} non trovata.")
            raise LookupError("Impossibile cancellare la richiesta.")
        
        try :

            self.db.session.delete(deleted)
            self.db.session.commit()
            self.logger.info(f"Richiesta {request_id} eliminata correttamente.")
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}", exc_info=True)
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")
        
    def _reset_foto_db_counter(self):
        remaining = self.db.session.query(BaseRequest).count()
        if remaining == 0:
            self.db.session.execute(text("ALTER SEQUENCE requests_id_seq RESTART WITH 1"))
        
        self.db.session.execute(text("ALTER SEQUENCE foto_requests_id_seq RESTART WITH 1"))
        self.db.session.commit()
    
    # MAIL request methods
    def get_mail_request(self, request_id)-> MailRequest:
        
        request_mail = self.db.session.query(MailRequest).filter(MailRequest.id == request_id).first()

        if not request_mail:
            raise LookupError(f"Richiesta mail {request_id} non trovata.")
        
        return request_mail

    def get_mail_request_all(self)-> list[MailRequest]:
        """
        Recupero tutte le richieste  mail presenti nel database.
        """
        return self.db.session.query(MailRequest).all()
    
    def delete_mail_request_all(self):
        """
        Cancella tutte le richieste Mail nel database.
        """
        try:
            records = self.db.session.query(MailRequest).all()
            deleted = len(records)
            for record in records:
                self.db.session.delete(record)
            self.db.session.commit()
            # reseta il contatore
            self._reset_mail_db_counter()
            self.logger.info(f"cancellati : {deleted}")
            return deleted
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}", exc_info=True)
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")
        
    def delete_mail_request(self, request_id):

        """
        Cancella la singola reques partendo dal request_id
        """

        deleted = self.db.session.query(MailRequest).filter(MailRequest.id == request_id).first()
        
        if not deleted:   
            self.logger.info(f"Richiesta {request_id} non trovata.")
            raise LookupError("Impossibile cancellare la richiesta.")
        
        try :

            self.db.session.delete(deleted)
            self.db.session.commit()
            self.logger.info(f"Richiesta {request_id} eliminata correttamente.")
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}", exc_info=True)
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")

    def _reset_mail_db_counter(self):
        # Resetta requests_id_seq solo se non ci sono altri record
        remaining = self.db.session.query(BaseRequest).count()
        if remaining == 0:
            self.db.session.execute(text("ALTER SEQUENCE requests_id_seq RESTART WITH 1"))
        
        self.db.session.execute(text("ALTER SEQUENCE mail_requests_id_seq RESTART WITH 1"))
        self.db.session.commit()