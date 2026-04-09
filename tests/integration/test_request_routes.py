"""
test_request_routes.py — Test di INTEGRAZIONE per gli endpoint /requests.

Questi test verificano il flusso completo:
  client HTTP → route → IngestionService → DB → risposta JSON

Per gli endpoint che coinvolgono l'AI (POST /requests/<id>/process),
usiamo patch() per sostituire il metodo AI con uno che restituisce
dati finti. In questo modo possiamo testare la logica dell'endpoint
senza fare chiamate reali a Google Gemini.

Nota sul "fresh token": alcuni endpoint richiedono un fresh=True token,
cioè un token emesso direttamente al login (non rinnovato via /refresh).
Il fixture auth_headers di conftest.py fa login direttamente, quindi
il token è già "fresh".
"""

import pytest
from unittest.mock import patch, MagicMock


class TestCreazioneRichiesta:
    """Test per POST /requests"""

    def test_crea_richiesta_autenticato_ritorna_201(self, client, auth_headers):
        """
        Caso normale: utente autenticato crea una richiesta.
        Deve rispondere 201 con i dati della richiesta appena creata.
        """
        resp = client.post("/requests",
                           json={"text": "Ho un problema con la fattura"},
                           headers=auth_headers)

        assert resp.status_code == 201
        data = resp.get_json()
        # La richiesta appena creata deve avere status "pending"
        assert data["status"] == "pending"
        assert data["text"] == "Ho un problema con la fattura"
        assert "id" in data

    def test_crea_richiesta_senza_autenticazione_ritorna_401(self, client):
        """Senza token JWT, la richiesta deve essere rifiutata."""
        resp = client.post("/requests", json={"text": "testo"})
        assert resp.status_code == 401

    def test_crea_richiesta_senza_testo_ritorna_422(self, client, auth_headers):
        """
        Il campo "text" è obbligatorio (definito nello schema Marshmallow).
        Senza di esso, la validazione deve fallire con 422.
        """
        resp = client.post("/requests", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_id_richiesta_incrementale(self, client, auth_headers):
        """
        Le richieste devono avere ID interi progressivi (1, 2, 3...).
        """
        resp1 = client.post("/requests", json={"text": "Prima"}, headers=auth_headers)
        resp2 = client.post("/requests", json={"text": "Seconda"}, headers=auth_headers)

        assert resp1.get_json()["id"] == 1
        assert resp2.get_json()["id"] == 2


class TestListaRichieste:
    """Test per GET /requests"""

    def test_lista_vuota_ritorna_400(self, client, auth_headers):
        """
        Con nessuna richiesta nel DB, il servizio lancia un 400.
        Nota: in una API REST "pura" si userebbe 200 con lista vuota [],
        ma questo test documenta il comportamento ATTUALE dell'app.
        """
        resp = client.get("/requests", headers=auth_headers)
        assert resp.status_code == 400

    def test_lista_con_richieste_ritorna_200(self, client, auth_headers):
        """Con almeno una richiesta nel DB, deve rispondere 200 con la lista."""
        client.post("/requests", json={"text": "Prima richiesta"}, headers=auth_headers)
        client.post("/requests", json={"text": "Seconda richiesta"}, headers=auth_headers)

        resp = client.get("/requests", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.get("/requests")
        assert resp.status_code == 401


class TestDettaglioRichiesta:
    """Test per GET /requests/<id>"""

    def test_dettaglio_richiesta_esistente(self, client, auth_headers):
        """Deve restituire i dati della richiesta specificata dall'ID."""
        create_resp = client.post("/requests",
                                  json={"text": "Problema con la spedizione"},
                                  headers=auth_headers)
        req_id = create_resp.get_json()["id"]

        resp = client.get(f"/requests/{req_id}", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.get_json()["text"] == "Problema con la spedizione"

    def test_richiesta_inesistente_ritorna_404(self, client, auth_headers):
        """Un ID che non esiste nel DB deve restituire 404 Not Found."""
        resp = client.get("/requests/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.get("/requests/1")
        assert resp.status_code == 401


class TestElaborazioneAI:
    """
    Test per POST /requests/<id>/process

    Questi test usano patch() per non chiamare Gemini realmente.
    Il patch viene applicato direttamente sul metodo del ProcessingService
    già istanziato nel modulo request_routes.
    """

    def test_process_richiesta_pending_con_ai_mockato(self, client, auth_headers):
        """
        Flusso completo con AI mockato:
        1. Crea una richiesta (status: pending)
        2. Chiama l'endpoint /process
        3. Verifica che lo status diventi "processed"
        """
        # Arrange: crea una richiesta
        create_resp = client.post("/requests",
                                  json={"text": "Non riesco a fare login"},
                                  headers=auth_headers)
        req_id = create_resp.get_json()["id"]

        # Simuliamo la risposta AI senza chiamare Gemini
        risposta_ai_simulata = {
            "category": "supporto",
            "priority": "alta",
            "suggested_reply": "Abbiamo resettato la tua password.",
        }

        # patch() sostituisce il metodo process() del ProcessingService
        # già istanziato nel modulo request_routes (a livello di modulo).
        # "app.services.processing_service.ProcessingService.process" intercetta
        # tutte le istanze della classe.
        with patch("app.services.processing_service.ProcessingService.process") as mock_process:
            # Configuriamo il mock per restituire un oggetto con i dati attesi
            fake_result = MagicMock()
            fake_result.to_dict.return_value = {
                "id": req_id,
                "text": "Non riesco a fare login",
                "status": "processed",
                **risposta_ai_simulata,
            }
            mock_process.return_value = fake_result

            # Act
            resp = client.post(f"/requests/{req_id}/process", headers=auth_headers)

        # Assert
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "processed"
        assert data["category"] == "supporto"
        assert data["priority"] == "alta"

    def test_process_richiesta_inesistente_ritorna_404(self, client, auth_headers):
        """Elaborare un ID che non esiste deve restituire 404."""
        resp = client.post("/requests/99999/process", headers=auth_headers)
        assert resp.status_code == 404

    def test_process_richiesta_gia_elaborata_ritorna_400(self, client, auth_headers):
        """
        Se la richiesta è già stata processata (status = "processed"),
        non deve essere elaborata di nuovo → 400 Bad Request.
        """
        # Creiamo e "processiamo" una richiesta con AI mockato
        create_resp = client.post("/requests",
                                  json={"text": "testo"},
                                  headers=auth_headers)
        req_id = create_resp.get_json()["id"]

        fake_result = MagicMock()
        fake_result.to_dict.return_value = {
            "id": req_id, "text": "testo", "status": "processed",
            "category": "supporto", "priority": "bassa", "suggested_reply": "ok",
        }

        with patch("app.services.processing_service.ProcessingService.process",
                   return_value=fake_result):
            client.post(f"/requests/{req_id}/process", headers=auth_headers)

        # Seconda chiamata: la richiesta è già processed → 400
        # (Il controllo è nella route, PRIMA di chiamare il service)
        resp = client.post(f"/requests/{req_id}/process", headers=auth_headers)
        assert resp.status_code == 400

    def test_senza_autenticazione_ritorna_401(self, client):
        resp = client.post("/requests/1/process")
        assert resp.status_code == 401
