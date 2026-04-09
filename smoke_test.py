import requests
import json
import time

# Configurazione locale
BASE_URL = "http://127.0.0.1:5000/requests"
BASE_URL_1 = "http://127.0.0.1:5000/users"

def run_smoke_test():
    print(" 🚀 Avvio Smoke Test per AI workflow Assistant...")
    print("-" * 50)

    # 1. TEST POST : Creazione di una richiesta

    payload = {
        "text": "Buongiorno, Ho un problema con l'ultimo ordine #12345. Il prodotto è arrivato graffiato."
        "Posso avere un reso?"
    }

    try:
        print("📥 1. Invio richiesta...")
        response = requests.post(BASE_URL, json=payload)

        if response.status_code == 201:
            data = response.json()
            request_id = data["id"]
            print(f"👍 Successo! Richiesta creata con ID: {request_id}")
        else:
            print(f"👎 Errore nella Creazione: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"💥 Connessione fallita: {e}")
        return 
    # 2. TEST GET : Verifica che la richiesta sia presente nella lista
    print(f"🔍 2. Verifica presenza ID {request_id} nella lista...")

    list_res = requests.get(BASE_URL)
    if any(r["id"] == request_id for r in list_res.json()):
        print("✅ Richiesta trovata correttamente.")
    else:
        print("❎ Richiesta non trovata nella lista GET.")

    # 3. TEST PROCESS: Scatena L'AI
    print(f"🧠 3. Avvia elaborazione AI per ID {request_id} (atteasa risposta...)")
    start_time = time.time()
    

    proc_res = requests.post(f"{BASE_URL}/{request_id}/process")
    duration = time.time() - start_time

    if proc_res.status_code == 200:
        result = proc_res.json()
        print(f"✅ AI ha risposto in {duration:.2f} secondi!")
        print("    ------------------------------------------")
        print(f"    CATEGORIA: {result.get('category')}")
        print(f"    PRIORITA:  {result.get('priority')}")
        print(f"    RISPOSTA SUGGERITA: {result.get('suggested_reply')[:80]}...")
        print(f"    STATO:     {result.get('status')}")
        print("    ---------------------------------")
    else:
        print(f"❎ Errore durante il processing AI : {proc_res.text}")

    # 4. Test che si occupa della registrazione di un nuovo utente
    print("4. Inizio la procedura di registrazione")
    payload = {"username":"sano", "email": "Turbo_58@test.com", "password": "tryMe"}
    try :
        response = requests.post(f"{BASE_URL_1}/register", json=payload)

        if response.status_code == 201:
            print("registrazione riuscita")
            data = response.json()
            print(f"{data}")
        else:
            print(f"Errore durante la registrazione: {response.status_code} - {response.text}")
    except Exception as e:
        print (f"💥 Connessione fallita: {e}")

    # 5. Test della login con l'utente appena registrato
    print("5. Inizio la procedura di login")
    payload = payload = {"username":"sano", "password": "tryMe"}
    try:
        response = requests.post(f"{BASE_URL_1}/login", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Autenticazione riuscita: {data['access_token']}\n {data['refresh_token']}")
        else:
            print(f"Credenziali non valide.{response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connessione fallita: {e}")

    print("\n🏁 Smoke Test completato!")

if __name__ == "__main__":
    run_smoke_test()