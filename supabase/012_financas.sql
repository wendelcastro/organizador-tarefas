-- Migration 012: Módulo Financeiro
-- Tabelas para controle de receitas, despesas, orçamento e metas financeiras

-- ========== CATEGORIAS FINANCEIRAS ==========
CREATE TABLE IF NOT EXISTS categorias_financeiras (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  tipo TEXT NOT NULL DEFAULT 'despesa' CHECK (tipo IN ('despesa', 'receita', 'ambos')),
  icone TEXT DEFAULT '💰',
  cor TEXT DEFAULT '#C4993D',
  ordem INTEGER DEFAULT 0,
  user_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed de categorias padrão
INSERT INTO categorias_financeiras (nome, tipo, icone, cor, ordem) VALUES
  ('Alimentação',   'despesa', '🍔', '#FF6B6B', 1),
  ('Transporte',    'despesa', '🚗', '#4ECDC4', 2),
  ('Moradia',       'despesa', '🏠', '#45B7D1', 3),
  ('Assinaturas',   'despesa', '📱', '#96CEB4', 4),
  ('Lazer',         'despesa', '🎮', '#DDA0DD', 5),
  ('Saúde',         'despesa', '💊', '#98D8C8', 6),
  ('Educação',      'despesa', '📚', '#F7DC6F', 7),
  ('Vestuário',     'despesa', '👕', '#BB8FCE', 8),
  ('Outros',        'despesa', '📦', '#AEB6BF', 9),
  ('Salário',       'receita', '💼', '#2ECC71', 10),
  ('Aulas Optativas','receita','🎓', '#F39C12', 11),
  ('Consultoria',   'receita', '💡', '#3498DB', 12),
  ('Freelance',     'receita', '🔧', '#1ABC9C', 13),
  ('Outros Receita','receita', '💵', '#27AE60', 14)
ON CONFLICT (nome) DO NOTHING;

-- ========== TRANSAÇÕES ==========
CREATE TABLE IF NOT EXISTS transacoes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
  valor NUMERIC(12,2) NOT NULL CHECK (valor > 0),
  descricao TEXT NOT NULL,
  categoria TEXT NOT NULL,
  data DATE NOT NULL DEFAULT CURRENT_DATE,
  recorrente BOOLEAN DEFAULT FALSE,
  recorrencia TEXT DEFAULT NULL CHECK (recorrencia IN ('mensal', 'semanal', 'anual', NULL)),
  dia_vencimento INTEGER DEFAULT NULL,
  notas TEXT DEFAULT '',
  origem TEXT DEFAULT 'telegram',
  user_id UUID,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes(data);
CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes(tipo);
CREATE INDEX IF NOT EXISTS idx_transacoes_categoria ON transacoes(categoria);
CREATE INDEX IF NOT EXISTS idx_transacoes_user ON transacoes(user_id);
CREATE INDEX IF NOT EXISTS idx_transacoes_mes ON transacoes(date_trunc('month', data));

-- ========== ORÇAMENTO MENSAL ==========
CREATE TABLE IF NOT EXISTS orcamento_mensal (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  categoria TEXT NOT NULL,
  limite NUMERIC(12,2) NOT NULL CHECK (limite > 0),
  mes DATE NOT NULL, -- primeiro dia do mês (ex: 2026-04-01)
  user_id UUID,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(categoria, mes)
);

-- ========== METAS FINANCEIRAS ==========
CREATE TABLE IF NOT EXISTS metas_financeiras (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  titulo TEXT NOT NULL,
  valor_alvo NUMERIC(12,2) NOT NULL CHECK (valor_alvo > 0),
  valor_atual NUMERIC(12,2) DEFAULT 0,
  prazo DATE DEFAULT NULL,
  status TEXT DEFAULT 'ativa' CHECK (status IN ('ativa', 'concluida', 'pausada')),
  icone TEXT DEFAULT '🎯',
  user_id UUID,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ========== VIEW: RESUMO MENSAL ==========
CREATE OR REPLACE VIEW resumo_financeiro_mensal AS
SELECT
  date_trunc('month', data) AS mes,
  tipo,
  categoria,
  COUNT(*) AS quantidade,
  SUM(valor) AS total,
  user_id
FROM transacoes
GROUP BY date_trunc('month', data), tipo, categoria, user_id;

-- ========== TRIGGER: UPDATED_AT ==========
CREATE OR REPLACE FUNCTION update_transacoes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_transacoes_updated_at ON transacoes;
CREATE TRIGGER trigger_transacoes_updated_at
  BEFORE UPDATE ON transacoes
  FOR EACH ROW EXECUTE FUNCTION update_transacoes_updated_at();

-- ========== RLS ==========
ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias_financeiras ENABLE ROW LEVEL SECURITY;
ALTER TABLE orcamento_mensal ENABLE ROW LEVEL SECURITY;
ALTER TABLE metas_financeiras ENABLE ROW LEVEL SECURITY;

-- Políticas: usuário vê apenas seus dados
CREATE POLICY "transacoes_select" ON transacoes FOR SELECT USING (
  auth.uid() = user_id OR user_id IS NULL
);
CREATE POLICY "transacoes_insert" ON transacoes FOR INSERT WITH CHECK (true);
CREATE POLICY "transacoes_update" ON transacoes FOR UPDATE USING (
  auth.uid() = user_id OR user_id IS NULL
);
CREATE POLICY "transacoes_delete" ON transacoes FOR DELETE USING (
  auth.uid() = user_id OR user_id IS NULL
);

CREATE POLICY "categorias_fin_select" ON categorias_financeiras FOR SELECT USING (true);
CREATE POLICY "categorias_fin_insert" ON categorias_financeiras FOR INSERT WITH CHECK (true);

CREATE POLICY "orcamento_select" ON orcamento_mensal FOR SELECT USING (
  auth.uid() = user_id OR user_id IS NULL
);
CREATE POLICY "orcamento_insert" ON orcamento_mensal FOR INSERT WITH CHECK (true);
CREATE POLICY "orcamento_update" ON orcamento_mensal FOR UPDATE USING (
  auth.uid() = user_id OR user_id IS NULL
);

CREATE POLICY "metas_fin_select" ON metas_financeiras FOR SELECT USING (
  auth.uid() = user_id OR user_id IS NULL
);
CREATE POLICY "metas_fin_insert" ON metas_financeiras FOR INSERT WITH CHECK (true);
CREATE POLICY "metas_fin_update" ON metas_financeiras FOR UPDATE USING (
  auth.uid() = user_id OR user_id IS NULL
);
