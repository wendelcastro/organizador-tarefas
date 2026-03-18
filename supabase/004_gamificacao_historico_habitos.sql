-- ============================================================
-- ORGANIZADOR DE TAREFAS — Migration 004
-- Gamificacao, historico semanal, habitos e subcategorias
-- ============================================================
-- COMO USAR:
-- 1. Acesse Supabase > SQL Editor
-- 2. Cole TODO este conteudo e clique "Run"
-- ============================================================

-- ==========================================
-- 1. TABELA: gamificacao
-- XP, nivel, streaks do usuario
-- ==========================================
CREATE TABLE IF NOT EXISTS gamificacao (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  xp_total INTEGER DEFAULT 0,
  nivel INTEGER DEFAULT 1,
  titulo TEXT DEFAULT 'Iniciante Organizado',
  streak_atual INTEGER DEFAULT 0,
  streak_recorde INTEGER DEFAULT 0,
  ultimo_dia_streak DATE DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE gamificacao ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total gamificacao" ON gamificacao FOR ALL USING (true) WITH CHECK (true);

-- Inserir registro inicial
INSERT INTO gamificacao (xp_total, nivel, titulo, streak_atual)
VALUES (0, 1, 'Iniciante Organizado', 0)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 2. TABELA: historico_semanal
-- Snapshot de cada semana para revisitar
-- ==========================================
CREATE TABLE IF NOT EXISTS historico_semanal (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  semana_inicio DATE NOT NULL,
  semana_fim DATE NOT NULL,
  total_tarefas INTEGER DEFAULT 0,
  concluidas INTEGER DEFAULT 0,
  atrasadas INTEGER DEFAULT 0,
  taxa_conclusao FLOAT DEFAULT 0,
  xp_ganho INTEGER DEFAULT 0,
  minutos_totais INTEGER DEFAULT 0,
  categorias JSONB DEFAULT '{}',
  anotacao TEXT DEFAULT NULL,
  destaque TEXT DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(semana_inicio)
);

ALTER TABLE historico_semanal ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total historico_semanal" ON historico_semanal FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_hist_semanal_inicio ON historico_semanal(semana_inicio);

-- ==========================================
-- 3. NOVOS CAMPOS na tabela tarefas
-- Subcategoria para habitos e tipo de atividade
-- ==========================================

-- Subcategoria: academia, leitura, corrida, beach_tennis, estudo_ingles, etc.
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS subcategoria TEXT DEFAULT NULL;

-- Tipo: 'tarefa' (padrao), 'habito', 'rotina'
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'tarefa'
  CHECK (tipo IN ('tarefa', 'habito', 'rotina'));

-- ==========================================
-- 4. TABELA: xp_log
-- Historico de XP ganho (para mostrar no dashboard)
-- ==========================================
CREATE TABLE IF NOT EXISTS xp_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tarefa_id UUID,
  xp_ganho INTEGER NOT NULL,
  motivo TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE xp_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total xp_log" ON xp_log FOR ALL USING (true) WITH CHECK (true);

-- ==========================================
-- 5. Trigger para updated_at nas novas tabelas
-- ==========================================
CREATE TRIGGER trigger_gamificacao_updated_at
  BEFORE UPDATE ON gamificacao
  FOR EACH ROW
  EXECUTE FUNCTION atualizar_updated_at();

CREATE TRIGGER trigger_hist_semanal_updated_at
  BEFORE UPDATE ON historico_semanal
  FOR EACH ROW
  EXECUTE FUNCTION atualizar_updated_at();

-- ==========================================
-- PRONTO! Migration 004 aplicada com sucesso.
-- Novas tabelas: gamificacao, historico_semanal, xp_log
-- Novos campos em tarefas: subcategoria, tipo
-- ==========================================
