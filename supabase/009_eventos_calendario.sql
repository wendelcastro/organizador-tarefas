-- Migration 009: Eventos de Calendario (Google + Microsoft)
-- Sincroniza eventos do Google Calendar e Outlook/Teams

CREATE TABLE IF NOT EXISTS eventos_calendario (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  external_id TEXT NOT NULL,
  provider TEXT NOT NULL CHECK (provider IN ('google', 'microsoft')),
  titulo TEXT NOT NULL,
  descricao TEXT DEFAULT '',
  local_evento TEXT DEFAULT '',
  data_inicio TIMESTAMPTZ NOT NULL,
  data_fim TIMESTAMPTZ NOT NULL,
  dia DATE NOT NULL,
  horario_inicio TEXT DEFAULT '',
  horario_fim TEXT DEFAULT '',
  all_day BOOLEAN DEFAULT false,
  meeting_link TEXT DEFAULT '',
  meeting_platform TEXT DEFAULT NULL,
  recorrente BOOLEAN DEFAULT false,
  synced_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(external_id, provider)
);

ALTER TABLE eventos_calendario ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Acesso total eventos" ON eventos_calendario FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_eventos_dia ON eventos_calendario(dia);
CREATE INDEX IF NOT EXISTS idx_eventos_provider ON eventos_calendario(provider);
CREATE INDEX IF NOT EXISTS idx_eventos_data_inicio ON eventos_calendario(data_inicio);
