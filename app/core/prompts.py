
PROMPT_TEXT = """
            Sei un sistema esperto per il supportro clienti.
            Analizza la seguente richiesta e restituisci un JSON.

            Categorie : supporto, vendita, reclamo
            Priorità : bassa, media, alta

            Richiesta cliente: "{text}"

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

            Razza: Razza dell'animale in foto.
            Famiglia: famiglia dell'animale in foto.
            descrizione: del rapporto dell'animale in foto con l'uomo.
            pericolosità: dell'animale in foto.
            classificazione dell'animale in foto.

            foto dell'animale : {text}

            Rispondi ESCLUSIVAMENTE con questi dati in modopreciso e conciso.

            """