"""
test_processing_service.py — Test UNITARI per ProcessingService.

ProcessingService espone due metodi pubblici:
  - process(request_id)  → orchestra l'analisi AI di un MailRequest
  - predict(request_id)  → orchestra la classificazione AI di un FotoRequest

Entrambi i metodi hanno tre dipendenze:
  - db_session  → SQLAlchemy (recupero e aggiornamento record)
  - ai_service  → AIService / Google Gemini (analisi del contenuto)
  - logger      → logging

Nei test unitari tutte e tre vengono sostituite con mock per:
  1. Testare la logica del servizio in isolamento
  2. Simulare scenari di errore difficili da riprodurre (es. Gemini timeout)

Pattern di mock per la query SQLAlchemy (stile 2.x):
  mock_db.session.query(...).filter(...).first()
  → Configurato tramite chaining automatico di MagicMock.
"""

import pytest
from unittest.mock import MagicMock
from app.services.processing_service import ProcessingService
from app.models.request import MailRequest, FotoRequest


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    db = MagicMock()
    db.session = MagicMock()
    return db


@pytest.fixture()
def mock_ai():
    """
    Mock dell'AI service.
    - process_request()               → usato da process() per le mail
    - process_request_image_description() → usato da predict() per le foto
    """
    ai = MagicMock()
    ai.process_request.return_value = {
        "category": "supporto",
        "priority": "alta",
        "suggested_reply": "Ci scusiamo per il disagio, ti aiutiamo subito.",
    }
    ai.process_request_image_description.return_value = {
        "tipo": "Mammifero",
        "classe": "Mammalia",
        "ordine": "Carnivora",
        "famiglia": "Felidae",
        "genere": "Panthera",
        "specie": "Panthera tigris",
        "pericolosita": "Alta",
        "habitat": "Foreste tropicali e subtropicali dell'Asia",
        "in_pericolo": "In pericolo critico — circa 3.900 esemplari selvatici",
    }
    return ai


@pytest.fixture()
def service(mock_db, mock_ai):
    return ProcessingService(
        db_session=mock_db,
        ai_service=mock_ai,
        logger=MagicMock(),
    )


@pytest.fixture()
def fake_mail_request(mock_db):
    """
    Simula un MailRequest recuperato dal DB.
    spec=MailRequest vincola il mock agli attributi reali del modello,
    evitando falsi positivi su attributi inesistenti.
    """
    req = MagicMock(spec=MailRequest)
    req.id = 1
    req.mail_text = "Non riesco ad accedere al mio account"
    req.status = "pending"
    # Configura la catena di query: session.query().filter().first()
    mock_db.session.query.return_value.filter.return_value.first.return_value = req
    return req


@pytest.fixture()
def fake_foto_request(mock_db):
    """Simula un FotoRequest recuperato dal DB."""
    req = MagicMock(spec=FotoRequest)
    req.id = 2
    req.foto_path = "/app/multimedia/uploads/tigras.jpeg"
    req.status = "pending"
    mock_db.session.query.return_value.filter.return_value.first.return_value = req
    return req


# ─────────────────────────────────────────────────────────────────────────────
# TEST: process() — elaborazione richieste mail
# ─────────────────────────────────────────────────────────────────────────────

class TestProcess:

    def test_aggiorna_campi_con_risultati_ai(self, service, mock_ai, fake_mail_request):
        """
        Dopo la chiamata AI, il servizio deve aggiornare category, priority
        e suggested_reply sulla richiesta mail.
        """
        service.process(1)

        assert fake_mail_request.category == "supporto"
        assert fake_mail_request.priority == "alta"
        assert fake_mail_request.suggested_reply == "Ci scusiamo per il disagio, ti aiutiamo subito."

    def test_imposta_status_processed_al_successo(self, service, fake_mail_request):
        """Quando tutto va bene, lo status deve diventare 'processed'."""
        service.process(1)

        assert fake_mail_request.status == "processed"

    def test_esegue_commit_dopo_aggiornamento(self, service, mock_db, fake_mail_request):
        """Il DB deve essere aggiornato tramite commit."""
        service.process(1)

        mock_db.session.commit.assert_called()

    def test_richiesta_non_trovata_lancia_value_error(self, service, mock_db):
        """
        Se l'ID non esiste nel DB (first() restituisce None),
        deve lanciare ValueError con messaggio chiaro.
        """
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="non trovata"):
            service.process(999)

    def test_errore_ai_imposta_status_error_e_rollback(self, service, mock_ai, mock_db, fake_mail_request):
        """
        Se l'AI lancia un'eccezione:
        1. Lo status della richiesta diventa 'error'
        2. Il DB fa rollback prima di salvare lo stato di errore
        3. L'eccezione viene rilanciata al chiamante
        """
        mock_ai.process_request.side_effect = RuntimeError("Gemini timeout")

        with pytest.raises(RuntimeError, match="Gemini timeout"):
            service.process(1)

        assert fake_mail_request.status == "error"
        mock_db.session.rollback.assert_called_once()

    def test_richiesta_gia_processata_lancia_exception(self, service, mock_db):
        """
        Se la richiesta ha già status='processed', il servizio deve
        lanciare un'eccezione senza chiamare l'AI.
        """
        req = MagicMock(spec=MailRequest)
        req.id = 1
        req.status = "processed"
        mock_db.session.query.return_value.filter.return_value.first.return_value = req

        with pytest.raises(Exception, match="gia processata"):
            service.process(1)

    @pytest.mark.parametrize("category,priority", [
        ("supporto", "alta"),
        ("vendita",  "media"),
        ("reclamo",  "bassa"),
    ])
    def test_gestisce_tutte_le_categorie(self, service, mock_ai, fake_mail_request, category, priority):
        """
        pytest.mark.parametrize esegue questo test per ogni categoria/priorità
        senza duplicare codice.
        """
        mock_ai.process_request.return_value = {
            "category": category,
            "priority": priority,
            "suggested_reply": "risposta di esempio",
        }

        service.process(1)

        assert fake_mail_request.category == category
        assert fake_mail_request.priority == priority
        assert fake_mail_request.status == "processed"


# ─────────────────────────────────────────────────────────────────────────────
# TEST: predict() — classificazione richieste foto
# ─────────────────────────────────────────────────────────────────────────────

class TestPredict:

    def test_aggiorna_campi_tassonomici_con_risultati_ai(self, service, mock_ai, fake_foto_request):
        """
        Dopo la chiamata AI, il servizio deve aggiornare tutti i campi
        tassonomici: tipo, classe, ordine, famiglia, genere, specie,
        pericolosita, habitat, in_pericolo.
        """
        service.predict(2)

        assert fake_foto_request.tipo == "Mammifero"
        assert fake_foto_request.classe == "Mammalia"
        assert fake_foto_request.ordine == "Carnivora"
        assert fake_foto_request.famiglia == "Felidae"
        assert fake_foto_request.genere == "Panthera"
        assert fake_foto_request.specie == "Panthera tigris"
        assert fake_foto_request.pericolosita == "Alta"
        assert fake_foto_request.habitat == "Foreste tropicali e subtropicali dell'Asia"
        assert fake_foto_request.in_pericolo == "In pericolo critico — circa 3.900 esemplari selvatici"

    def test_imposta_status_processed_al_successo(self, service, fake_foto_request):
        """Dopo la classificazione, lo status deve diventare 'processed'."""
        service.predict(2)

        assert fake_foto_request.status == "processed"

    def test_esegue_commit_dopo_aggiornamento(self, service, mock_db, fake_foto_request):
        """Il DB deve essere aggiornato tramite commit."""
        service.predict(2)

        mock_db.session.commit.assert_called()

    def test_foto_non_trovata_lancia_value_error(self, service, mock_db):
        """ID foto inesistente → ValueError."""
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="non trovata"):
            service.predict(999)

    def test_errore_ai_imposta_status_error_e_rollback(self, service, mock_ai, mock_db, fake_foto_request):
        """
        Se l'AI lancia un'eccezione durante la classificazione foto:
        1. status → 'error'
        2. rollback eseguito
        3. eccezione rilanciata
        """
        mock_ai.process_request_image_description.side_effect = RuntimeError("Gemini quota exceeded")

        with pytest.raises(RuntimeError, match="Gemini quota exceeded"):
            service.predict(2)

        assert fake_foto_request.status == "error"
        mock_db.session.rollback.assert_called_once()

    def test_foto_gia_processata_lancia_exception(self, service, mock_db):
        """Se la foto ha già status='processed', non deve essere riprocessata."""
        req = MagicMock(spec=FotoRequest)
        req.id = 2
        req.status = "processed"
        mock_db.session.query.return_value.filter.return_value.first.return_value = req

        with pytest.raises(Exception, match="gia processata"):
            service.predict(2)
