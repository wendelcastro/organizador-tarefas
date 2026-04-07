-- Migration 016: Perfis de usuário com roles
-- Remove a necessidade de hardcodar email/role no código do frontend

CREATE TABLE IF NOT EXISTS perfis_usuario (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nome TEXT,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('owner', 'admin', 'user')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ========== RLS ==========
ALTER TABLE perfis_usuario ENABLE ROW LEVEL SECURITY;

-- Cada usuário só lê o próprio perfil
CREATE POLICY "perfis_select" ON perfis_usuario FOR SELECT
  USING (auth.uid() = user_id);

-- Cada usuário pode criar o próprio perfil (1 vez, via trigger ou signup)
CREATE POLICY "perfis_insert" ON perfis_usuario FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Apenas owners/admins podem atualizar roles
CREATE POLICY "perfis_update" ON perfis_usuario FOR UPDATE
  USING (auth.uid() = user_id);

-- ========== TRIGGER: criar perfil automaticamente no signup ==========
CREATE OR REPLACE FUNCTION criar_perfil_usuario()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO perfis_usuario (user_id, role)
  VALUES (NEW.id, 'user')
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION criar_perfil_usuario();

-- ========== BACKFILL: criar perfis para usuários já existentes ==========
INSERT INTO perfis_usuario (user_id, role)
SELECT id, 'user' FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

-- ========== DEFINIR O OWNER ==========
-- IMPORTANTE: Depois de rodar este script, acesse o Supabase e marque
-- manualmente o seu user_id como 'owner'. Exemplo via SQL:
--
--   UPDATE perfis_usuario
--   SET role = 'owner'
--   WHERE user_id = 'seu-uuid-aqui';
--
-- Ou pegue o UUID assim:
--   SELECT id, email FROM auth.users WHERE email = 'seu@email.com';
