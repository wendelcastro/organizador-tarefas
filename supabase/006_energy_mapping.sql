-- Migration 006: Energy Mapping
-- Mapeamento de energia por periodo do dia

CREATE TABLE IF NOT EXISTS energia_diaria (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  data DATE NOT NULL DEFAULT CURRENT_DATE,
  periodo TEXT NOT NULL CHECK (periodo IN ('manha', 'tarde', 'noite')),
  nivel INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 5),
  notas TEXT DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(data, periodo)
);

ALTER TABLE energia_diaria ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total energia" ON energia_diaria FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_energia_data ON energia_diaria(data);
