# AI Workflow Assistant

Sistema di gestione richieste clienti con classificazione automatica tramite Google Gemini AI.

## Descrizione

L'applicazione riceve richieste di supporto clienti (testo o immagini), le archivia nel database e le analizza con Gemini AI per:

**Richieste testo:**
- **Classificare** il tipo di richiesta (`supporto`, `vendita`, `reclamo`)
- **Assegnare una priorità** (`bassa`, `media`, `alta`)
- **Generare una risposta suggerita** professionale

**Richieste foto (classificazione animali):**
- **Identificare** razza, famiglia, classificazione dell'animale
- **Descrivere** il rapporto con l'uomo e il grado di pericolosità

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Flask + Flask-Smorest |
| ORM | Flask-SQLAlchemy |
| Autenticazione | Flask-JWT-Extended |
| AI | Google Gemini 2.5 Flash |
| Token blocklist | Redis |
| Database dev | SQLite |
| Database prod | PostgreSQL |
| Containerizzazione | Docker + Docker Compose |

> **Nota:** RQ (Redis Queue) è incluso come dipendenza ma l'elaborazione è attualmente **sincrona** — non vengono usati worker in background.

## Prerequisiti

- Python 3.10+
- Docker e Docker Compose (per avvio containerizzato)
- Una chiave API Google Gemini (ottienila su [Google AI Studio](https://aistudio.google.com/))

---

## Setup

### 1. Clona il repository

```bash
git clone <url-repo>
cd ai-workflow-assistant
```

### 2. Crea il file `.env`

```bash
cp .env.example .env
```

Compila `.env` con i tuoi valori:

```env
GEMINI_API_KEY=la-tua-chiave-gemini
GEMINI_MODEL=gemini-2.5-flash
SQLALCHEMY_DATABASE_URI=sqlite:///app.db
PRIVATE_APP_KEY=una-chiave-segreta-lunga-almeno-32-caratteri
REDIS_URL=redis://redis:6379
```

> **Attenzione:** non committare mai `.env` nel repository. Contiene segreti.

### 3a. Avvio con Docker (consigliato)

```bash
docker compose up --build
```

L'API sarà disponibile su `http://localhost:5000`.

### 3b. Avvio in locale (senza Docker)

```bash
# Installa le dipendenze con uv
pip install uv
uv pip install -e ".[dev]"

# Crea la cartella per i file caricati
mkdir -p multimedia/uploads

# Avvia Redis (richiesto per JWT blocklist)
docker run -d -p 6379:6379 redis:alpine

# Avvia l'applicazione
python main.py
```

> **Attenzione locale:** il salvataggio delle foto usa il path `/app/multimedia/uploads` (pensato per Docker). In locale, assicurati che il path esista o adatta `ingestion_service.py`.

### Documentazione API interattiva (Swagger UI)

Con l'app avviata, visita: `http://localhost:5000/docs/swagger-ui`

---

## Endpoint API

### Autenticazione (`/users`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/users/register` | Registra un nuovo utente | No |
| `POST` | `/users/login` | Login, restituisce access + refresh token | No |
| `POST` | `/users/refresh` | Rinnova l'access token | Refresh token |
| `POST` | `/users/logout` | Revoca il token corrente | Access token (fresh) |

### Richieste testo (`/requests`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/requests` | Crea una nuova richiesta testo | Access token |
| `GET` | `/requests` | Elenca tutte le richieste testo | Access token |
| `GET` | `/requests/<id>` | Dettaglio di una richiesta testo | Access token |
| `POST` | `/requests/<id>/process` | Avvia elaborazione AI | Access token (fresh) |
| `DELETE` | `/requests` | Elimina **tutte** le richieste | Admin + fresh token |
| `DELETE` | `/requests/<id>` | Elimina una singola richiesta | Admin + fresh token |

### Richieste foto (`/requests/foto`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/requests/foto` | Carica una foto (multipart/form-data, campo `file`) | Access token |
| `GET` | `/requests/foto` | Elenca tutte le richieste foto | Access token |
| `GET` | `/requests/foto/<id>` | Dettaglio di una richiesta foto | Access token |
| `POST` | `/requests/foto/<id>/process` | Avvia classificazione AI dell'immagine | Access token (fresh) |

---

## Esempio: flusso completo via curl

```bash
# 1. Registrazione
curl -X POST http://localhost:5000/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "mario", "email": "mario@example.com", "password": "password123"}'

# 2. Login → copia il valore di "access_token"
curl -X POST http://localhost:5000/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "mario", "password": "password123"}'

# 3. Crea una richiesta cliente
curl -X POST http://localhost:5000/requests \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Non riesco ad accedere al mio account, ho bisogno di aiuto urgente."}'
# → risposta: {"id": 1, "status": "pending", ...}

# 4. Avvia l'elaborazione AI sulla richiesta con id=1
# (richiede fresh token: riesegui il login per ottenerne uno nuovo)
curl -X POST http://localhost:5000/requests/1/process \
  -H "Authorization: Bearer <fresh_access_token>"
# → risposta: {"category": "supporto", "priority": "alta", "suggested_reply": "..."}

# 5. Carica una foto di un animale
curl -X POST http://localhost:5000/requests/foto \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/percorso/del/file/immagine.jpg"
# → risposta: {"id": 1, "status": "pending", "foto_path": "...", ...}

# 6. Avvia la classificazione AI della foto con id=1
curl -X POST http://localhost:5000/requests/foto/1/process \
  -H "Authorization: Bearer <fresh_access_token>"
# → risposta: {"classificazione": "Mammifero", "razza": "...", "famiglia": "...", ...}
```

---

## Eseguire i test

```bash
# Installa le dipendenze di test (incluse con [dev])
uv pip install -e ".[dev]"

# Esegui tutti i test
pytest

# Con output dettagliato
pytest -v

# Solo i test unitari (veloci, nessuna connessione esterna)
pytest tests/unit/ -v

# Solo i test di integrazione (testano le API end-to-end)
pytest tests/integration/ -v

# Con report di copertura
pytest --cov=app --cov-report=term-missing
```

---

## Struttura del progetto

```
ai-workflow-assistant/
├── main.py                      # Entry point e factory dell'app Flask
├── pyproject.toml               # Dipendenze progetto
├── Dockerfile
├── docker-compose.yml
├── .env                         # Segreti locali (NON committare)
├── .env.example                 # Template variabili d'ambiente
├── smoke_test.py                # Script di test manuale
├── multimedia/
│   └── uploads/                 # Foto caricate dagli utenti
└── app/
    ├── errors.py                # Handler di errore globali (attualmente disabilitato)
    ├── core/
    │   ├── config.py            # Configurazione centralizzata (legge da .env)
    │   ├── logger.py            # Setup logging
    │   └── prompts.py           # Prompt AI (testo e foto)
    ├── db/
    │   ├── database.py          # Istanza SQLAlchemy condivisa
    │   └── redis_client.py      # Helper connessione Redis
    ├── models/
    │   ├── request.py           # Modelli ORM: CustomerRequest, CustomerRequestFoto
    │   └── user.py              # Modello ORM: User
    ├── api/
    │   ├── request_routes.py    # Blueprint endpoint /requests
    │   ├── user_routes.py       # Blueprint endpoint /users
    │   └── schemas.py           # Schemi Marshmallow (validazione I/O)
    └── services/
        ├── ai_service.py        # Integrazione Google Gemini API
        ├── ingestion_service.py # Creazione e salvataggio richieste
        ├── processing_service.py# Orchestrazione pipeline AI
        └── user_service.py      # Registrazione, login, token
```

## Architettura

```
Client HTTP
    │
    ▼
┌─────────────────────────────────────┐
│  API Layer (Flask-Smorest)          │  ← validazione I/O con Marshmallow
│  request_routes.py / user_routes.py │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Service Layer                      │  ← logica di business
│  ingestion / processing / user      │
└──────┬──────────────┬───────────────┘
       │              │
       ▼              ▼
┌────────────┐  ┌─────────────────────┐
│ SQLAlchemy │  │  Google Gemini API  │
│ (SQLite /  │  │  (classificazione + │
│ PostgreSQL)│  │   risposta suggerita│
└────────────┘  └─────────────────────┘
       │
       ▼
┌────────────┐
│   Redis    │  ← token blocklist (logout)
└────────────┘
```

## Variabili d'ambiente

| Variabile | Descrizione | Esempio |
|---|---|---|
| `GEMINI_API_KEY` | Chiave API Google Gemini | `AIzaSy...` |
| `GEMINI_MODEL` | Modello Gemini da usare | `gemini-2.5-flash` |
| `SQLALCHEMY_DATABASE_URI` | URI del database | `sqlite:///app.db` |
| `PRIVATE_APP_KEY` | Chiave segreta per JWT | stringa casuale lunga |
| `REDIS_URL` | URL connessione Redis | `redis://redis:6379` |
