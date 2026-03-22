-- Migration 010: Anexos e busca contextual

-- Tabela de anexos (arquivos, transcricoes, notas longas vinculadas a tarefas/eventos)
CREATE TABLE IF NOT EXISTS anexos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tarefa_id UUID DEFAULT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  evento_id UUID DEFAULT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('texto', 'transcricao', 'link', 'arquivo')),
  titulo TEXT NOT NULL DEFAULT '',
  conteudo TEXT NOT NULL DEFAULT '',
  url TEXT DEFAULT '',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE anexos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total anexos" ON anexos FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_anexos_tarefa ON anexos(tarefa_id);
CREATE INDEX IF NOT EXISTS idx_anexos_evento ON anexos(evento_id);
CREATE INDEX IF NOT EXISTS idx_anexos_conteudo ON anexos USING gin(to_tsvector('portuguese', conteudo));
CREATE INDEX IF NOT EXISTS idx_tarefas_titulo_busca ON tarefas USING gin(to_tsvector('portuguese', titulo));
