-- Esquema SQL para "Life as an RPG" (Supabase / PostgreSQL)

-- 1. Tabla de Perfil de Usuario / Avatar RPG
CREATE TABLE IF NOT EXISTS user_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT DEFAULT 'Héroe',
    level INT DEFAULT 1,
    current_xp INT DEFAULT 0,
    next_level_xp INT DEFAULT 100,
    hp INT DEFAULT 100,
    max_hp INT DEFAULT 100,
    streak_days INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Misiones diarias / Quests
CREATE TABLE IF NOT EXISTS quests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    xp_reward INT DEFAULT 20,
    difficulty TEXT DEFAULT 'media', -- facil, media, dificil, epica
    category TEXT DEFAULT 'general', -- salud, estudio, trabajo, orden
    status TEXT DEFAULT 'pending',   -- pending, in_progress, completed, failed
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 3. Registro de Ganancia de XP y Actividad
CREATE TABLE IF NOT EXISTS xp_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quest_id UUID REFERENCES quests(id) ON DELETE SET NULL,
    xp_amount INT NOT NULL,
    reason TEXT NOT NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Recompensas Desbloqueables en el Mundo Real
CREATE TABLE IF NOT EXISTS rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    cost_xp INT NOT NULL,
    is_claimed BOOLEAN DEFAULT FALSE,
    claimed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Contactos Autorizados para WhatsApp (Regla de Seguridad #2)
CREATE TABLE IF NOT EXISTS contactos_autorizados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefono TEXT UNIQUE NOT NULL, -- ej: '5215512345678'
    nombre TEXT NOT NULL,
    relacion TEXT, -- amigo, familia, trabajo
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Cola de Mensajes de WhatsApp Pendientes de Confirmación (Regla de Seguridad #3)
CREATE TABLE IF NOT EXISTS whatsapp_pending_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destinatario_telefono TEXT NOT NULL,
    destinatario_nombre TEXT,
    borrador_mensaje TEXT NOT NULL,
    status TEXT DEFAULT 'waiting_confirmation', -- waiting_confirmation, confirmed, rejected, sent
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insertar un perfil inicial por defecto si no existe
INSERT INTO user_profile (username, level, current_xp, next_level_xp)
SELECT 'Héroe', 1, 0, 100
WHERE NOT EXISTS (SELECT 1 FROM user_profile);
