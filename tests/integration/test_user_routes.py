"""
test_user_routes.py — Test di INTEGRAZIONE per gli endpoint /users.

I test di integrazione a differenza dei test unitari:
  - Testano il sistema completo: route → service → database
  - Usano un vero database (SQLite in memoria, ricreato prima di ogni test)
  - NON mockano la logica applicativa (solo Redis e Gemini, dipendenze esterne)
  - Verificano le risposte HTTP (status code, struttura JSON)

Il client Flask simula richieste HTTP reali senza avviare un server di rete.
Ogni fixture che usi qui deve essere dichiarata in conftest.py o localmente.
"""

import pytest


class TestRegistrazione:
    """Test per POST /users/register"""

    def test_registrazione_nuovo_utente_ritorna_201(self, client):
        """
        Caso normale: registrazione con dati validi.
        La risposta deve essere 201 Created con l'ID dell'utente.
        """
        resp = client.post("/users/register", json={
            "username": "mario",
            "email": "mario@example.com",
            "password": "password123",
        })

        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["id"] is not None

    def test_registrazione_nuovo_utente_admin_ritorna_201(self, client):
        """
        Caso normale: registrazione con dati validi.
        La risposta deve essere 201 Created con l'ID dell'utente.
        """
        resp = client.post("/users/register", json={
            "username": "rossi_admin",
            "email": "rossi_admin@example.com",
            "password": "password123",
            "is_admin": True
        })

        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["id"] is not None
        
    def test_username_duplicato_ritorna_409(self, client):
        """
        Se un utente con lo stesso username esiste già, deve rispondere 409 Conflict.
        Registriamo lo stesso utente due volte.
        """
        payload = {
            "username": "mario",
            "email": "mario@example.com",
            "password": "password123",
        }
        client.post("/users/register", json=payload)  # Prima registrazione: OK
        resp = client.post("/users/register", json=payload)  # Seconda: deve fallire

        assert resp.status_code == 409

    def test_registrazione_senza_email_ritorna_422(self, client):
        """
        La validazione Marshmallow deve rifiutare richieste con campi mancanti.
        422 Unprocessable Entity = dati sintatticamente corretti ma semanticamente invalidi.
        """
        resp = client.post("/users/register", json={
            "username": "mario",
            # "email" mancante
            "password": "password123",
        })

        assert resp.status_code == 422

    def test_registrazione_senza_body_ritorna_422(self, client):
        """Senza body JSON, la validazione deve fallire."""
        resp = client.post("/users/register", json={})
        assert resp.status_code == 422


class TestLogin:
    """Test per POST /users/login"""

    def _registra_utente(self, client, username="mario", password="password123"):
        """Helper privato per non ripetere il codice di registrazione."""
        client.post("/users/register", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        })

    def test_login_con_credenziali_corrette_ritorna_token(self, client):
        """
        Login con credenziali valide: deve rispondere 200 con access_token
        e refresh_token.
        """
        self._registra_utente(client)

        resp = client.post("/users/login", json={
            "username": "mario",
            "password": "password123",
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        # I token non devono essere stringhe vuote
        assert len(data["access_token"]) > 0

    def test_login_password_errata_ritorna_401(self, client):
        """
        Con password sbagliata deve rispondere 401 Unauthorized.
        Non deve trapelare se il problema è la password o lo username (sicurezza).
        """
        self._registra_utente(client)

        resp = client.post("/users/login", json={
            "username": "mario",
            "password": "PASSWORDSBAGLIATA",
        })

        assert resp.status_code == 401

    def test_login_utente_inesistente_ritorna_401(self, client):
        """Tentare il login con uno username che non esiste deve restituire 401."""
        resp = client.post("/users/login", json={
            "username": "utente_che_non_esiste",
            "password": "password123",
        })

        assert resp.status_code == 401

    def test_login_senza_username_ritorna_422(self, client):
        """Username mancante: la validazione Marshmallow deve rifiutare la richiesta."""
        resp = client.post("/users/login", json={"password": "password123"})
        assert resp.status_code == 422


class TestEndpointProtetti:
    """
    Verifica che gli endpoint protetti rifiutino richieste senza token JWT.
    Questi test non usano auth_headers → nessun token nell'header Authorization.
    """

    def test_get_requests_senza_token_ritorna_401(self, client):
        resp = client.get("/requests")
        assert resp.status_code == 401

    def test_post_requests_senza_token_ritorna_401(self, client):
        resp = client.post("/requests/mail", json={"text": "test"})
        assert resp.status_code == 401

    def test_token_invalido_ritorna_401(self, client):
        """Un token malformato o firmato con chiave diversa deve essere rifiutato."""
        resp = client.get("/requests", headers={
            "Authorization": "Bearer questo-non-e-un-token-jwt-valido"
        })
        assert resp.status_code == 401
