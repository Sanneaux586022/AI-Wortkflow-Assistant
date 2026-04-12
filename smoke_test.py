import requests
import json
import time
import io

# Configurazione locale
BASE_URL = "http://127.0.0.1:5000/requests"
BASE_URL_USERS = "http://127.0.0.1:5000/users"

TEST_USER = {"username": "smokeuser", "email": "smoke@test.com", "password": "SmokePass123"}


def _register_and_login() -> dict:
    """
    Registra l'utente di test (ignora 409 se già esiste) e fa login.
    Restituisce gli header Authorization con il token fresh.
    """
    requests.post(f"{BASE_URL_USERS}/register", json=TEST_USER)

    resp = requests.post(f"{BASE_URL_USERS}/login", json={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    if resp.status_code != 200:
        raise RuntimeError(f"Login fallito: {resp.status_code} - {resp.text}")

    token = resp.json()["access_token"]
    print(f"   Token ottenuto: {token[:30]}...")
    return {"Authorization": f"Bearer {token}"}


def run_smoke_test():
    print("🚀 Avvio Smoke Test — AI Workflow Assistant")
    print("=" * 55)

    # ─── AUTH ────────────────────────────────────────────────
    print("\n[AUTH] Registrazione e login utente di test...")
    try:
        auth = _register_and_login()
        print("   ✅ Autenticazione riuscita.")
    except Exception as e:
        print(f"   💥 Autenticazione fallita: {e}")
        return

    # ─── 1. CREA RICHIESTA MAIL ──────────────────────────────
    print("\n[1] POST /requests — Crea richiesta mail...")
    mail_payload = {
        "mail_text": "Buongiorno, ho un problema con l'ultimo ordine #12345. "
                     "Il prodotto è arrivato graffiato. Posso avere un reso?",
        "request_type": "mail",
    }
    try:
        resp = requests.post(BASE_URL, json=mail_payload, headers=auth)
        if resp.status_code == 201:
            mail_id = resp.json()["id"]
            print(f"   ✅ Richiesta mail creata con ID: {mail_id}")
        else:
            print(f"   ❎ Errore: {resp.status_code} — {resp.text}")
            return
    except Exception as e:
        print(f"   💥 Connessione fallita: {e}")
        return

    # ─── 2. LISTA RICHIESTE MAIL ─────────────────────────────
    print(f"\n[2] GET /requests — Verifica presenza ID {mail_id}...")
    resp = requests.get(BASE_URL, headers=auth)
    if resp.status_code == 200:
        items = resp.json()
        found = any(r["id"] == mail_id for r in items)
        print(f"   {'✅ Trovata' if found else '❎ Non trovata'} ({len(items)} richieste totali)")
    else:
        print(f"   ❎ Errore: {resp.status_code} — {resp.text}")

    # ─── 3. ELABORAZIONE AI — MAIL ──────────────────────────
    print(f"\n[3] POST /requests/{mail_id}/process — Elaborazione AI mail...")
    start = time.time()
    resp = requests.post(f"{BASE_URL}/{mail_id}/process", headers=auth)
    duration = time.time() - start

    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Risposta AI in {duration:.2f}s")
        print(f"      Categoria:          {result.get('category')}")
        print(f"      Priorità:           {result.get('priority')}")
        print(f"      Risposta suggerita: {str(result.get('suggested_reply', ''))[:70]}...")
        print(f"      Stato:              {result.get('status')}")
    else:
        print(f"   ❎ Errore elaborazione AI: {resp.status_code} — {resp.text}")

    # ─── 4. CARICA FOTO ─────────────────────────────────────
    print("\n[4] POST /requests/foto — Carica immagine animale...")
    foto_path = "multimedia/uploads/tigras.jpeg"
    try:
        with open(foto_path, "rb") as f:
            file_bytes = f.read()

        resp = requests.post(
            f"{BASE_URL}/foto",
            files={"file": ("tigras.jpeg", io.BytesIO(file_bytes), "image/jpeg")},
            data={"request_type": "foto"},
            headers=auth,
        )
        if resp.status_code == 201:
            foto_id = resp.json()["id"]
            print(f"   ✅ Richiesta foto creata con ID: {foto_id}")
        else:
            print(f"   ❎ Errore upload: {resp.status_code} — {resp.text}")
            foto_id = None
    except FileNotFoundError:
        print(f"   ⚠️  File '{foto_path}' non trovato — test foto saltato.")
        foto_id = None
    except Exception as e:
        print(f"   💥 Errore: {e}")
        foto_id = None

    # ─── 5. LISTA RICHIESTE FOTO ─────────────────────────────
    if foto_id is not None:
        print(f"\n[5] GET /requests/foto — Verifica presenza ID {foto_id}...")
        resp = requests.get(f"{BASE_URL}/foto", headers=auth)
        if resp.status_code == 200:
            items = resp.json()
            found = any(r["id"] == foto_id for r in items)
            print(f"   {'✅ Trovata' if found else '❎ Non trovata'} ({len(items)} foto totali)")
        else:
            print(f"   ❎ Errore: {resp.status_code} — {resp.text}")

        # ─── 6. ELABORAZIONE AI — FOTO ───────────────────────
        print(f"\n[6] POST /requests/foto/{foto_id}/process — Classificazione AI animale...")
        start = time.time()
        resp = requests.post(f"{BASE_URL}/foto/{foto_id}/process", headers=auth)
        duration = time.time() - start

        if resp.status_code == 200:
            result = resp.json()
            print(f"   ✅ Classificazione AI in {duration:.2f}s")
            print(f"      Tipo:       {result.get('tipo')}")
            print(f"      Classe:     {result.get('classe')}")
            print(f"      Ordine:     {result.get('ordine')}")
            print(f"      Famiglia:   {result.get('famiglia')}")
            print(f"      Genere:     {result.get('genere')}")
            print(f"      Specie:     {result.get('specie')}")
            print(f"      Pericolosità: {result.get('pericolosita')}")
            print(f"      Habitat:    {str(result.get('habitat', ''))[:70]}...")
            print(f"      In pericolo: {str(result.get('in_pericolo', ''))[:70]}...")
            print(f"      Stato:      {result.get('status')}")
        else:
            print(f"   ❎ Errore classificazione AI: {resp.status_code} — {resp.text}")

    print("\n" + "=" * 55)
    print("🏁 Smoke Test completato!")


if __name__ == "__main__":
    run_smoke_test()
