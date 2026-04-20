# AI Workflow Assistant

Sistema di gestione richieste clienti con classificazione automatica tramite Google Gemini AI.

## Descrizione

L'applicazione riceve richieste di supporto clienti (testo mail o immagini di animali), le archivia nel database e le elabora in background tramite worker RQ (Redis Queue) che invocano l'AI Google Gemini 2.5 Flash.

**Richieste mail:**
- **Classificare** il tipo di richiesta (`supporto`, `vendita`, `reclamo`)
- **Assegnare una priorità** (`bassa`, `media`, `alta`)
- **Generare una risposta suggerita** professionale

**Richieste foto (classificazione animali):**
- **Classificare tassonomicamente** l'animale (tipo, classe, ordine, famiglia, genere, specie)
- **Descrivere** pericolosità, habitat e stato di conservazione

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Flask 3.x + Flask-Smorest |
| ORM | Flask-SQLAlchemy + SQLAlchemy 2.x |
| Autenticazione | Flask-JWT-Extended (access + refresh token) |
| Validazione I/O | Marshmallow |
| AI | Google Gemini 2.5 Flash (`google-genai`) |
| Token blocklist | Redis |
| Coda task asincroni | RQ (Redis Queue) |
| Rate limiting | Flask-Limiter (backend Redis) |
| CORS | Flask-CORS |
| Database dev | SQLite (in-memory per test, file per sviluppo) |
| Database prod | PostgreSQL 16 |
| Server prod | Gunicorn |
| Containerizzazione | Docker + Docker Compose |
| Gestione dipendenze | uv |

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
# Google Gemini
GEMINI_API_KEY=la-tua-chiave-gemini
GEMINI_MODEL=gemini-2.5-flash

# Database (produzione PostgreSQL, sviluppo SQLite)
SQLALCHEMY_DATABASE_URI=sqlite:///app.db

# JWT
PRIVATE_APP_KEY=una-chiave-segreta-lunga-almeno-32-caratteri

# Redis
REDIS_URL=redis://redis:6379

# Protezione endpoint admin (cron)
CRON_SECRET=una-chiave-segreta-per-il-cron

# Origini CORS consentite (virgola-separato)
ALLOWED_ORIGINS=http://localhost:3000

# Email (opzionale, per invio mail di benvenuto via Mailgun)
MAILGUN_API_KEY=
MAILGUN_DOMAIN_NAME=
```

> **Attenzione:** non committare mai `.env` nel repository. Contiene segreti.

### 3a. Avvio con Docker (consigliato)

```bash
docker compose up --build
```

Vengono avviati 6 servizi:
- `api` — server Flask (porta 5000)
- `db` — PostgreSQL 16
- `redis` — Redis
- `worker_mail` — worker RQ per elaborazione mail
- `worker_foto` — worker RQ per elaborazione foto
- `worker_email` — worker RQ per invio email di registrazione

L'API sarà disponibile su `http://localhost:5000`.

### 3b. Avvio in locale (senza Docker)

```bash
# Installa le dipendenze
pip install uv
uv sync

# Crea la cartella per i file caricati
mkdir -p app/multimedia/uploads

# Avvia Redis (richiesto per JWT blocklist, rate limiter e code RQ)
docker run -d -p 6379:6379 redis:alpine

# Avvia i worker RQ (in terminali separati)
uv run rq worker mail_processing
uv run rq worker foto_processing
uv run rq worker emails

# Avvia l'applicazione
uv run python main.py
```

> **Nota:** il salvataggio delle foto usa il path `/app/multimedia/uploads` (configurato per Docker).
> In locale, modifica il percorso in `app/services/ingestion_service.py`.

### Documentazione API interattiva (Swagger UI)

Con `FLASK_ENV=development` e l'app avviata:

```
http://localhost:5000/docs/swagger-ui
```

---

## Endpoint API

### Autenticazione (`/users`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/users/register` | Registra un nuovo utente | No |
| `POST` | `/users/login` | Login → access token (fresh) + refresh token | No |
| `POST` | `/users/refresh` | Rinnova l'access token (non fresh) | Refresh token |
| `POST` | `/users/logout` | Revoca il token corrente (aggiunge JTI a blocklist Redis) | Access token (fresh) |

### Richieste mail (`/requests/mail`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/requests/mail` | Crea una nuova richiesta mail | Access token |
| `GET` | `/requests/mail` | Elenca tutte le richieste mail | Access token |
| `GET` | `/requests/mail/<id>` | Dettaglio di una singola richiesta mail | Access token |
| `POST` | `/requests/mail/<id>/process` | Accoda il task AI → risponde 202 Accepted | Access token (fresh) |
| `DELETE` | `/requests/mail` | Elimina **tutte** le richieste mail | Admin + fresh token |
| `DELETE` | `/requests/mail/<id>` | Elimina una singola richiesta mail | Admin + fresh token |

### Richieste foto (`/requests/foto`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `POST` | `/requests/foto` | Carica una foto (multipart/form-data, campo `file`) | Access token |
| `GET` | `/requests/foto` | Elenca tutte le richieste foto | Access token |
| `GET` | `/requests/foto/<id>` | Dettaglio di una singola richiesta foto | Access token |
| `POST` | `/requests/foto/<id>/process` | Accoda il task AI → risponde 202 Accepted | Access token (fresh) |
| `DELETE` | `/requests/foto` | Elimina **tutte** le richieste foto | Admin + fresh token |
| `DELETE` | `/requests/foto/<id>` | Elimina una singola richiesta foto | Admin + fresh token |

### Aggregato (`/requests`)

| Metodo | Endpoint | Descrizione | Token richiesto |
|---|---|---|---|
| `GET` | `/requests` | Lista di tutte le richieste (mail + foto) in formato base | Access token |

### Admin — elaborazione batch (`/admin`)

Questi endpoint sono protetti tramite header `X-cron-secret` e pensati per essere invocati da un cron job esterno.

| Metodo | Endpoint | Descrizione | Header richiesto |
|---|---|---|---|
| `POST` | `/admin/process-pending/mail` | Elabora con AI tutte le mail in stato `pending` | `X-cron-secret` |
| `POST` | `/admin/process-pending/foto` | Elabora con AI tutte le foto in stato `pending` | `X-cron-secret` |

---

## Flusso di elaborazione (asincrono)

```
Client                         API (Flask)              Redis Queue        Worker RQ
  │                                │                         │                 │
  │  POST /requests/mail           │                         │                 │
  │ ─────────────────────────────► │                         │                 │
  │                         salva nel DB                     │                 │
  │  201 {id: 1, status: pending}  │                         │                 │
  │ ◄───────────────────────────── │                         │                 │
  │                                │                         │                 │
  │  POST /requests/mail/1/process │                         │                 │
  │ ─────────────────────────────► │                         │                 │
  │                         enqueue(process_mail_task, 1) ──►│                 │
  │  202 {message: "in elaborazione"} │                      │  consume task   │
  │ ◄───────────────────────────── │                         │ ───────────────►│
  │                                │                         │          chiama Gemini AI
  │                                │                         │          aggiorna DB
  │  GET /requests/mail/1          │                         │                 │
  │ ─────────────────────────────► │                         │                 │
  │  200 {status: "processed", category: "supporto", ...}    │                 │
  │ ◄───────────────────────────── │                         │                 │
```

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
# → {"access_token": "eyJ...", "refresh_token": "eyJ..."}

# 3. Crea una richiesta mail
curl -X POST http://localhost:5000/requests/mail \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"mail_text": "Non riesco ad accedere al mio account.", "request_type": "mail"}'
# → {"id": 1, "status": "pending", "mail_text": "...", ...}

# 4. Accoda l'elaborazione AI (il token appena ottenuto al login è già fresh)
curl -X POST http://localhost:5000/requests/mail/1/process \
  -H "Authorization: Bearer <access_token>"
# → {"message": "Richiesta 1 in elaborazione."} (HTTP 202)

# 5. Verifica il risultato dopo l'elaborazione del worker
curl -X GET http://localhost:5000/requests/mail/1 \
  -H "Authorization: Bearer <access_token>"
# → {"status": "processed", "category": "supporto", "priority": "alta",
#    "suggested_reply": "...", ...}

# 6. Carica una foto di un animale (multipart/form-data)
curl -X POST http://localhost:5000/requests/foto \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/percorso/immagine.jpg" \
  -F "request_type=foto"
# → {"id": 1, "status": "pending", "foto_path": "...", ...}

# 7. Accoda la classificazione AI della foto
curl -X POST http://localhost:5000/requests/foto/1/process \
  -H "Authorization: Bearer <access_token>"
# → {"message": "Richiesta 1 in elaborazione."} (HTTP 202)

# 8. Verifica il risultato
curl -X GET http://localhost:5000/requests/foto/1 \
  -H "Authorization: Bearer <access_token>"
# → {
#     "tipo": "Mammifero", "classe": "Mammalia", "ordine": "Carnivora",
#     "famiglia": "Felidae", "genere": "Panthera", "specie": "Panthera tigris",
#     "pericolosita": "Alta",
#     "habitat": "Foreste tropicali e subtropicali dell'Asia",
#     "in_pericolo": "In pericolo critico — circa 3.900 esemplari selvatici",
#     "status": "processed"
#   }
```

---

## Eseguire i test

```bash
# Installa le dipendenze di test
uv sync --extra dev

# Esegui tutti i test
uv run python -m pytest

# Con output dettagliato
uv run python -m pytest -v

# Solo i test unitari (veloci, nessuna connessione esterna)
uv run python -m pytest tests/unit/ -v

# Solo i test di integrazione (testano le API end-to-end)
uv run python -m pytest tests/integration/ -v

# Con report di copertura
uv run python -m pytest --cov=app --cov-report=term-missing
```

I test usano:
- **SQLite in memoria** al posto di PostgreSQL (isolamento completo, nessun file su disco)
- **Redis mockato** (nessun server Redis necessario)
- **Gemini mockato** (nessuna chiamata API reale)
- **Reset del DB** prima di ogni test (fixture `autouse`)

---

## Struttura del progetto

```
ai-workflow-assistant/
├── main.py                      # Entry point: factory create_app() + inizializzazione code RQ
├── pyproject.toml               # Dipendenze progetto (uv)
├── Dockerfile
├── docker-compose.yml           # 6 servizi: api, db, redis, worker_mail, worker_foto, worker_email
├── docker-entrypoint.sh
├── .env                         # Segreti locali (NON committare)
├── .env.example                 # Template variabili d'ambiente
├── smoke_test.py                # Script di test manuale end-to-end
├── multimedia/
│   └── uploads/                 # Foto caricate dagli utenti
├── tests/
│   ├── conftest.py              # Fixture pytest: app, client, reset_db, auth_headers, admin_headers
│   ├── unit/
│   │   ├── test_ingestion_service.py   # 10 test unitari (mail + foto creation)
│   │   └── test_processing_service.py  # 13 test unitari (process + predict)
│   └── integration/
│       ├── test_user_routes.py         # 12 test integrazione /users
│       └── test_request_routes.py      # 27 test integrazione /requests
└── app/
    ├── errors.py                # Handler di errore globali (ValueError→400, LookupError→404, ecc.)
    ├── core/
    │   ├── config.py            # Configurazione centralizzata (legge da .env)
    │   ├── extensions.py        # Flask-Limiter (rate limiting)
    │   ├── logger.py            # Setup logging (stdout → Docker logs)
    │   ├── prompts.py           # Prompt AI (PROMPT_TEXT per mail, PROMPT_PHOTO per foto)
    │   └── redis_client.py      # Helper connessione Redis
    ├── db/
    │   └── database.py          # Istanza SQLAlchemy condivisa
    ├── models/
    │   ├── request.py           # ORM: BaseRequest (polymorphic), MailRequest, FotoRequest
    │   └── user.py              # ORM: User
    ├── api/
    │   ├── request_routes.py    # Blueprint /requests (mail + foto)
    │   ├── user_routes.py       # Blueprint /users
    │   ├── admin_routes.py      # Blueprint /admin (cron batch processing)
    │   └── schemas.py           # Schemi Marshmallow (validazione I/O)
    ├── services/
    │   ├── ai_service.py        # Integrazione Google Gemini API (retry logic)
    │   ├── ingestion_service.py # Creazione richieste: validazione file, salvataggio DB
    │   ├── processing_service.py# Orchestrazione pipeline AI: process() e predict()
    │   ├── common_service.py    # Lettura e cancellazione record dal DB
    │   └── user_service.py      # Registrazione, login, JWT, logout
    └── workers/
        └── tasks.py             # Task RQ: process_mail_task, process_foto_task, send_user_registration_email
```

---

## Modelli dati

### MailRequest

| Campo | Tipo | Descrizione |
|---|---|---|
| `id` | Integer | Chiave primaria (ereditata da BaseRequest) |
| `request_type` | String | Sempre `"mail"` |
| `status` | String | `pending` → `processed` / `error` |
| `mail_text` | Text | Testo originale della mail del cliente |
| `category` | String | `supporto`, `vendita`, `reclamo` (compilato dall'AI) |
| `priority` | String | `bassa`, `media`, `alta` (compilato dall'AI) |
| `suggested_reply` | Text | Risposta suggerita dall'AI |
| `extracted_data` | Text | Dati strutturati estratti (opzionale) |
| `feedback` | Text | Feedback dell'operatore (opzionale) |
| `created_at` | DateTime | Timestamp creazione |

### FotoRequest

| Campo | Tipo | Descrizione |
|---|---|---|
| `id` | Integer | Chiave primaria (ereditata da BaseRequest) |
| `request_type` | String | Sempre `"foto"` |
| `status` | String | `pending` → `processed` / `error` |
| `foto_path` | Text | Path del file salvato su disco |
| `tipo` | String | Suddivisione per piano strutturale (es. Mammifero) |
| `classe` | String | Classe biologica (es. Mammalia) |
| `ordine` | String | Ordine (es. Carnivora) |
| `famiglia` | String | Famiglia (es. Felidae) |
| `genere` | String | Genere (es. Panthera) |
| `specie` | String | Specie completa (es. Panthera tigris) |
| `pericolosita` | Text | Grado di pericolosità per l'uomo |
| `habitat` | Text | Descrizione habitat e migrazioni |
| `in_pericolo` | Text | Stato di conservazione e numero esemplari |
| `created_at` | DateTime | Timestamp creazione |

---

## Architettura

```
Client HTTP
    │
    ▼
┌────────────────────────────────────┐
│  API Layer (Flask-Smorest)         │  ← JWT auth, rate limiting, Marshmallow
│  request_routes / user_routes      │
│  admin_routes                      │
└─────────────────┬──────────────────┘
                  │ enqueue task
                  ▼
┌────────────────────────────────────┐
│  Redis Queue (RQ)                  │  ← mail_processing / foto_processing / emails
└─────────────────┬──────────────────┘
                  │ consume task
                  ▼
┌────────────────────────────────────┐
│  Worker Layer (RQ Workers)         │  ← process_mail_task / process_foto_task
│  ProcessingService                 │
└──────────┬─────────────────────────┘
           │                   │
           ▼                   ▼
┌──────────────────┐  ┌────────────────────┐
│ SQLAlchemy ORM   │  │ Google Gemini API  │
│ (SQLite / PgSQL) │  │ gemini-2.5-flash   │
└──────────────────┘  └────────────────────┘

Altre dipendenze trasversali:
  Redis  ← JWT token blocklist + rate limiter storage
  Mailgun ← invio email di registrazione (worker emails)
```

---

## Variabili d'ambiente

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| `GEMINI_API_KEY` | Chiave API Google Gemini | Sì |
| `GEMINI_MODEL` | Modello Gemini (`gemini-2.5-flash`) | Sì |
| `SQLALCHEMY_DATABASE_URI` | URI del database | Sì |
| `PRIVATE_APP_KEY` | Chiave segreta per JWT (min 32 char) | Sì |
| `REDIS_URL` | URL connessione Redis | Sì |
| `CRON_SECRET` | Token segreto per endpoint `/admin` | Sì |
| `FLASK_ENV` | `development` o `production` | No (default: production) |
| `ALLOWED_ORIGINS` | Origini CORS (virgola-separato) | No |
| `MAILGUN_API_KEY` | Chiave API Mailgun | No |
| `MAILGUN_DOMAIN_NAME` | Dominio Mailgun | No |

---

## Criticità note

### Validazione foto (magic number)

La validazione del tipo MIME delle immagini usa `python-magic` che legge i magic bytes del file. Nel contesto dei test viene mockato tramite `patch("app.services.ingestion_service.magic.from_buffer", return_value="image/jpeg")`. In produzione richiede `libmagic` installato nel sistema (incluso nel Dockerfile con `apt-get install libmagic1`).

### Path upload foto hardcoded

Il percorso di salvataggio delle foto è hardcoded a `/app/multimedia/uploads/` in `ingestion_service.py`. In ambiente locale senza Docker è necessario creare la directory o modificare il path.

### Token fresh obbligatorio per le operazioni critiche

Gli endpoint `/process`, `/logout` e `DELETE` richiedono un token "fresh" (ottenuto direttamente con login, non con refresh). Un token rinnovato via `/users/refresh` non è fresh e verrà rifiutato con 401.

### Workers RQ devono essere attivi per l'elaborazione AI

Dopo aver chiamato `POST /requests/mail/<id>/process`, l'API risponde immediatamente 202 ma l'elaborazione avviene in background. Se i worker RQ non sono attivi, le richieste restano in stato `pending` indefinitamente. Usare `/admin/process-pending/mail` (o foto) per forzare un'elaborazione batch sincrona.
