-- Migration 015: Multi-usuário (bot + dashboard)
-- Permite que o mesmo bot Telegram atenda múltiplos usuários do Supabase Auth.

-- ========== TABELA DE MAPEAMENTO TELEGRAM ↔ SUPABASE ==========
CREATE TABLE IF NOT EXISTS usuarios_bot (
  chat_id BIGINT PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  nome TEXT,
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_bot_user ON usuarios_bot(user_id);

-- ========== CÓDIGOS TEMPORÁRIOS DE VINCULAÇÃO ==========
CREATE TABLE IF NOT EXISTS codigos_vinculacao (
  codigo TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  expira_em TIMESTAMPTZ DEFAULT (now() + interval '15 minutes'),
  usado BOOLEAN DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_codigos_user ON codigos_vinculacao(user_id);
CREATE INDEX IF NOT EXISTS idx_codigos_expira ON codigos_vinculacao(expira_em);

-- ========== RLS ==========
ALTER TABLE usuarios_bot ENABLE ROW LEVEL SECURITY;
ALTER TABLE codigos_vinculacao ENABLE ROW LEVEL SECURITY;

-- Usuários só veem o próprio mapeamento
CREATE POLICY "usuarios_bot_select" ON usuarios_bot FOR SELECT
  USING (auth.uid() = user_id);

-- Service role (bot) pode inserir e atualizar
CREATE POLICY "usuarios_bot_insert" ON usuarios_bot FOR INSERT
  WITH CHECK (true);

CREATE POLICY "usuarios_bot_update" ON usuarios_bot FOR UPDATE
  USING (true);

-- Códigos de vinculação: usuário cria o próprio, bot lê todos
CREATE POLICY "codigos_insert" ON codigos_vinculacao FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "codigos_select" ON codigos_vinculacao FOR SELECT
  USING (auth.uid() = user_id OR true); -- bot (service_role) lê tudo

CREATE POLICY "codigos_update" ON codigos_vinculacao FOR UPDATE
  USING (true);

-- ========== FUNÇÃO: LIMPAR CÓDIGOS EXPIRADOS ==========
CREATE OR REPLACE FUNCTION limpar_codigos_expirados()
RETURNS void AS $$
BEGIN
  DELETE FROM codigos_vinculacao
  WHERE expira_em < now() OR usado = true;
END;
$$ LANGUAGE plpgsql;
