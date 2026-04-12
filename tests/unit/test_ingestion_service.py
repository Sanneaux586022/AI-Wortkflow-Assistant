"""
test_ingestion_service.py — Test UNITARI per IngestionService.

IngestionService espone due metodi pubblici:
  - create_mail_request(mail_text, request_type) → salva un MailRequest nel DB
  - create_foto_request(file, request_type)      → salva il file su disco e crea un FotoRequest

In entrambi i casi le dipendenze esterne (DB, filesystem, logger) vengono
sostituite con mock, così i test sono veloci e non lasciano effetti collaterali.

Pattern AAA:
  1. Arrange → prepara dati e mock
  2. Act     → chiama il metodo sotto test
  3. Assert  → verifica il risultato atteso
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.ingestion_service import IngestionService


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE comuni
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    """
    Simula Flask-SQLAlchemy: espone db.session con add/commit/rollback/refresh.
    MagicMock crea attributi finti al primo accesso → nessuna chiamata reale al DB.
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


@pytest.fixture()
def mock_file():
    """
    Simula un oggetto FileStorage di Werkzeug (file caricato via HTTP).
    secure_filename e file.save() vengono gestiti nei test singoli tramite patch.
    """
    f = MagicMock()
    f.filename = "tigras.jpeg"
    return f


# ─────────────────────────────────────────────────────────────────────────────
# TEST: create_mail_request()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateMailRequest:
    """Verifica la creazione di richieste di tipo mail."""

    def test_salva_mail_request_nel_db(self, service, mock_db):
        """
        Caso normale: add() e commit() devono essere chiamati una volta ciascuno.
        """
        service.create_mail_request("Il prodotto è rotto", "mail")

        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    def test_oggetto_ha_mail_text_e_status_pending(self, service, mock_db):
        """
        L'oggetto passato a session.add() deve avere mail_text e status="pending".
        """
        service.create_mail_request("Voglio un rimborso", "mail")

        salvato = mock_db.session.add.call_args[0][0]
        assert salvato.mail_text == "Voglio un rimborso"
        assert salvato.status == "pending"

    def test_oggetto_ha_request_type_corretto(self, service, mock_db):
        """Il campo request_type deve corrispondere a quello passato."""
        service.create_mail_request("Testo di prova", "mail")

        salvato = mock_db.session.add.call_args[0][0]
        assert salvato.request_type == "mail"

    def test_rollback_se_commit_fallisce(self, service, mock_db):
        """
        Se commit() lancia un'eccezione, il servizio deve fare rollback
        e rilanciare l'eccezione originale.
        """
        mock_db.session.commit.side_effect = Exception("Connessione DB persa")

        with pytest.raises(Exception, match="Connessione DB persa"):
            service.create_mail_request("testo qualsiasi", "mail")

        mock_db.session.rollback.assert_called_once()

    def test_logger_chiamato_all_inizio_e_al_successo(self, service, mock_db, mock_logger):
        """Il servizio deve loggare: 1) inizio creazione, 2) successo con ID."""
        service.create_mail_request("test", "mail")

        assert mock_logger.info.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# TEST: create_foto_request()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateFotoRequest:
    """Verifica la creazione di richieste di tipo foto."""

    def test_salva_foto_request_nel_db(self, service, mock_db, mock_file):
        """
        Caso normale: il file viene salvato su disco e il record viene inserito nel DB.
        """
        with patch("app.services.ingestion_service.secure_filename", return_value="tigras.jpeg"), \
             patch.object(mock_file, "save"):
            service.create_foto_request(mock_file, "foto")

        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    def test_oggetto_ha_foto_path_corretto(self, service, mock_db, mock_file):
        """
        foto_path deve essere il percorso completo dove il file è stato salvato.
        """
        with patch("app.services.ingestion_service.secure_filename", return_value="tigras.jpeg"), \
             patch.object(mock_file, "save"):
            service.create_foto_request(mock_file, "foto")

        salvato = mock_db.session.add.call_args[0][0]
        assert salvato.foto_path == "/app/multimedia/uploads/tigras.jpeg"

    def test_oggetto_ha_status_pending(self, service, mock_db, mock_file):
        """Una foto appena caricata deve avere status="pending"."""
        with patch("app.services.ingestion_service.secure_filename", return_value="tigras.jpeg"), \
             patch.object(mock_file, "save"):
            service.create_foto_request(mock_file, "foto")

        salvato = mock_db.session.add.call_args[0][0]
        assert salvato.status == "pending"
        assert salvato.request_type == "foto"

    def test_rollback_se_commit_fallisce(self, service, mock_db, mock_file):
        """Se il commit fallisce, il servizio deve fare rollback e lanciare ValueError."""
        mock_db.session.commit.side_effect = Exception("Errore DB")

        with patch("app.services.ingestion_service.secure_filename", return_value="tigras.jpeg"), \
             patch.object(mock_file, "save"):
            with pytest.raises(ValueError, match="Errore durante la cancellazione"):
                service.create_foto_request(mock_file, "foto")

        mock_db.session.rollback.assert_called_once()

    def test_secure_filename_viene_applicato(self, service, mock_db, mock_file):
        """
        Il nome del file deve passare per secure_filename() prima di essere
        usato nel path, per prevenire path traversal.
        """
        with patch("app.services.ingestion_service.secure_filename",
                   return_value="safe_name.jpg") as mock_secure, \
             patch.object(mock_file, "save"):
            service.create_foto_request(mock_file, "foto")

        mock_secure.assert_called_once_with(mock_file.filename)
        salvato = mock_db.session.add.call_args[0][0]
        assert "safe_name.jpg" in salvato.foto_path
