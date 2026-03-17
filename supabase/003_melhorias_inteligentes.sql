-- ============================================================
-- ORGANIZADOR DE TAREFAS — Migration 003
-- Melhorias de inteligencia: campos extras + tabela de contexto IA
-- ============================================================
-- COMO USAR:
-- 1. Acesse Supabase > SQL Editor
-- 2. Cole TODO este conteudo e clique "Run"
-- ============================================================

-- ==========================================
-- 1. NOVOS CAMPOS na tabela tarefas
-- ==========================================

-- Tempo estimado (em minutos) — usado para calculo de sobrecarga
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS tempo_estimado_min INTEGER DEFAULT NULL;

-- Recorrencia: null = tarefa unica, senao define o padrao
-- Valores: 'diaria', 'semanal', 'quinzenal', 'mensal'
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS recorrencia TEXT DEFAULT NULL;

-- Dia da recorrencia (0=segunda ... 6=domingo para semanal, 1-31 para mensal)
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS recorrencia_dia INTEGER DEFAULT NULL;

-- Delegacao: nome da pessoa responsavel
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS delegado_para TEXT DEFAULT NULL;

-- Referencia a tarefa "modelo" para recorrencias
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS tarefa_pai_id UUID DEFAULT NULL;

-- ==========================================
-- 2. TABELA: contexto_ia
-- Memoria de longo prazo da IA.
-- Guarda associacoes aprendidas (ex: "Carlos = Grupo Ser")
-- ==========================================
CREATE TABLE IF NOT EXISTS contexto_ia (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  chave TEXT NOT NULL UNIQUE,
  valor TEXT NOT NULL,
  tipo TEXT NOT NULL DEFAULT 'geral'
    CHECK (tipo IN ('pessoa', 'padrao', 'preferencia', 'geral')),
  confianca FLOAT DEFAULT 1.0,
  vezes_usado INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contexto_tipo ON contexto_ia(tipo);
CREATE INDEX IF NOT EXISTS idx_contexto_chave ON contexto_ia(chave);

-- RLS
ALTER TABLE contexto_ia ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total contexto_ia" ON contexto_ia FOR ALL USING (true) WITH CHECK (true);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION atualizar_contexto_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_contexto_updated_at ON contexto_ia;
CREATE TRIGGER trigger_contexto_updated_at
  BEFORE UPDATE ON contexto_ia
  FOR EACH ROW
  EXECUTE FUNCTION atualizar_contexto_updated_at();

-- ==========================================
-- 3. GARANTIR que migration 002 foi aplicada
-- (remove FK do historico se ainda existir)
-- ==========================================
ALTER TABLE historico DROP CONSTRAINT IF EXISTS historico_tarefa_id_fkey;

-- ==========================================
-- 4. VIEW: carga_por_dia
-- Mostra ocupacao de cada dia (para sugestao de realocacao)
-- ==========================================
CREATE OR REPLACE VIEW carga_por_dia AS
SELECT
  prazo AS dia,
  COUNT(*) AS total_tarefas,
  COALESCE(SUM(tempo_estimado_min), COUNT(*) * 30) AS minutos_estimados,
  COUNT(*) FILTER (WHERE horario IS NOT NULL) AS reunioes_fixas,
  COUNT(*) FILTER (WHERE prioridade = 'alta') AS alta_prioridade
FROM tarefas
WHERE status != 'concluida'
  AND prazo IS NOT NULL
  AND prazo >= CURRENT_DATE
GROUP BY prazo
ORDER BY prazo;

-- ==========================================
-- PRONTO! Migration 003 aplicada com sucesso.
-- ==========================================
