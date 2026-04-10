-- Migration 019: Sistema de Convites + Gestão de Usuários (Admin)
-- =====================================================================
-- MOTIVAÇÃO:
-- Qualquer pessoa com o link do dashboard pode criar conta livremente.
-- O dono (owner) precisa controlar quem acessa a ferramenta.
--
-- ESTA MIGRATION:
--   1) Cria tabela codigos_convite (código de uso único com validade)
--   2) Adiciona campo status em perfis_usuario ('ativo','pendente','desativado')
--   3) Adiciona campo nome_exibicao em perfis_usuario
--   4) Adiciona campo ultimo_acesso em perfis_usuario
--   5) RLS para que só owner gerencie convites e veja todos os perfis
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Tabela codigos_convite
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS codigos_convite (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  codigo VARCHAR(8) NOT NULL UNIQUE,
  criado_por UUID NOT NULL REFERENCES auth.users(id),
  usado_por UUID REFERENCES auth.users(id),
  usado_em TIMESTAMPTZ,
  expira_em TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
  ativo BOOLEAN DEFAULT TRUE,
  notas TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_convites_codigo ON codigos_convite(codigo);
CREATE INDEX IF NOT EXISTS idx_convites_criado_por ON codigos_convite(criado_por);

-- RLS: só owner pode criar/ver convites
ALTER TABLE codigos_convite ENABLE ROW LEVEL SECURITY;

-- Owner vê todos os convites que criou
CREATE POLICY "convites_owner_select" ON codigos_convite
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM perfis_usuario
      WHERE user_id = auth.uid() AND role = 'owner'
    )
  );

CREATE POLICY "convites_owner_insert" ON codigos_convite
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM perfis_usuario
      WHERE user_id = auth.uid() AND role = 'owner'
    )
  );

CREATE POLICY "convites_owner_update" ON codigos_convite
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM perfis_usuario
      WHERE user_id = auth.uid() AND role = 'owner'
    )
  );

-- Usuário comum pode ler convite pelo código (para validar no cadastro)
CREATE POLICY "convites_validar" ON codigos_convite
  FOR SELECT USING (
    ativo = TRUE AND usado_por IS NULL AND expira_em > now()
  );

CREATE POLICY "convites_usar" ON codigos_convite
  FOR UPDATE USING (
    ativo = TRUE AND usado_por IS NULL AND expira_em > now()
  ) WITH CHECK (
    usado_por = auth.uid()
  );

-- ---------------------------------------------------------------------
-- 2) Adicionar campos em perfis_usuario
-- ---------------------------------------------------------------------
ALTER TABLE perfis_usuario
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ativo'
    CHECK (status IN ('ativo', 'pendente', 'desativado'));

ALTER TABLE perfis_usuario
  ADD COLUMN IF NOT EXISTS nome_exibicao TEXT DEFAULT '';

ALTER TABLE perfis_usuario
  ADD COLUMN IF NOT EXISTS ultimo_acesso TIMESTAMPTZ;

ALTER TABLE perfis_usuario
  ADD COLUMN IF NOT EXISTS codigo_convite_usado VARCHAR(8);

-- Backfill: marcar usuários existentes como ativos
UPDATE perfis_usuario SET status = 'ativo' WHERE status IS NULL;

-- ---------------------------------------------------------------------
-- 3) Policy para owner ver TODOS os perfis (painel admin)
-- ---------------------------------------------------------------------
-- A policy existente (migration 016) permite cada usuário ver seu perfil.
-- Precisamos que o owner veja todos para gerenciar.
DROP POLICY IF EXISTS "perfis_owner_select_all" ON perfis_usuario;
CREATE POLICY "perfis_owner_select_all" ON perfis_usuario
  FOR SELECT USING (
    auth.uid() = user_id
    OR EXISTS (
      SELECT 1 FROM perfis_usuario p
      WHERE p.user_id = auth.uid() AND p.role = 'owner'
    )
  );

-- Owner pode atualizar perfis de outros (desativar, mudar role, etc)
DROP POLICY IF EXISTS "perfis_owner_update_all" ON perfis_usuario;
CREATE POLICY "perfis_owner_update_all" ON perfis_usuario
  FOR UPDATE USING (
    auth.uid() = user_id
    OR EXISTS (
      SELECT 1 FROM perfis_usuario p
      WHERE p.user_id = auth.uid() AND p.role = 'owner'
    )
  );

-- Owner pode deletar perfis
DROP POLICY IF EXISTS "perfis_owner_delete" ON perfis_usuario;
CREATE POLICY "perfis_owner_delete" ON perfis_usuario
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM perfis_usuario p
      WHERE p.user_id = auth.uid() AND p.role = 'owner'
    )
    AND user_id != auth.uid()  -- não pode deletar a si mesmo
  );

-- ---------------------------------------------------------------------
-- 4) Função para gerar código aleatório
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION gerar_codigo_convite()
RETURNS TEXT AS $$
DECLARE
  chars TEXT := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  result TEXT := '';
  i INTEGER;
BEGIN
  FOR i IN 1..6 LOOP
    result := result || substr(chars, floor(random() * length(chars) + 1)::int, 1);
  END LOOP;
  RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 5) Trigger: atualizar ultimo_acesso quando o perfil é carregado
--    (chamado via RPC ou manualmente pelo frontend)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION atualizar_ultimo_acesso()
RETURNS void AS $$
BEGIN
  UPDATE perfis_usuario
  SET ultimo_acesso = now()
  WHERE user_id = auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ---------------------------------------------------------------------
-- 6) View auxiliar: contagem de dados por usuário (para painel admin)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW admin_usuarios_resumo AS
SELECT
  p.user_id,
  p.role,
  p.status,
  p.nome_exibicao,
  p.ultimo_acesso,
  p.created_at,
  p.codigo_convite_usado,
  u.email,
  (SELECT COUNT(*) FROM tarefas t WHERE t.user_id = p.user_id) AS total_tarefas,
  (SELECT COUNT(*) FROM transacoes tr WHERE tr.user_id = p.user_id) AS total_transacoes
FROM perfis_usuario p
LEFT JOIN auth.users u ON u.id = p.user_id;

-- ---------------------------------------------------------------------
-- Verificação
-- ---------------------------------------------------------------------
-- SELECT * FROM admin_usuarios_resumo;
-- SELECT gerar_codigo_convite();
