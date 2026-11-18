import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Módulos especializados de Abby
from supabase_client import supabase
from whatsapp_bridge import WhatsAppBridge
from gamification import GamificationManager
from llm_client import query_abby_llm
from tts_service import generate_speech_audio

app = FastAPI(
    title="Abby Coordinator API - Life as an RPG",
    description="Servidor central para el asistente por voz Abby conectado a Supabase, WhatsApp Bridge y Gamificación.",
    version="1.0.0"
)

# Permitir conexiones desde cualquier origen (móvil, local, túneles)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia singleton del puente de WhatsApp
whatsapp_bridge = WhatsAppBridge()

class CommandRequest(BaseModel):
    texto: str

class CommandResponse(BaseModel):
    respuesta: str
    accion_ejecutada: str
    detalles: dict = {}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "agent": "Abby RPG Coordinator",
        "supabase_connected": supabase is not None
    }

@app.post("/comando", response_model=CommandResponse)
async def handle_comando(req: CommandRequest):
    """
    Endpoint principal para tu Android (Moto G05):
    Recibe texto, lo procesa con Abby y devuelve texto limpio para TTS.
    """
    user_input = req.texto.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="El comando no puede estar vacío.")

    print(f"\n[Abby Recibió]: {user_input}")

    # 1. Consultar al LLM / Motor de Coordinación
    decision = await query_abby_llm(user_input)
    action = decision.get("action", "reply")
    payload = decision.get("payload", {})
    spoken = decision.get("spoken_response", "")

    final_response = spoken
    details = {}

    # 2. Enrutamiento dinámico a subagentes
    if action == "add_quest":
        title = payload.get("title", user_input)
        xp = int(payload.get("xp", 25))
        desc = payload.get("description", "")
        rpg_msg = GamificationManager.add_quest(title=title, description=desc, xp_reward=xp)
        final_response = f"{spoken} {rpg_msg}".strip()
        details = {"quest_title": title, "xp": xp}

    elif action == "complete_quest":
        title = payload.get("title", user_input)
        rpg_msg = GamificationManager.complete_quest(title)
        final_response = rpg_msg
        details = {"quest_title": title}

    elif action == "list_quests":
        quests_msg = GamificationManager.list_pending_quests()
        final_response = quests_msg
        details = {"list": quests_msg}

    elif action == "send_whatsapp":
        # Reglas de seguridad de WhatsApp #2 y #3
        recipient = payload.get("recipient", "")
        message = payload.get("message", "")
        wa_result = whatsapp_bridge.prepare_send_request(recipient, message)
        
        if wa_result.get("needs_confirmation"):
            final_response = wa_result.get("confirmation_prompt")
        else:
            final_response = wa_result.get("message")
        details = wa_result

    elif action == "confirm_whatsapp":
        # Regla de seguridad #3: Confirmación autorizada por el usuario
        result_msg = whatsapp_bridge.execute_pending_send()
        final_response = result_msg
        details = {"status": "confirmed"}

    elif action == "cancel_whatsapp":
        whatsapp_bridge.pending_message = None
        final_response = "Entendido, cancelé el envío del mensaje."
        details = {"status": "cancelled"}

    print(f"[Abby Responde]: {final_response}")

    return CommandResponse(
        respuesta=final_response,
        accion_ejecutada=action,
        detalles=details
    )

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"Iniciando Abby Coordinator Server en http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
