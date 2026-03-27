-- ============================================================
-- ORGANIZADOR DE TAREFAS — Migration 011
-- Autenticação e Row Level Security por usuário
-- ============================================================
-- COMO USAR:
-- 1. PRIMEIRO: Crie sua conta no Supabase Dashboard > Authentication > Users > Add User
-- 2. Copie o UUID do seu usuário
-- 3. Substitua 'SEU_USER_UUID_AQUI' pelo UUID copiado
-- 4. Cole TODO este conteúdo no SQL Editor e clique "Run"
-- ============================================================

-- ==========================================
-- 1. ADICIONAR user_id EM TODAS AS TABELAS
-- ==========================================

ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE historico ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE contexto_ia ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE gamificacao ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE historico_semanal ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE xp_log ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE reflexoes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE energia_diaria ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE subtarefas ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE eventos_calendario ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE anexos ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_tarefas_user ON tarefas(user_id);
CREATE INDEX IF NOT EXISTS idx_historico_user ON historico(user_id);
CREATE INDEX IF NOT EXISTS idx_configuracoes_user ON configuracoes(user_id);
CREATE INDEX IF NOT EXISTS idx_contexto_ia_user ON contexto_ia(user_id);
CREATE INDEX IF NOT EXISTS idx_gamificacao_user ON gamificacao(user_id);
CREATE INDEX IF NOT EXISTS idx_historico_semanal_user ON historico_semanal(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_log_user ON xp_log(user_id);
CREATE INDEX IF NOT EXISTS idx_reflexoes_user ON reflexoes(user_id);
CREATE INDEX IF NOT EXISTS idx_energia_user ON energia_diaria(user_id);
CREATE INDEX IF NOT EXISTS idx_subtarefas_user ON subtarefas(user_id);
CREATE INDEX IF NOT EXISTS idx_eventos_user ON eventos_calendario(user_id);
CREATE INDEX IF NOT EXISTS idx_anexos_user ON anexos(user_id);

-- ==========================================
-- 2. VINCULAR DADOS EXISTENTES AO SEU USUÁRIO
-- ==========================================
-- ⚠️ IMPORTANTE: Substitua 'SEU_USER_UUID_AQUI' pelo UUID do seu usuário!
-- Encontre no Supabase Dashboard > Authentication > Users

-- UPDATE tarefas SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE historico SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE configuracoes SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE contexto_ia SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE gamificacao SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE historico_semanal SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE xp_log SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE reflexoes SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE energia_diaria SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE subtarefas SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE eventos_calendario SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;
-- UPDATE anexos SET user_id = 'SEU_USER_UUID_AQUI' WHERE user_id IS NULL;

-- ==========================================
-- 3. TRIGGER: AUTO-PREENCHER user_id
-- ==========================================
-- Novos registros recebem automaticamente o user_id do usuário logado

CREATE OR REPLACE FUNCTION set_user_id()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.user_id IS NULL THEN
    NEW.user_id = auth.uid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Aplicar em cada tabela
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN VALUES
    ('tarefas'), ('historico'), ('configuracoes'), ('contexto_ia'),
    ('gamificacao'), ('historico_semanal'), ('xp_log'), ('reflexoes'),
    ('energia_diaria'), ('subtarefas'), ('eventos_calendario'), ('anexos')
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS set_user_id_%I ON %I', tbl, tbl);
    EXECUTE format('CREATE TRIGGER set_user_id_%I BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION set_user_id()', tbl, tbl);
  END LOOP;
END $$;

-- ==========================================
-- 4. SUBSTITUIR RLS POLICIES
-- ==========================================
-- Remove policies antigas (acesso total) e cria novas (por usuário)
-- USING permite ver dados do próprio user OU dados órfãos (user_id IS NULL)
-- WITH CHECK garante que só pode escrever com seu próprio user_id
-- Dados órfãos serão reclamados automaticamente pelo primeiro login (claimOrphanData)

-- === tarefas ===
DROP POLICY IF EXISTS "Acesso total tarefas" ON tarefas;
DROP POLICY IF EXISTS "Tarefas do usuario" ON tarefas;
CREATE POLICY "Tarefas do usuario" ON tarefas
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === historico ===
DROP POLICY IF EXISTS "Acesso total historico" ON historico;
DROP POLICY IF EXISTS "Historico do usuario" ON historico;
CREATE POLICY "Historico do usuario" ON historico
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === configuracoes ===
DROP POLICY IF EXISTS "Acesso total configuracoes" ON configuracoes;
DROP POLICY IF EXISTS "Configuracoes do usuario" ON configuracoes;
CREATE POLICY "Configuracoes do usuario" ON configuracoes
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === contexto_ia ===
DROP POLICY IF EXISTS "Acesso total contexto_ia" ON contexto_ia;
DROP POLICY IF EXISTS "Contexto do usuario" ON contexto_ia;
CREATE POLICY "Contexto do usuario" ON contexto_ia
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === gamificacao ===
DROP POLICY IF EXISTS "Acesso total gamificacao" ON gamificacao;
DROP POLICY IF EXISTS "Gamificacao do usuario" ON gamificacao;
CREATE POLICY "Gamificacao do usuario" ON gamificacao
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === historico_semanal ===
DROP POLICY IF EXISTS "Acesso total historico_semanal" ON historico_semanal;
DROP POLICY IF EXISTS "Historico semanal do usuario" ON historico_semanal;
CREATE POLICY "Historico semanal do usuario" ON historico_semanal
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === xp_log ===
DROP POLICY IF EXISTS "Acesso total xp_log" ON xp_log;
DROP POLICY IF EXISTS "XP do usuario" ON xp_log;
CREATE POLICY "XP do usuario" ON xp_log
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === reflexoes ===
DROP POLICY IF EXISTS "Acesso total reflexoes" ON reflexoes;
DROP POLICY IF EXISTS "Reflexoes do usuario" ON reflexoes;
CREATE POLICY "Reflexoes do usuario" ON reflexoes
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === energia_diaria ===
DROP POLICY IF EXISTS "Acesso total energia" ON energia_diaria;
DROP POLICY IF EXISTS "Energia do usuario" ON energia_diaria;
CREATE POLICY "Energia do usuario" ON energia_diaria
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === subtarefas ===
DROP POLICY IF EXISTS "Acesso total subtarefas" ON subtarefas;
DROP POLICY IF EXISTS "Subtarefas do usuario" ON subtarefas;
CREATE POLICY "Subtarefas do usuario" ON subtarefas
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === eventos_calendario ===
DROP POLICY IF EXISTS "Acesso total eventos_calendario" ON eventos_calendario;
DROP POLICY IF EXISTS "Eventos do usuario" ON eventos_calendario;
CREATE POLICY "Eventos do usuario" ON eventos_calendario
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === anexos ===
DROP POLICY IF EXISTS "Acesso total anexos" ON anexos;
DROP POLICY IF EXISTS "Anexos do usuario" ON anexos;
CREATE POLICY "Anexos do usuario" ON anexos
  FOR ALL USING (user_id = auth.uid() OR user_id IS NULL) WITH CHECK (user_id = auth.uid());

-- === categorias (compartilhada — leitura para autenticados) ===
DROP POLICY IF EXISTS "Acesso total categorias" ON categorias;
CREATE POLICY "Leitura categorias" ON categorias
  FOR SELECT USING (auth.role() = 'authenticated');

-- ==========================================
-- 5. UNIQUE CONSTRAINT: energia com user_id
-- ==========================================
-- A constraint original era (data, periodo). Agora precisa incluir user_id.

ALTER TABLE energia_diaria DROP CONSTRAINT IF EXISTS energia_diaria_data_periodo_key;
ALTER TABLE energia_diaria ADD CONSTRAINT energia_diaria_user_data_periodo_key
  UNIQUE (user_id, data, periodo);
