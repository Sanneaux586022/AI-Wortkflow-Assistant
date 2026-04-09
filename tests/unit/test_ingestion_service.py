"""
test_ingestion_service.py — Test UNITARI per IngestionService.

I test unitari testano UNA singola classe/funzione in isolamento,
sostituendo tutte le dipendenze esterne (DB, logger) con dei "mock".

Un mock è un oggetto finto che:
  - Non fa nulla di reale (non scrive sul DB, non logga su file)
  - Registra se è stato chiamato e con quali argomenti
  - Può essere configurato per restituire valori specifici o lanciare eccezioni

Struttura tipica di un test (pattern AAA):
  1. Arrange  → prepara i dati e i mock
  2. Act      → chiama la funzione che stai testando
  3. Assert   → verifica che il risultato sia quello atteso
"""

import pytest
from unittest.mock import MagicMock, call
from app.services.ingestion_service import IngestionService


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE locali: mock del database e del logger
# Sono "function"-scoped (default): ricreati per ogni test → isolamento totale.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    """
    Simula Flask-SQLAlchemy: ha un attributo .session con i metodi
    add(), commit(), rollback(), refresh(), query().
    MagicMock crea automaticamente attributi e metodi finti al primo accesso.
    """
    db = MagicMock()
    db.session = MagicMock()
    return db


@pytest.fixture()
def mock_logger():
    """Logger finto: registra le chiamate senza scrivere su nessun file."""
    return MagicMock()


@pytest.fixture()
def service(mock_db, mock_logger):
    """Istanza di IngestionService pronta per i test, con dipendenze mockat."""
    return IngestionService(db_session=mock_db, logger=mock_logger)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: create_request()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateRequest:
    """Raggruppiamo i test dello stesso metodo in una classe per chiarezza."""

    def test_salva_richiesta_nel_db(self, service, mock_db):
        """
        Caso normale: una nuova richiesta deve essere aggiunta alla sessione DB
        e il commit deve essere eseguito.
        """
        # Act
        service.create_request("Il mio prodotto è rotto")

        # Assert: verifichiamo che add() e commit() siano stati chiamati
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    def test_oggetto_salvato_ha_testo_e_status_corretti(self, service, mock_db):
        """
        L'oggetto passato a session.add() deve avere:
        - il testo della richiesta
        - status = "pending" (non ancora elaborato)
        """
        # Act
        service.create_request("Voglio un rimborso")

        # Recuperiamo l'oggetto passato a session.add()
        # call_args[0][0] = primo argomento posizionale della prima chiamata
        oggetto_salvato = mock_db.session.add.call_args[0][0]

        # Assert
        assert oggetto_salvato.text == "Voglio un rimborso"
        assert oggetto_salvato.status == "pending"

    def test_rollback_se_commit_fallisce(self, service, mock_db):
        """
        Se il commit lancia un'eccezione (es. DB non disponibile),
        il servizio deve fare rollback e rilanciare l'eccezione.
        Questo previene dati "sporchi" nel database.
        """
        # Arrange: facciamo sì che commit() lanci un'eccezione
        mock_db.session.commit.side_effect = Exception("Connessione DB persa")

        # Act + Assert: verifichiamo che l'eccezione venga rilancita
        with pytest.raises(Exception, match="Connessione DB persa"):
            service.create_request("testo qualsiasi")

        # Verifichiamo che il rollback sia stato eseguito
        mock_db.session.rollback.assert_called_once()

    def test_log_info_chiamato_due_volte(self, service, mock_db, mock_logger):
        """
        Il servizio deve loggare:
        1. L'inizio della creazione
        2. Il successo con l'ID della richiesta
        """
        service.create_request("test")

        # assert_called() verifica che il metodo sia stato chiamato almeno una volta
        assert mock_logger.info.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# TEST: get_all_request()
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAllRequest:

    def test_restituisce_lista_dal_db(self, service, mock_db):
        """
        get_all_request() deve delegare la query al DB e restituire il risultato.
        """
        # Arrange: configuriamo il mock per restituire una lista finta
        richieste_false = [MagicMock(), MagicMock()]
        mock_db.session.query.return_value.all.return_value = richieste_false

        # Act
        result = service.get_all_request()

        # Assert
        assert result == richieste_false
        assert len(result) == 2

    def test_restituisce_lista_vuota_se_nessun_record(self, service, mock_db):
        """Se il DB è vuoto, deve restituire una lista vuota (non None)."""
        mock_db.session.query.return_value.all.return_value = []

        result = service.get_all_request()

        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# TEST: cancel_all_record()
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelAllRecord:

    def test_elimina_tutti_i_record_e_resetta_sequenza(self, service, mock_db):
        """
        Deve eliminare tutti i record E resettare il contatore auto-increment
        della tabella (DELETE FROM sqlite_sequence).
        """
        # Arrange: il delete() restituisce il numero di righe eliminate
        mock_db.session.query.return_value.delete.return_value = 5

        # Act
        deleted = service.cancel_all_record()

        # Assert
        assert deleted == 5
        mock_db.session.commit.assert_called_once()

    def test_rollback_se_delete_fallisce(self, service, mock_db):
        """Se la cancellazione fallisce, deve fare rollback e lanciare ValueError."""
        mock_db.session.query.return_value.delete.side_effect = Exception("Errore DB")

        with pytest.raises(ValueError, match="Errore durante la cancellazione"):
            service.cancel_all_record()

        mock_db.session.rollback.assert_called_once()
