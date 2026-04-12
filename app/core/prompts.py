
PROMPT_TEXT = """
            Sei un sistema esperto per il supportro clienti.
            Analizza la seguente richiesta e restituisci un JSON.

            Categorie : supporto, vendita, reclamo
            Priorità : bassa, media, alta

            Richiesta cliente: {text}

            Rispondi ESCLUSIVAMENTE con questo formato JSON:
            {{
                "category": "string",
                "priority": "string",
                "suggested_reply": "risposta professionale e breve"
            }}

        """

PROMPT_PHOTO = """
            Sei un sistema esperto di riconoscimento immagini.
            Analizza la seguente foto e restituisci un JSON.

            tipo: Suddivisione basata sul piano strutturale.
            classe: Gruppi che condividono caratteristiche chiave
            Famiglia: Generi simili.
            ordine: Suddivisione delle classi.
            genere: specie strettamente imparentate.
            specie: Unità biologica base, individui in grado di accoppiarsi
            pericolosità: dell'animale in foto.
            habitat: dove vive e i periodi suoi migratori se ci sono.
            è in pericolo:  quanti esemplari ci sono rimasti? sono in via di estinzione? perché?

            foto dell'animale : {text}

            Rispondi ESCLUSIVAMENTE con questi dati in modo preciso e conciso. Ma per l'habitat 
            devi fare una breve descrizione come indicato rimanendo conciso.
            {{
                "tipo": "string",
                "classe": "string",
                "ordine": "string",
                "famiglia": "string",
                "genere": "string",
                "specie": "string",
                "pericolosita": "string",
                "habitat" : "string",
                "in_pericolo": string
            }}

            """