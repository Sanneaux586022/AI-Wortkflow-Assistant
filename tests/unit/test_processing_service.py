"""
test_processing_service.py — Test UNITARI per ProcessingService.

ProcessingService ha due dipendenze:
  - db_session (SQLAlchemy)
  - ai_service (AIService → Google Gemini)

Nei test unitari le sostituiamo ENTRAMBE con mock, così possiamo:
  1. Testare la logica del servizio senza fare chiamate reali a Gemini
  2. Simulare scenari di errore difficili da riprodurre in ambiente reale
     (es. Gemini non risponde, DB non disponibile durante il commit)

Pattern chiave: patch.object(Classe, "attributo")
  Sostituisce temporaneamente un attributo di una classe con un mock.
  Utile quando la classe viene importata in un altro modulo.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.processing_service import ProcessingService
from app.models.request import CustomerRequest


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
    Mock dell'AI service. Configuriamo il valore di ritorno di process_request()
    così possiamo controllare cosa "risponde" l'AI in ogni test.
    """
    ai = MagicMock()
    ai.process_request.return_value = {
        "category": "supporto",
        "priority": "alta",
        "suggested_reply": "Ci scusiamo per il disagio, ti aiutiamo subito.",
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
def fake_request():
    """
    Simula un oggetto CustomerRequest recuperato dal DB.
    spec=CustomerRequest vincola il mock agli attributi reali del modello.
    """
    req = MagicMock(spec=CustomerRequest)
    req.id = 1
    req.text = "Non riesco ad accedere al mio account"
    req.status = "pending"
    return req


# ─────────────────────────────────────────────────────────────────────────────
# TEST: process()
# ─────────────────────────────────────────────────────────────────────────────

class TestProcess:

    def test_chiama_ai_con_il_testo_della_richiesta(self, service, mock_ai, fake_request):
        """
        Il servizio deve passare il testo della richiesta all'AI service.
        Verifichiamo che l'AI sia stata interrogata con il dato corretto.
        """
        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request

            service.process(1)

        # assert_called_once_with() verifica argomenti esatti
        mock_ai.process_request.assert_called_once_with(fake_request.text)

    def test_aggiorna_campi_con_risultati_ai(self, service, mock_ai, fake_request):
        """
        Dopo la chiamata AI, il servizio deve aggiornare category, priority
        e suggested_reply sulla richiesta.
        """
        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request
            service.process(1)

        # Verifichiamo che i campi siano stati impostati correttamente
        assert fake_request.category == "supporto"
        assert fake_request.priority == "alta"
        assert fake_request.suggested_reply == "Ci scusiamo per il disagio, ti aiutiamo subito."

    def test_imposta_status_processed_al_successo(self, service, fake_request):
        """
        Quando tutto va bene, lo status deve diventare "processed".
        """
        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request
            service.process(1)

        assert fake_request.status == "processed"

    def test_esegue_commit_dopo_aggiornamento(self, service, mock_db, fake_request):
        """Il DB deve essere aggiornato tramite commit."""
        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request
            service.process(1)

        mock_db.session.commit.assert_called_once()

    def test_richiesta_non_trovata_lancia_value_error(self, service):
        """
        Se l'ID non esiste nel DB (query.get restituisce None),
        deve lanciare ValueError con messaggio chiaro.
        """
        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = None  # ← ID non trovato

            with pytest.raises(ValueError, match="non trovata"):
                service.process(999)

    def test_errore_ai_imposta_status_error(self, service, mock_ai, mock_db, fake_request):
        """
        Se l'AI lancia un'eccezione:
        1. Lo status della richiesta diventa "error"
        2. Il DB fa rollback (per non lasciare dati a metà)
        3. L'eccezione viene rilancita (il chiamante deve saperlo)
        """
        # Arrange: simuliamo un timeout di Gemini
        mock_ai.process_request.side_effect = RuntimeError("Gemini timeout")

        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request

            with pytest.raises(RuntimeError, match="Gemini timeout"):
                service.process(1)

        # Lo status deve essere "error", NON "processed"
        assert fake_request.status == "error"

        # Il rollback deve essere stato chiamato prima del secondo commit
        mock_db.session.rollback.assert_called_once()

    def test_diversi_tipi_di_risposta_ai(self, service, mock_ai, fake_request):
        """
        Verifica che il servizio funzioni correttamente con valori diversi
        restituiti dall'AI (es. categoria "reclamo", priorità "bassa").

        Questo è un test parametrizzato: lo stesso test viene eseguito
        con input diversi senza duplicare il codice.
        """
        # Cambiamo il valore di ritorno del mock AI
        mock_ai.process_request.return_value = {
            "category": "reclamo",
            "priority": "bassa",
            "suggested_reply": "Abbiamo preso nota del tuo reclamo.",
        }

        with patch.object(CustomerRequest, "query") as mock_query:
            mock_query.get.return_value = fake_request
            service.process(1)

        assert fake_request.category == "reclamo"
        assert fake_request.priority == "bassa"


# ─────────────────────────────────────────────────────────────────────────────
# ESEMPIO: test parametrizzato con pytest.mark.parametrize
# Esegue lo stesso test con più combinazioni di input/output.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("category,priority", [
    ("supporto", "alta"),
    ("vendita", "media"),
    ("reclamo", "bassa"),
])
def test_process_gestisce_tutte_le_categorie(service, mock_ai, fake_request, category, priority):
    """
    pytest.mark.parametrize esegue questo test 3 volte, una per ogni coppia
    (category, priority). Ottimo per testare casi limite senza ripetere codice.
    """
    mock_ai.process_request.return_value = {
        "category": category,
        "priority": priority,
        "suggested_reply": "risposta di esempio",
    }

    with patch.object(CustomerRequest, "query") as mock_query:
        mock_query.get.return_value = fake_request
        service.process(1)

    assert fake_request.category == category
    assert fake_request.priority == priority
    assert fake_request.status == "processed"
