-- Migration 008: Subtarefas
-- Permite que tarefas tenham sub-itens com progresso

CREATE TABLE IF NOT EXISTS subtarefas (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tarefa_id UUID NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  titulo TEXT NOT NULL,
  concluida BOOLEAN DEFAULT false,
  ordem INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE subtarefas ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total subtarefas" ON subtarefas FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_subtarefas_tarefa ON subtarefas(tarefa_id);
