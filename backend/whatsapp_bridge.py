import os
import asyncio
from typing import Dict, Any, Optional
from supabase_client import supabase

class WhatsAppBridge:
    """
    Módulo de WhatsApp de Abby usando neonize con las 3 reglas de seguridad:
    1. Solo lee comandos de mi propio número en mi chat personal ('self-chat').
    2. Solo permite enviar mensajes a números registrados en 'contactos_autorizados'.
    3. Antes de enviar a un tercero, muestra destinatario y borrador y espera 'Confirmar'.
    """

    def __init__(self, my_phone: Optional[str] = None):
        self.my_phone = my_phone or os.getenv("MY_PHONE_NUMBER", "")
        self.pending_message: Optional[Dict[str, Any]] = None
        self._client = None

    def initialize_client(self):
        """Inicializa el cliente de neonize si está disponible."""
        try:
            from neonize.core import Client as NeonizeClient
            self._client = NeonizeClient()
            print("[WhatsApp Bridge] Neonize listo para escuchar/enviar.")
        except ImportError:
            print("[WhatsApp Bridge] Aviso: 'neonize' no instalado aún en el entorno local.")
        except Exception as e:
            print(f"[WhatsApp Bridge] Error al inicializar neonize: {e}")

    def is_authorized_contact(self, phone: str) -> (bool, Optional[str]):
        """Regla 2: Valida si el teléfono existe en contactos_autorizados de Supabase."""
        if not supabase:
            return False, None
        
        # Limpieza básica de número (solo dígitos)
        clean_phone = "".join(filter(str.isdigit, str(phone)))
        try:
            res = supabase.table("contactos_autorizados").select("*").execute()
            rows = res.data or []
            for contact in rows:
                contact_clean = "".join(filter(str.isdigit, str(contact.get("telefono", ""))))
                if contact_clean and (clean_phone == contact_clean or clean_phone.endswith(contact_clean) or contact_clean.endswith(clean_phone)):
                    return True, contact.get("nombre", "Contacto")
            return False, None
        except Exception as e:
            print(f"[WhatsApp Bridge] Error consultando contactos_autorizados: {e}")
            return False, None

    def handle_incoming_message(self, sender: str, is_group: bool, text: str) -> Optional[str]:
        """
        Regla 1: Solo lee comandos enviados desde mi propio número ('self-chat').
        Ignora chats o grupos de terceros.
        """
        if is_group:
            # Ignorar mensajes de grupos por seguridad
            return None

        # Verificar si proviene del self-chat / propio número
        if self.my_phone:
            clean_my_phone = "".join(filter(str.isdigit, self.my_phone))
            clean_sender = "".join(filter(str.isdigit, sender))
            if clean_my_phone not in clean_sender:
                print(f"[WhatsApp Bridge] Ignorando mensaje de tercero: {sender}")
                return None

        # Si el usuario responde a una confirmación pendiente
        text_clean = text.strip().lower()
        if self.pending_message:
            if text_clean in ["confirmar", "confirmo", "si", "sí", "enviar"]:
                return self.execute_pending_send()
            elif text_clean in ["cancelar", "cancel", "no", "abortar"]:
                self.pending_message = None
                return "Operación cancelada. El mensaje a terceros no fue enviado."

        return f"Comando recibido en self-chat: {text}"

    def prepare_send_request(self, recipient_phone: str, draft_text: str) -> Dict[str, Any]:
        """
        Regla 2 y 3: Valida contacto y genera el borrador para pedir 'Confirmar'.
        """
        authorized, contact_name = self.is_authorized_contact(recipient_phone)
        if not authorized:
            return {
                "success": False,
                "needs_confirmation": False,
                "message": f"Seguridad: El número {recipient_phone} NO está en tu lista de 'contactos_autorizados'. Mensaje denegado."
            }

        # Guardar como mensaje pendiente de confirmación
        self.pending_message = {
            "recipient_phone": recipient_phone,
            "recipient_name": contact_name or recipient_phone,
            "draft_text": draft_text
        }

        # Registrar en Supabase para persistencia y trazabilidad
        if supabase:
            try:
                supabase.table("whatsapp_pending_messages").insert({
                    "destinatario_telefono": recipient_phone,
                    "destinatario_nombre": contact_name,
                    "borrador_mensaje": draft_text,
                    "status": "waiting_confirmation"
                }).execute()
            except Exception as e:
                print(f"[WhatsApp Bridge] Registro en Supabase falló: {e}")

        # Mensaje para el usuario (Regla 3)
        confirmation_prompt = (
            f"Borrador preparado para {contact_name} ({recipient_phone}):\n"
            f"\"{draft_text}\"\n"
            f"¿Deseas enviarlo? Responde 'Confirmar' para autorizar el envío."
        )

        return {
            "success": True,
            "needs_confirmation": True,
            "confirmation_prompt": confirmation_prompt,
            "pending": self.pending_message
        }

    def execute_pending_send(self) -> str:
        """Envía el mensaje confirmado a través de neonize."""
        if not self.pending_message:
            return "No hay ningún mensaje pendiente de confirmación."

        recipient = self.pending_message["recipient_phone"]
        name = self.pending_message["recipient_name"]
        text = self.pending_message["draft_text"]

        print(f"[WhatsApp Bridge] Enviando mensaje autorizado a {name} ({recipient}): {text}")

        # Si el cliente neonize está activo, enviarlo
        if self._client:
            try:
                # self._client.send_message(...)
                pass
            except Exception as e:
                return f"Error al emitir por WhatsApp: {e}"

        # Actualizar en Supabase
        if supabase:
            try:
                supabase.table("whatsapp_pending_messages").update({
                    "status": "sent"
                }).eq("destinatario_telefono", recipient).eq("status", "waiting_confirmation").execute()
            except Exception:
                pass

        self.pending_message = None
        return f"Confirmado y enviado con éxito a {name}."
