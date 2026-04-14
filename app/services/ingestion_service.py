
import os
from app.models.request import FotoRequest, MailRequest
from werkzeug.utils import secure_filename
import magic
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_SIZE = 5 * 1024 * 1024


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
            request_type = "mail",
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
            self.logger.error(f"❎ Errore DB in IngestionService in : {str(e)}")
            self.logger.error(f"Errore durante il salvataggio richiesta mail: {str(e)}")
            raise RuntimeError(f"Errore durante il salvataggio richiesta mail: {str(e)}")
    
    def create_foto_request(self, file, request_type: str)-> FotoRequest:
        """
        Crea un'istanza del modello FotoRequest partendo dalla path della foto.
        L'oggetto viene salvato nel DB.
        """
        self.logger.info("📥 Creazione nuova richiesta nel database ...")

        self._validate_file(file)
        filename = secure_filename(file.filename)

        save_path = os.path.join("/app/multimedia/uploads", filename)
        file.save(save_path)
        new_foto_request = FotoRequest(
            foto_path = save_path,
            request_type = "foto",
            status="pending"
        )

        try:
            self.db.session.add(new_foto_request)
            self.db.session.commit()
            self.db.session.refresh(new_foto_request)
            self.logger.info(f"✅ Richiesta salvata con ID: {new_foto_request.id}")
            return new_foto_request

        except Exception as e:
            # Se il DB fallisce, rimuovi il file salvato
            if os.path.exists(save_path):
                os.remove(save_path)
            self.db.session.rollback()
            self.logger.error(f"Errore durante il salvataggio richiesta foto: {str(e)}")
            raise RuntimeError(f"Errore durante il salvataggio richiesta foto: {str(e)}")

    import magic

    def _validate_file(self, file):
        # Controlla dimensione
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_SIZE:
            raise ValueError("File troppo grande. Massimo 5MB.")
        
        # Controlla magic number
        header = file.read(2048)  # legge i primi bytes
        file.seek(0)
        mime_type = magic.from_buffer(header, mime=True)
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("Il file non è un'immagine valida.")
        
        # Controlla estensione
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Estensione non permessa. Usa: {', '.join(ALLOWED_EXTENSIONS)}")