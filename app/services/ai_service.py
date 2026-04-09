import time
import json
from  google import genai
from typing import TypedDict
from app.core.config import Config
from app.core.prompts import PROMPT_PHOTO, PROMPT_TEXT


class AIResponse(TypedDict):
    category: str
    priority: str
    suggested_reply: str

class AIResponsefoto(TypedDict):
    Razza: str
    Famiglia: str
    descrizione: str
    pericolosità: str
    classificazione: str

class AIService:
    def __init__(self, logger):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_id = Config.GEMINI_MODEL
        self.logger = logger

    def _retry_call(self, func, retries=3, delay=1):
        for attempts in range(retries):
            try:
                return func()
            except Exception as e:
                self.logger.error(f"[AI ERROR] Tentativo: {attempts + 1} fallito: {e}")
                if attempts < retries -1:
                    time.sleep(delay)
            
        return None

    def process_request(self, text: str)-> AIResponse:
        """
            Esegue classificazione e generazione risposta in unica chiamata
            (Risparmio token/tempo)
        """
        self.logger.info(f"🧠 Interrogazione Gemini ({self.model_id})")
        # prompt = f"""
        #     Sei un sistema esperto per il supportro clienti.
        #     Analizza la seguente richiesta e restituisci un JSON.

        #     Categorie : supporto, vendita, reclamo
        #     Priorità : bassa, media, alta

        #     Richiesta cliente: "{text}"

        #     Rispondi ESCLUSIVAMENTE con questo formato JSON:
        #     {{
        #         "category": "string",
        #         "priority": "string",
        #         "suggested_reply": "risposta professionale e breve"
        #     }}

        # """
        prompt = PROMPT_TEXT.format(text)
        def call():
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            return json.loads(response.text)

        result = self._retry_call(call)
        # Fallback sicuro in caso di errore totale dopo i retries
        if not result:
            return {
                "category": "unknown",
                "priority": "unknown",
                "suggested_reply": "unknown",
            }
        
        return result
    

    def process_request_image_description(self, text: str)-> AIResponsefoto:
        """
            Esegue classificazione e generazione risposta in unica chiamata
            (Risparmio token/tempo)
        """
        self.logger.info(f"🧠 Interrogazione Gemini ({self.model_id})")
        prompt = PROMPT_PHOTO.format(text=text)
        def call():
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            return json.loads(response.text)

        result = self._retry_call(call)
        # Fallback sicuro in caso di errore totale dopo i retries
        if not result:
            return {
                "tipo": "unknown",
                "classe": "unknown",
                "ordine": "unknown",
                "famiglia": "unknown",
                "genere": "unknown",
                "specie": "unknown",
                "pericolosità": "unknown"
            }
        
        return result