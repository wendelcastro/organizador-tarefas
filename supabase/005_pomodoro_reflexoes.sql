-- Migration 005: Pomodoro tracking + Reflexoes diarias

-- Tempo gasto real por tarefa (Pomodoro tracking)
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS tempo_gasto_min INTEGER DEFAULT 0;

-- Reflexoes diarias
CREATE TABLE IF NOT EXISTS reflexoes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  data DATE NOT NULL DEFAULT CURRENT_DATE,
  pergunta TEXT NOT NULL,
  resposta TEXT DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(data)
);
ALTER TABLE reflexoes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total reflexoes" ON reflexoes FOR ALL USING (true) WITH CHECK (true);
