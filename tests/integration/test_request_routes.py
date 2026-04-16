"""
test_request_routes.py — Test di INTEGRAZIONE per gli endpoint /requests.

Questi test verificano il flusso completo:
  client HTTP → route → service → DB → risposta JSON

Il DB usato è SQLite in memoria (ricreato prima di ogni test da conftest.py).
Redis e Gemini sono mockati a livello di applicazione (conftest.py).

Per gli endpoint che coinvolgono l'AI (POST /requests/<id>/process e
POST /requests/foto/<id>/process) usiamo patch() per restituire dati finti
e non fare chiamate reali a Google Gemini.

Payload richieste mail:
  {"mail_text": "...", "request_type": "mail"}

Payload richieste foto:
  multipart/form-data con campo "file" (FileStorage) e "request_type"

Nota sul "fresh token":
  Il token ottenuto direttamente al login è già "fresh". Il fixture
  auth_headers in conftest.py fa login direttamente, quindi funziona
  sia per @jwt_required() che per @jwt_required(fresh=True).
"""

import io
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.db.database import db
from app.models.request import MailRequest, FotoRequest
from app.workers.tasks import process_mail_task


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

MAIL_PAYLOAD = {"mail_text": "Ho un problema con la fattura", "request_type": "mail"}


def _fake_foto_file(filename="test.jpg"):
    """Restituisce un file JPEG minimale in-memory per test multipart."""
    return (io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 10), filename)


# ─────────────────────────────────────────────────────────────────────────────
# TEST: POST /requests — Creazione richiesta mail
# ─────────────────────────────────────────────────────────────────────────────

class TestCreazioneRichiestamail:

    def test_crea_richiesta_autenticato_ritorna_201(self, client, auth_headers):
        """
        Caso normale: utente autenticato crea una richiesta mail.
        Deve rispondere 201 con i dati della richiesta appena creata.
        """
        resp = client.post("/requests", json=MAIL_PAYLOAD, headers=auth_headers)

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "pending"
        assert data["mail_text"] == "Ho un problema con la fattura"
        assert "id" in data

    def test_crea_richiesta_senza_autenticazione_ritorna_401(self, client):
        """Senza token JWT la richiesta deve essere rifiutata con 401."""
        resp = client.post("/requests", json=MAIL_PAYLOAD)
        assert resp.status_code == 401

    def test_crea_richiesta_senza_mail_text_ritorna_422(self, client, auth_headers):
        """
        Il campo 'mail_text' è obbligatorio (schema Marshmallow).
        Senza di esso la validazione fallisce con 422 Unprocessable Entity.
        """
        resp = client.post("/requests",
                           json={"request_type": "mail"},
                           headers=auth_headers)
        assert resp.status_code == 422

    def test_crea_richiesta_senza_body_ritorna_422(self, client, auth_headers):
        """Body JSON vuoto → validazione Marshmallow fallisce con 422."""
        resp = client.post("/requests", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_id_richiesta_incrementale(self, client, auth_headers):
        """Le richieste devono avere ID interi progressivi (1, 2, 3...)."""
        resp1 = client.post("/requests",
                            json={"mail_text": "Prima", "request_type": "mail"},
                            headers=auth_headers)
        resp2 = client.post("/requests",
                            json={"mail_text": "Seconda", "request_type": "mail"},
                            headers=auth_headers)

        assert resp1.get_json()["id"] == 1
        assert resp2.get_json()["id"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# TEST: GET /requests — Lista richieste mail
# ─────────────────────────────────────────────────────────────────────────────

class TestListaRichiestemail:

    def test_lista_vuota_ritorna_200_con_lista_vuota(self, client, auth_headers):
        """Con nessuna richiesta nel DB, deve rispondere 200 con lista vuota []."""
        resp = client.get("/requests", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_lista_con_richieste_ritorna_200(self, client, auth_headers):
        """Con richieste presenti, deve rispondere 200 con la lista completa."""
        client.post("/requests",
                    json={"mail_text": "Prima richiesta", "request_type": "mail"},
                    headers=auth_headers)
        client.post("/requests",
                    json={"mail_text": "Seconda richiesta", "request_type": "mail"},
                    headers=auth_headers)

        resp = client.get("/requests", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.get("/requests")
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TEST: GET /requests/<id> — Dettaglio richiesta mail
# ─────────────────────────────────────────────────────────────────────────────

class TestDettaglioRichiestamail:

    def test_dettaglio_richiesta_esistente(self, client, auth_headers):
        """Deve restituire i dati della richiesta specificata dall'ID."""
        create_resp = client.post(
            "/requests",
            json={"mail_text": "Problema con la spedizione", "request_type": "mail"},
            headers=auth_headers,
        )
        req_id = create_resp.get_json()["id"]

        resp = client.get(f"/requests/{req_id}", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.get_json()["mail_text"] == "Problema con la spedizione"

    def test_richiesta_inesistente_ritorna_404(self, client, auth_headers):
        """Un ID inesistente deve restituire 404 Not Found."""
        resp = client.get("/requests/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.get("/requests/1")
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TEST: POST /requests/<id>/process — Elaborazione AI mail
# ─────────────────────────────────────────────────────────────────────────────

class TestElaborazioneAImail:
    """
    Usiamo patch() per non chiamare Gemini realmente.
    Il patch viene applicato direttamente sul metodo process() del
    ProcessingService già istanziato nel modulo request_routes.
    """

    def test_process_richiesta_pending_con_ai_mockato(self, client, auth_headers):
        """
        Flusso completo con AI mockato:
        1. Crea una richiesta (status: pending)
        2. Chiama /process
        3. Verifica che la risposta contenga i risultati AI e status='processed'

        Usiamo spec=MailRequest sul mock per evitare che Marshmallow lo tratti
        come Mapping (MagicMock senza spec implementa __getitem__/__len__/__iter__
        e supera il check isinstance(obj, Mapping)).
        """
        create_resp = client.post(
            "/requests",
            json={"mail_text": "Non riesco a fare login", "request_type": "mail"},
            headers=auth_headers,
        )
        req_id = create_resp.get_json()["id"]

        _ts = datetime(2024, 1, 1, tzinfo=timezone.utc)

        with patch("flask.current_app.mail_queue") as mock_queue:
            resp = client.post(f"/requests/{req_id}/process", headers=auth_headers)
            mock_queue.enqueue.assert_called_once_with(process_mail_task, req_id)
        
        # Verifica la risposta HTTP
            assert resp.status_code == 202

    def test_process_richiesta_inesistente_ritorna_404(self, client, auth_headers):
        """Elaborare un ID inesistente deve restituire 404."""
        resp = client.post("/requests/99999/process", headers=auth_headers)
        assert resp.status_code == 404

    def test_process_richiesta_gia_elaborata_ritorna_400(self, client,app, auth_headers):
        """
        Una richiesta già processata (status='processed') non deve essere
        rielaborata → 400 Bad Request.
        Il controllo avviene nella route, prima di invocare il service.

        Strategia: mocchiamo solo l'AI (process_request) e lasciamo girare
        il ProcessingService reale. Così il DB viene effettivamente aggiornato
        a status='processed', e la seconda chiamata trova lo stato corretto.
        """
        create_resp = client.post(
            "/requests",
            json={"mail_text": "testo", "request_type": "mail"},
            headers=auth_headers,
        )
        req_id = create_resp.get_json()["id"]

        # Aggiorno manualmente la richiesta su db
        with app.app_context():
            req = db.session.get(MailRequest, req_id)
            req.status = "processed"
            db.session.commit()

        # Seconda chiamata: status nel DB è ora "processed" → route risponde 400
        with patch("main.app.mail_queue") as mock_queue:
            resp = client.post(f"/requests/{req_id}/process", headers=auth_headers)
            mock_queue.enqueue.assert_not_called()
        
            # Verifica la risposta HTTP
            assert resp.status_code == 400


    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.post("/requests/1/process")
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TEST: POST /requests/foto — Caricamento foto
# ─────────────────────────────────────────────────────────────────────────────

class TestCreazioneRichiestaFoto:

    def test_carica_foto_autenticato_ritorna_201(self, client, auth_headers):
        """
        Caso normale: caricamento di un file immagine valido.
        Usiamo patch su file.save per evitare scritture reali sul filesystem.
        La route e il service eseguono il percorso reale, restituendo un vero
        oggetto FotoRequest (con created_at valorizzato) che Marshmallow
        serializza correttamente.
        """
        with patch("app.services.ingestion_service.secure_filename", return_value="test.jpg"), \
             patch("werkzeug.datastructures.file_storage.FileStorage.save"):
            resp = client.post(
                "/requests/foto",
                data={
                    "file": _fake_foto_file(),
                    "request_type": "foto",
                },
                content_type="multipart/form-data",
                headers=auth_headers,
            )

        assert resp.status_code == 201

    def test_carica_foto_senza_file_ritorna_400(self, client, auth_headers):
        """Senza il campo 'file' nel multipart, deve rispondere 400."""
        resp = client.post(
            "/requests/foto",
            data={"request_type": "foto"},
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_carica_foto_senza_autenticazione_ritorna_401(self, client):
        resp = client.post(
            "/requests/foto",
            data={"file": _fake_foto_file(), "request_type": "foto"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TEST: GET /requests/foto — Lista richieste foto
# ─────────────────────────────────────────────────────────────────────────────

class TestListaRichiesteFoto:

    def test_lista_foto_vuota_ritorna_200(self, client, auth_headers):
        """Con nessuna foto nel DB, deve rispondere 200 con lista vuota."""
        resp = client.get("/requests/foto", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.get("/requests/foto")
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TEST: Protezione generale degli endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestEndpointProtetti:
    """Verifica che tutti gli endpoint rifiutino richieste senza token JWT."""

    def test_get_requests_senza_token_ritorna_401(self, client):
        resp = client.get("/requests")
        assert resp.status_code == 401

    def test_post_requests_senza_token_ritorna_401(self, client):
        resp = client.post("/requests", json=MAIL_PAYLOAD)
        assert resp.status_code == 401

    def test_get_foto_senza_token_ritorna_401(self, client):
        resp = client.get("/requests/foto")
        assert resp.status_code == 401

    def test_token_invalido_ritorna_401(self, client):
        """Un token malformato o firmato con chiave diversa deve essere rifiutato."""
        resp = client.get("/requests", headers={
            "Authorization": "Bearer questo-non-e-un-token-jwt-valido"
        })
        assert resp.status_code == 401

# ─────────────────────────────────────────────────────────────────────────────
# TEST: Protezione generale degli endpoint per admin
# ─────────────────────────────────────────────────────────────────────────────
class TestEndpointAdmin:
    """
    Verifica che tutti  gli endpoint solo per admin rifiutino qualsiasi chiamata di altri utenti.
    """
    def test_delete_all_mail_requests_utente_admin(self, client, auth_headers):
        """Utente registrato ma non admin."""
        resp = client.delete("/requests", headers=auth_headers)
        assert resp.status_code == 401



