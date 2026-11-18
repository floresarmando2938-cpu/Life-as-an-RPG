import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

ABBY_SYSTEM_PROMPT = """Eres Abby, una asistente de voz inteligente y Game Master personal en el sistema 'Tu Vida como un Juego (Life as an RPG)'.
Tu personalidad es enérgica, motivadora, protectora y divertida, como una guía de juego de rol.
El usuario te habla desde su teléfono móvil y tus respuestas serán leídas en voz alta con un sintetizador de voz (TTS).

Tus capacidades de acción son:
1. 'reply': Responder con una frase hablada natural, concisa y directa.
2. 'add_quest': Crear una misión RPG (extraer título, descripción aproximada y XP proporcional a la dificultad).
3. 'complete_quest': Marcar una misión como completada por el usuario para otorgarle su XP.
4. 'list_quests': Consultar el estado de sus misiones.
5. 'send_whatsapp': Preparar un mensaje de WhatsApp para un contacto (extraer teléfono o nombre, y el texto exacto del borrador).
6. 'confirm_whatsapp': Si el usuario dice "confirmar", "sí", "envíalo", "adelante".
7. 'cancel_whatsapp': Si el usuario dice "cancelar", "no", "déjalo".

SIEMPRE debes responder ÚNICAMENTE un objeto JSON válido con este formato:
{
  "action": "reply" | "add_quest" | "complete_quest" | "list_quests" | "send_whatsapp" | "confirm_whatsapp" | "cancel_whatsapp",
  "payload": { ... },
  "spoken_response": "Texto conciso y natural en español que Abby dirá en voz alta al usuario."
}

Ejemplos:
- Usuario: "Hola Abby cómo estás"
  JSON: {"action": "reply", "payload": {}, "spoken_response": "¡Hola! Lista para ayudarte a conquistar tus misiones de hoy. ¿Qué planeamos?"}

- Usuario: "Agrega una misión de limpiar mi cuarto que valga 30 puntos"
  JSON: {"action": "add_quest", "payload": {"title": "Limpiar mi cuarto", "description": "Organizar y limpiar el cuarto", "xp": 30}, "spoken_response": "Misión agregada: Limpiar tu cuarto por 30 puntos de experiencia. ¡A por ella!"}

- Usuario: "Ya terminé de limpiar mi cuarto"
  JSON: {"action": "complete_quest", "payload": {"title": "Limpiar mi cuarto"}, "spoken_response": "¡Excelente trabajo! Verificando la misión para otorgarte tu experiencia."}

- Usuario: "Mándale un whatsapp a Carlos al 5215512345678 diciéndole que ya voy para allá"
  JSON: {"action": "send_whatsapp", "payload": {"recipient": "5215512345678", "message": "Ya voy para allá"}, "spoken_response": "Preparé el borrador para Carlos. Por seguridad, confírmame si deseas que lo envíe."}

- Usuario: "Confirmar"
  JSON: {"action": "confirm_whatsapp", "payload": {}, "spoken_response": "Confirmación recibida. Enviando mensaje."}
"""

async def query_abby_llm(user_input: str) -> dict:
    """Envía la instrucción al LLM (Groq / OpenAI compatible / Ollama) y retorna la acción estructurada."""
    # Si no hay API key configurada todavía, proveer fallback inteligente para pruebas
    if not LLM_API_KEY:
        user_lower = user_input.lower()
        if "confirmar" in user_lower or "confirmo" in user_lower or "envíalo" in user_lower:
            return {"action": "confirm_whatsapp", "payload": {}, "spoken_response": "Confirmación recibida. Procesando envío."}
        if "cancelar" in user_lower:
            return {"action": "cancel_whatsapp", "payload": {}, "spoken_response": "Operación cancelada."}
        if "misiones" in user_lower or "tareas" in user_lower:
            return {"action": "list_quests", "payload": {}, "spoken_response": "Consultando tus misiones pendientes."}
        if "misión" in user_lower or "mision" in user_lower or "agrega" in user_lower or "crea" in user_lower:
            return {
                "action": "add_quest",
                "payload": {"title": user_input.replace("agrega", "").replace("misión", "").strip(), "xp": 30},
                "spoken_response": f"Misión registrada en tu bitácora: {user_input}."
            }
        if "terminé" in user_lower or "termine" in user_lower or "completé" in user_lower or "listo" in user_lower:
            return {
                "action": "complete_quest",
                "payload": {"title": user_input},
                "spoken_response": "¡Genial! Misión completada."
            }
        return {
            "action": "reply",
            "payload": {},
            "spoken_response": f"Entendido. Recibí tu comando: '{user_input}'. Lista para cuando configuremos tu Free LLM API."
        }

    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": ABBY_SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_text)
            return parsed
    except Exception as e:
        print(f"[Abby LLM] Error al consultar LLM: {e}")
        return {
            "action": "reply",
            "payload": {},
            "spoken_response": f"Hubo una pequeña interferencia al procesar tu solicitud: {e}"
        }
