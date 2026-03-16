-- ============================================================
-- ORGANIZADOR DE TAREFAS — Migration 001
-- Criacao das tabelas principais
-- ============================================================
-- COMO USAR:
-- 1. Acesse seu projeto no supabase.com
-- 2. Va em "SQL Editor" (icone de raio no menu lateral)
-- 3. Clique "New query"
-- 4. Cole TODO este conteudo e clique "Run"
-- ============================================================

-- ==========================================
-- TABELA: categorias
-- Analogia: As pastas do arquivo morto.
-- Cada tarefa pertence a uma categoria.
-- ==========================================
CREATE TABLE IF NOT EXISTS categorias (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  cor TEXT NOT NULL DEFAULT '#666666',
  icone TEXT DEFAULT NULL,
  ordem INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Inserir categorias padrao
INSERT INTO categorias (nome, cor, ordem) VALUES
  ('Trabalho',    '#f97316', 1),
  ('Consultoria', '#06b6d4', 2),
  ('Grupo Ser',   '#a855f7', 3),
  ('Pessoal',     '#22c55e', 4)
ON CONFLICT (nome) DO NOTHING;

-- ==========================================
-- TABELA: tarefas
-- Analogia: Cada ficha de tarefa no fichario.
-- E a tabela principal do sistema.
-- ==========================================
CREATE TABLE IF NOT EXISTS tarefas (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Conteudo
  titulo TEXT NOT NULL,
  notas TEXT DEFAULT '',

  -- Classificacao
  categoria TEXT NOT NULL DEFAULT 'Pessoal',
  prioridade TEXT NOT NULL DEFAULT 'media'
    CHECK (prioridade IN ('alta', 'media', 'baixa')),
  status TEXT NOT NULL DEFAULT 'pendente'
    CHECK (status IN ('pendente', 'em_andamento', 'concluida', 'cancelada')),

  -- Datas e horarios
  prazo DATE DEFAULT NULL,
  horario TIME DEFAULT NULL,

  -- Reuniao online
  meeting_link TEXT DEFAULT '',
  meeting_platform TEXT DEFAULT NULL
    CHECK (meeting_platform IN ('zoom', 'meet', 'teams', 'outro', NULL)),

  -- Integracao com Google Calendar
  google_event_id TEXT DEFAULT NULL,

  -- Origem: de onde veio a tarefa
  origem TEXT NOT NULL DEFAULT 'dashboard'
    CHECK (origem IN ('telegram', 'dashboard', 'claude_code', 'notion', 'google_calendar')),

  -- Metadados
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ DEFAULT NULL
);

-- ==========================================
-- TABELA: historico
-- Analogia: O diario de bordo.
-- Registra TUDO que aconteceu com cada tarefa.
-- Util para revisao semanal e analytics.
-- ==========================================
CREATE TABLE IF NOT EXISTS historico (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tarefa_id UUID REFERENCES tarefas(id) ON DELETE CASCADE,
  acao TEXT NOT NULL,
  detalhes JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ==========================================
-- TABELA: configuracoes
-- Analogia: As preferencias do usuario.
-- Guarda tokens, configs de integracao, etc.
-- ==========================================
CREATE TABLE IF NOT EXISTS configuracoes (
  chave TEXT PRIMARY KEY,
  valor TEXT NOT NULL,
  descricao TEXT DEFAULT '',
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Configs iniciais
INSERT INTO configuracoes (chave, valor, descricao) VALUES
  ('telegram_chat_id', '', 'Chat ID do Telegram para receber notificacoes'),
  ('google_calendar_id', 'primary', 'ID do calendario do Google para criar eventos'),
  ('revisao_semanal_dia', 'domingo', 'Dia da revisao semanal'),
  ('fuso_horario', 'America/Recife', 'Fuso horario do usuario')
ON CONFLICT (chave) DO NOTHING;

-- ==========================================
-- INDICES
-- Analogia: Abas no fichario para achar
-- as coisas mais rapido.
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_tarefas_status ON tarefas(status);
CREATE INDEX IF NOT EXISTS idx_tarefas_categoria ON tarefas(categoria);
CREATE INDEX IF NOT EXISTS idx_tarefas_prazo ON tarefas(prazo);
CREATE INDEX IF NOT EXISTS idx_tarefas_prioridade ON tarefas(prioridade);
CREATE INDEX IF NOT EXISTS idx_historico_tarefa ON historico(tarefa_id);
CREATE INDEX IF NOT EXISTS idx_historico_data ON historico(created_at);

-- ==========================================
-- FUNCAO: atualizar updated_at automaticamente
-- Analogia: Carimbo de "ultima modificacao"
-- que se atualiza sozinho.
-- ==========================================
CREATE OR REPLACE FUNCTION atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();

  -- Se status mudou para concluida, registra quando
  IF NEW.status = 'concluida' AND (OLD.status IS NULL OR OLD.status != 'concluida') THEN
    NEW.completed_at = now();
  END IF;

  -- Se voltou de concluida, limpa a data
  IF NEW.status != 'concluida' AND OLD.status = 'concluida' THEN
    NEW.completed_at = NULL;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger na tabela tarefas
DROP TRIGGER IF EXISTS trigger_updated_at ON tarefas;
CREATE TRIGGER trigger_updated_at
  BEFORE UPDATE ON tarefas
  FOR EACH ROW
  EXECUTE FUNCTION atualizar_updated_at();

-- ==========================================
-- FUNCAO: registrar historico automaticamente
-- Analogia: Toda vez que alguem mexe numa ficha,
-- o diario de bordo registra automaticamente.
-- ==========================================
CREATE OR REPLACE FUNCTION registrar_historico()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO historico (tarefa_id, acao, detalhes)
    VALUES (NEW.id, 'criada', jsonb_build_object(
      'titulo', NEW.titulo,
      'categoria', NEW.categoria,
      'prioridade', NEW.prioridade,
      'origem', NEW.origem
    ));
  ELSIF TG_OP = 'UPDATE' THEN
    -- Registra mudanca de status
    IF OLD.status != NEW.status THEN
      INSERT INTO historico (tarefa_id, acao, detalhes)
      VALUES (NEW.id, 'status_alterado', jsonb_build_object(
        'de', OLD.status,
        'para', NEW.status
      ));
    END IF;
    -- Registra mudanca de prioridade
    IF OLD.prioridade != NEW.prioridade THEN
      INSERT INTO historico (tarefa_id, acao, detalhes)
      VALUES (NEW.id, 'prioridade_alterada', jsonb_build_object(
        'de', OLD.prioridade,
        'para', NEW.prioridade
      ));
    END IF;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO historico (tarefa_id, acao, detalhes)
    VALUES (OLD.id, 'excluida', jsonb_build_object('titulo', OLD.titulo));
  END IF;
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger
DROP TRIGGER IF EXISTS trigger_historico ON tarefas;
CREATE TRIGGER trigger_historico
  AFTER INSERT OR UPDATE OR DELETE ON tarefas
  FOR EACH ROW
  EXECUTE FUNCTION registrar_historico();

-- ==========================================
-- RLS (Row Level Security)
-- Analogia: O cadeado do fichario.
-- Por enquanto, como e uso pessoal,
-- vamos permitir tudo via anon key.
-- Quando adicionar auth, restringimos por usuario.
-- ==========================================
ALTER TABLE tarefas ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuracoes ENABLE ROW LEVEL SECURITY;

-- Policies: permitir tudo para anon (uso pessoal)
-- IMPORTANTE: Em producao com multiplos usuarios, trocar por auth.uid()
CREATE POLICY "Acesso total tarefas" ON tarefas FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Acesso total categorias" ON categorias FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Acesso total historico" ON historico FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Acesso total configuracoes" ON configuracoes FOR ALL USING (true) WITH CHECK (true);

-- ==========================================
-- VIEW: resumo_semanal
-- Analogia: O relatorio que o coordenador
-- imprime toda segunda-feira.
-- ==========================================
CREATE OR REPLACE VIEW resumo_semanal AS
SELECT
  COUNT(*) FILTER (WHERE status != 'concluida') AS pendentes,
  COUNT(*) FILTER (WHERE status = 'concluida' AND completed_at >= date_trunc('week', now())) AS concluidas_semana,
  COUNT(*) FILTER (WHERE status != 'concluida' AND prazo < CURRENT_DATE) AS atrasadas,
  COUNT(*) FILTER (WHERE meeting_link != '' AND meeting_link IS NOT NULL AND status != 'concluida') AS reunioes_pendentes,
  COUNT(*) FILTER (WHERE prioridade = 'alta' AND status != 'concluida') AS alta_prioridade,
  COUNT(*) AS total
FROM tarefas;

-- ============================================================
-- PRONTO! Suas tabelas foram criadas com sucesso.
-- Agora volte ao Claude Code e me diga "pronto" :)
-- ============================================================
