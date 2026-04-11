from app.models.request import MailRequest, FotoRequest, BaseRequest

class CommonService:
    def __init__(self, db_session, logger):
        
        self.db = db_session
        self.logger = logger

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
    
    def cancel_foto_request_all(self):
        """
        Cancella tutte le richieste Mail nel database.
        """
        try:
            deleted = self.db.session.query(FotoRequest).delete()
            self.db.session.commit()
            self.logger.info(f"cancellati : {deleted}")
            return deleted
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")
        
    def cancel_foto_request(self, request_id):

        """
        Cancella la singola reques partendo dal request_id
        """

        deleted = self.db.session.query(FotoRequest).filter(
                MailRequest.id == request_id
            ).first()
        if not deleted:
                self.logger.info(f"Richiesta {request_id} non trovata.")
                raise LookupError("Impossibile cancellare la richiesta.")
        
        try :

            self.db.session.delete(deleted)
            self.db.session.commit()
            self.logger.info(f"Richiesta {request_id} eliminata correttamente.")
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")      
    
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
    
    def cancel_mail_request_all(self):
        """
        Cancella tutte le richieste Mail nel database.
        """
        try:
            deleted = self.db.session.query(MailRequest).delete()
            self.db.session.commit()
            self.logger.info(f"cancellati : {deleted}")
            return deleted
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")
        
    def cancel_mail_request(self, request_id):

        """
        Cancella la singola reques partendo dal request_id
        """

        deleted = self.db.session.query(MailRequest).filter(
                MailRequest.id == request_id).first()
        
        if not deleted:
                self.logger.info(f"Richiesta {request_id} non trovata.")
                raise LookupError("Impossibile cancellare la richiesta.")
        
        try :

            self.db.session.delete(deleted)
            self.db.session.commit()
            self.logger.info(f"Richiesta {request_id} eliminata correttamente.")
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Errore durante la cancellazione: {str(e)}")
            raise RuntimeError(f"Errore durante la cancellazione: {str(e)}")            