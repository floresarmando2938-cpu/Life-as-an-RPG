import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "es-MX-DaliaNeural")

async def generate_speech_audio(text: str, output_path: str = "temp_voice.mp3") -> Optional[str]:
    """
    Genera un archivo de audio MP3 usando edge-tts con la voz de Abby.
    Voz recomendada en español: es-MX-DaliaNeural (expresiva, amigable).
    """
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
        await communicate.save(output_path)
        return output_path
    except ImportError:
        print("[Edge TTS] Librería edge-tts aún no instalada. Omitiendo generación de MP3.")
        return None
    except Exception as e:
        print(f"[Edge TTS] Error generando voz: {e}")
        return None
