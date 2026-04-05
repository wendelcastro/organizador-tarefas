-- Migration 013: Finanças V2 — PF/PJ, receitas planejadas, status de pagamento
-- Evolução do módulo financeiro para controle completo de vida financeira

-- ========== NOVOS CAMPOS EM TRANSAÇÕES ==========

-- Pessoa Física (CLT/Ser Educacional) vs Pessoa Jurídica (CNPJ pessoal/consultorias)
ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS pessoa TEXT DEFAULT 'pf'
  CHECK (pessoa IN ('pf', 'pj'));

-- Status: pago (já aconteceu), pendente (aguardando), planejado (futuro)
ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pago'
  CHECK (status IN ('pago', 'pendente', 'planejado'));

-- Quem vai pagar (para receitas pendentes) ou para quem pagou
ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS pagador TEXT DEFAULT NULL;

-- Data prevista de pagamento (para receitas/despesas futuras)
ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS data_prevista DATE DEFAULT NULL;

-- Índices para novos campos
CREATE INDEX IF NOT EXISTS idx_transacoes_pessoa ON transacoes(pessoa);
CREATE INDEX IF NOT EXISTS idx_transacoes_status ON transacoes(status);
CREATE INDEX IF NOT EXISTS idx_transacoes_data_prevista ON transacoes(data_prevista);

-- ========== NOVAS CATEGORIAS DE RECEITA ==========
INSERT INTO categorias_financeiras (nome, tipo, icone, cor, ordem) VALUES
  ('Salário PJ',     'receita', '🏢', '#8E44AD', 15),
  ('Reembolso',      'receita', '↩️', '#16A085', 16),
  ('Rendimento',     'receita', '📈', '#2980B9', 17)
ON CONFLICT (nome) DO NOTHING;

-- ========== VIEW: RECEITAS PENDENTES ==========
CREATE OR REPLACE VIEW receitas_pendentes AS
SELECT
  id, descricao, valor, categoria, pessoa, pagador,
  data_prevista, data, status, recorrente, recorrencia,
  user_id, created_at
FROM transacoes
WHERE tipo = 'receita'
  AND status IN ('pendente', 'planejado')
ORDER BY COALESCE(data_prevista, data) ASC;

-- ========== VIEW: BALANÇO SEMANAL ==========
CREATE OR REPLACE VIEW balanco_semanal AS
SELECT
  date_trunc('week', data) AS semana,
  tipo,
  pessoa,
  SUM(valor) AS total,
  COUNT(*) AS quantidade,
  user_id
FROM transacoes
WHERE status = 'pago'
GROUP BY date_trunc('week', data), tipo, pessoa, user_id
ORDER BY semana DESC;

-- ========== VIEW: BALANÇO PF vs PJ ==========
CREATE OR REPLACE VIEW balanco_pf_pj AS
SELECT
  date_trunc('month', data) AS mes,
  pessoa,
  tipo,
  SUM(valor) AS total,
  COUNT(*) AS quantidade,
  user_id
FROM transacoes
GROUP BY date_trunc('month', data), pessoa, tipo, user_id
ORDER BY mes DESC;
