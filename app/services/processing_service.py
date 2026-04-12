from app.models.request import MailRequest, FotoRequest

class ProcessingService:
    def __init__(self, db_session, ai_service, logger):
        
        self.db = db_session
        self.ai = ai_service
        self.logger = logger
    
    def process(self, request_id: int)-> MailRequest:
        self.logger.info(f"🔄 Elaborazione richiesta {request_id} iniziata...")

        """
        Orchestra il processo di analisi.
        1. Recupera la richiesta dal DB tramite ID.
        2. Invia il testo all'AI Service.
        3. Aggiorna l'oggetto nel DB con i risultati.
        4. Cambia lo stato in 'processed'.
        """

        # 1. Recupero da Database
        customer_request = self.db.session.query(MailRequest).filter(
            MailRequest.id == request_id).first()

        if not customer_request:
            self.logger.error(f"❎ ID {request_id} non trovato")
            raise ValueError("Richiesta non trovata")
        
        if customer_request.status == "processed":
            self.logger.info("Richiesta gia processata")
            raise Exception("Richiesta gia processata")
        
        try:
            # 2. Chiamata all'AI Service (metodo unificato)
            ai_results = self.ai.process_request(customer_request.mail_text)

            # 3. Aggiornamento dei campi del modello
            customer_request.category = ai_results.get("category")
            customer_request.priority = ai_results.get("priority")
            customer_request.suggested_reply = ai_results.get("suggested_reply")

            # 4. Cambia Stato
            customer_request.status = "processed"

            # Salvataggio nel Database
            self.db.session.commit()
            self.logger.info(f"👍 Richiesta {request_id} elaborata con successo.")
            return customer_request

        except Exception as e:
            # In caso di errore facciamo Rollback per non lasciare dati sporchi nel Database
            self.db.session.rollback()
            customer_request.status = "error"
            self.db.session.commit()
            self.logger.error(f"💥 Errore durante l'elaborazione dell'ID {request_id}: {e}")
            raise e
        
    def predict(self, request_id: int)-> FotoRequest:
        self.logger.info(f"🔄 Elaborazione richiesta {request_id} iniziata...")

        customer_request_foto = self.db.session.query(FotoRequest).filter(
            FotoRequest.id == request_id
        ).first()
        if not customer_request_foto:
            self.logger.error(f"❎ ID {request_id} non trovato")
            raise ValueError("Richiesta non trovata")
        
        if customer_request_foto.status == "processed":
            self.logger.info("Richiesta gia processata")
            raise Exception("Richiesta gia processata")
        
        try:
            # 2. Chiamata all'AI Service (metodo unificato)
            ai_results = self.ai.process_request_image_description(customer_request_foto.foto_path)

            # 3. Aggiornamento dei campi del modello
            customer_request_foto.tipo = ai_results.get("tipo")
            customer_request_foto.classe = ai_results.get("classe")
            customer_request_foto.ordine = ai_results.get("ordine")
            customer_request_foto.famiglia = ai_results.get("famiglia")
            customer_request_foto.genere = ai_results.get("genere")
            customer_request_foto.specie = ai_results.get("specie")
            customer_request_foto.pericolosita = ai_results.get("pericolosita")
            customer_request_foto.habitat = ai_results.get("habitat")
            customer_request_foto.in_pericolo = ai_results.get("in_pericolo")
            

            # 4. Cambia Stato
            customer_request_foto.status = "processed"

            # Salvataggio nel Database
            self.db.session.commit()
            self.logger.info(f"👍 Richiesta {request_id} elaborata con successo.")
            return customer_request_foto

        except Exception as e:
            # In caso di errore facciamo Rollback per non lasciare dati sporchi nel Database
            self.db.session.rollback()
            customer_request_foto.status = "error"
            self.db.session.commit()
            self.logger.error(f"💥 Errore durante l'elaborazione dell'ID {request_id}: {e}")
            raise e


