from typing import Dict, Any, Optional
from supabase_client import supabase

class GamificationManager:
    """
    Motor de Gamificación RPG de Abby:
    - Gestión de misiones diarias (Quests)
    - Sistema de Puntos de Experiencia (XP) y Subida de Nivel
    - Recompensas en el mundo real
    """

    @staticmethod
    def get_user_status() -> Dict[str, Any]:
        """Obtiene el estado actual del héroe."""
        if not supabase:
            return {"level": 1, "current_xp": 0, "next_level_xp": 100, "username": "Héroe"}
        try:
            res = supabase.table("user_profile").select("*").limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            # Si no existe, crear uno
            new_profile = {"username": "Héroe", "level": 1, "current_xp": 0, "next_level_xp": 100}
            created = supabase.table("user_profile").insert(new_profile).execute()
            return created.data[0] if created.data else new_profile
        except Exception as e:
            print(f"[Gamification] Error al consultar perfil: {e}")
            return {"level": 1, "current_xp": 0, "next_level_xp": 100, "username": "Héroe"}

    @staticmethod
    def add_quest(title: str, description: str = "", xp_reward: int = 25, difficulty: str = "media", category: str = "general") -> str:
        """Crea una nueva misión (quest) en el sistema."""
        if not supabase:
            return f"Misión '{title}' creada localmente (+{xp_reward} XP al completar)."
        try:
            supabase.table("quests").insert({
                "title": title,
                "description": description,
                "xp_reward": xp_reward,
                "difficulty": difficulty,
                "category": category,
                "status": "pending"
            }).execute()
            return f"¡Nueva misión añadida a tu bitácora!: '{title}' [+{xp_reward} XP]. ¡Tú puedes, aventurero!"
        except Exception as e:
            return f"Error al registrar misión en Supabase: {e}"

    @staticmethod
    def complete_quest(title_or_id: str) -> str:
        """Completa una misión, calcula XP y evalúa si sube de nivel."""
        if not supabase:
            return f"Misión completada. ¡Ganaste XP!"
        try:
            # Buscar la misión pendiente
            res = supabase.table("quests").select("*").ilike("title", f"%{title_or_id}%").eq("status", "pending").limit(1).execute()
            if not res.data:
                return f"No encontré ninguna misión pendiente que coincida con '{title_or_id}'."

            quest = res.data[0]
            quest_id = quest["id"]
            xp_reward = quest.get("xp_reward", 20)

            # Marcar completada
            supabase.table("quests").update({"status": "completed"}).eq("id", quest_id).execute()

            # Registrar en xp_log
            supabase.table("xp_log").insert({
                "quest_id": quest_id,
                "xp_amount": xp_reward,
                "reason": f"Completó la misión: {quest.get('title')}"
            }).execute()

            # Actualizar perfil de usuario y comprobar nivel
            profile = GamificationManager.get_user_status()
            current_xp = profile.get("current_xp", 0) + xp_reward
            level = profile.get("level", 1)
            next_level_xp = profile.get("next_level_xp", 100)

            level_up_msg = ""
            while current_xp >= next_level_xp:
                level += 1
                current_xp -= next_level_xp
                next_level_xp = int(next_level_xp * 1.5)
                level_up_msg = f" ¡SUBISTE DE NIVEL! Ahora eres Nivel {level}. ¡Felicidades! "

            supabase.table("user_profile").update({
                "level": level,
                "current_xp": current_xp,
                "next_level_xp": next_level_xp
            }).eq("id", profile.get("id")).execute()

            return f"¡Misión completada: '{quest.get('title')}'! Ganaste +{xp_reward} XP.{level_up_msg} Estado actual: Nivel {level} ({current_xp}/{next_level_xp} XP)."
        except Exception as e:
            return f"Error al completar misión: {e}"

    @staticmethod
    def list_pending_quests() -> str:
        """Lista las misiones pendientes."""
        if not supabase:
            return "No hay misiones cargadas."
        try:
            res = supabase.table("quests").select("*").eq("status", "pending").limit(5).execute()
            if not res.data:
                return "No tienes misiones pendientes por ahora. ¡Pídele una a Abby o descansa un poco!"
            
            output = "Tus misiones activas son:\n"
            for q in res.data:
                output += f"- {q.get('title')} (+{q.get('xp_reward')} XP)\n"
            return output.strip()
        except Exception as e:
            return f"Error al consultar misiones: {e}"
