-- Migration 018: Suporte a hábitos (tarefas recorrentes diárias)
-- =====================================================================
-- MOTIVAÇÃO:
-- Hoje, quando o usuário conclui uma tarefa com recorrencia='diaria',
-- o status da tarefa mãe vira 'concluida' — encerrando o hábito
-- permanentemente. O certo é: o hábito nunca termina; cada dia tem
-- um "feito hoje" independente.
--
-- ESTA MIGRATION:
--   1) Adiciona coluna `eh_habito` em tarefas (true para hábitos)
--   2) Cria tabela `tarefas_diarias_log` com (tarefa_id, data) UNIQUE
--   3) Marca tarefas existentes com recorrencia='diaria' como eh_habito
--   4) Habilita RLS + policies + índices
--
-- Depois desta migration, o frontend/bot:
--   - Ao concluir tarefa eh_habito=true → INSERT em tarefas_diarias_log
--   - NUNCA muda status da tarefa mãe para 'concluida'
--   - View "Hoje" mostra o hábito com ✅ baseado no log
--   - View "Todas" filtra hábitos (eh_habito != true)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Coluna eh_habito em tarefas
-- ---------------------------------------------------------------------
ALTER TABLE tarefas
  ADD COLUMN IF NOT EXISTS eh_habito BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_tarefas_eh_habito
  ON tarefas(user_id, eh_habito)
  WHERE eh_habito = TRUE;

-- ---------------------------------------------------------------------
-- 2) Tabela tarefas_diarias_log
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tarefas_diarias_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  data DATE NOT NULL DEFAULT CURRENT_DATE,
  concluida_em TIMESTAMPTZ DEFAULT now(),
  tempo_gasto_min INTEGER DEFAULT NULL,
  nota TEXT DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (tarefa_id, data)
);

CREATE INDEX IF NOT EXISTS idx_habitos_log_tarefa_data
  ON tarefas_diarias_log (tarefa_id, data DESC);

CREATE INDEX IF NOT EXISTS idx_habitos_log_user_data
  ON tarefas_diarias_log (user_id, data DESC);

-- ---------------------------------------------------------------------
-- 3) Backfill: marca tarefas com recorrencia='diaria' como hábito
-- ---------------------------------------------------------------------
UPDATE tarefas
SET eh_habito = TRUE
WHERE recorrencia = 'diaria'
  AND eh_habito IS DISTINCT FROM TRUE;

-- ---------------------------------------------------------------------
-- 4) RLS
-- ---------------------------------------------------------------------
ALTER TABLE tarefas_diarias_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "habitos_log_select" ON tarefas_diarias_log;
DROP POLICY IF EXISTS "habitos_log_insert" ON tarefas_diarias_log;
DROP POLICY IF EXISTS "habitos_log_update" ON tarefas_diarias_log;
DROP POLICY IF EXISTS "habitos_log_delete" ON tarefas_diarias_log;

CREATE POLICY "habitos_log_select" ON tarefas_diarias_log
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "habitos_log_insert" ON tarefas_diarias_log
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "habitos_log_update" ON tarefas_diarias_log
  FOR UPDATE USING (auth.uid() = user_id)
               WITH CHECK (auth.uid() = user_id);

CREATE POLICY "habitos_log_delete" ON tarefas_diarias_log
  FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------
-- 5) View helper: streak atual por hábito
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW habitos_streak AS
WITH ultimas AS (
  SELECT
    t.id AS tarefa_id,
    t.user_id,
    t.titulo,
    COUNT(l.id) FILTER (WHERE l.data >= CURRENT_DATE - INTERVAL '30 days') AS feitos_30d,
    COUNT(l.id) FILTER (WHERE l.data = CURRENT_DATE) AS feito_hoje,
    MAX(l.data) AS ultima_data
  FROM tarefas t
  LEFT JOIN tarefas_diarias_log l ON l.tarefa_id = t.id
  WHERE t.eh_habito = TRUE
  GROUP BY t.id, t.user_id, t.titulo
)
SELECT * FROM ultimas;

-- ---------------------------------------------------------------------
-- 6) Verificação
-- ---------------------------------------------------------------------
-- SELECT COUNT(*) FROM tarefas WHERE eh_habito = TRUE;
-- SELECT * FROM habitos_streak WHERE user_id = auth.uid();
