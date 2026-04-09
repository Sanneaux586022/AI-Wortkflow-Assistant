import logging
import sys


def setup_logging():
    # Formato del log: Data/Ora - Nome - Livello - Messaggio

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        force=True,
        handlers=[
            logging.StreamHandler(sys.stdout) # Invia i log al terminale (Docker li legge da qui)
        ]
    )

    # Riduciamo i log troppo rumorosi di librerie esterne (es, SQLAlchemy o Google)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.ERROR)


def get_logger(name="AI-Workflow"):
    return logging.getLogger(name)