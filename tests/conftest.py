"""
conftest.py — Configurazione condivisa per tutti i test pytest.

Questo file viene caricato automaticamente da pytest prima di qualsiasi test.
Qui definiamo i "fixture": oggetti riutilizzabili (app, client, DB, token JWT)
che ogni test può richiedere semplicemente dichiarandoli come parametro.

Concetti chiave:
  - fixture(scope="session") → creato UNA VOLTA per tutta la sessione di test
  - fixture(scope="function") → creato di nuovo per OGNI singolo test (default)
  - autouse=True            → applicato automaticamente senza doverlo dichiarare
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# ─── Sovrascriviamo le variabili d'ambiente PRIMA di importare qualsiasi
# modulo del progetto. load_dotenv() in config.py non sovrascrive variabili
# già presenti nell'ambiente, quindi queste prendono la precedenza su .env.
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # DB in RAM, isolato
os.environ["GEMINI_API_KEY"] = "fake-key-for-tests"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
os.environ["PRIVATE_APP_KEY"] = "chiave-segreta-di-test-lunga-32-caratteri!"
os.environ["REDIS_URL"] = "redis://localhost:6379"


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: app Flask di test
# scope="session" → l'app viene creata una sola volta per tutta la sessione.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def app():
    """
    Crea l'app Flask configurata per i test:
    - Database SQLite in memoria (non lascia file su disco)
    - Redis mockato (non serve un server Redis reale)
    - Client Gemini mockato (non fa chiamate API reali)
    """
    # Mock Redis: restituisce None per ogni .get() → nessun token è revocato
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # Usiamo patch() come context manager per sostituire le dipendenze esterne
    # DURANTE L'IMPORT di main.py. Questo è fondamentale: l'import avviene
    # UNA SOLA VOLTA, e dobbiamo intercettare le istanze create a livello di modulo.
    with patch("redis.from_url", return_value=mock_redis), \
         patch("google.genai.Client"):  # Evita connessione reale a Gemini
        from main import create_app
        flask_app = create_app()

    flask_app.config["TESTING"] = True
    return flask_app


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: client HTTP
# Permette di fare richieste HTTP all'app senza avviare un server reale.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def client(app):
    """
    Client HTTP per simulare chiamate alle API nei test di integrazione.
    Uso: client.post("/users/register", json={...})
    """
    return app.test_client()


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: reset del database (autouse → si applica a OGNI test)
# Garantisce che ogni test parta con un database pulito e vuoto.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_db(app):
    """
    Prima di ogni test: svuota e ricrea tutte le tabelle.
    Dopo ogni test: chiude la sessione DB.

    Grazie a questo, i test sono completamente isolati tra loro:
    i dati creati in un test non influenzano il test successivo.
    """
    from app.db.database import db
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield  # ← qui viene eseguito il test
    with app.app_context():
        db.session.remove()


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: header JWT pronti all'uso
# Registra un utente di test, fa login, e restituisce l'header Authorization.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def auth_headers(client):
    """
    Restituisce gli header HTTP con un token JWT valido.
    Da usare nei test che richiedono autenticazione:

        def test_qualcosa(client, auth_headers):
            resp = client.get("/requests", headers=auth_headers)
    """
    client.post("/users/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
    })
    resp = client.post("/users/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: header JWT pronti all'uso
# Registra un utente admin di test, fa login, e restituisce l'header Authorization.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def admin_headers(client):
    """
    Restituisce gli header HTTP con un token JWT valido.
    Da usare nei test che richiedono autenticazione ed un utente admin:

        def test_qualcosa(client, admin_headers):
            resp = client.get("/requests", headers=admin_headers)
    """
    client.post("/users/register", json={
        "username": "testuser_admin",
        "email": "test_admin@example.com",
        "password": "password123",
        "is_admin": True
    })
    resp = client.post("/users/login", json={
        "username": "testuser_admin",
        "password": "password123",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}