-- Migration 021: Correções de segurança RLS (auditoria Jul/2026)
-- =====================================================================
-- MOTIVAÇÃO:
-- O dashboard é público (GitHub Pages) e usa a ANON KEY, que fica exposta
-- no código-fonte por design. Logo, RLS é a ÚNICA barreira de segurança.
-- A auditoria encontrou políticas permissivas (USING(true), OR true,
-- WITH CHECK(true)) e views que ignoram RLS, permitindo:
--   C1 - qualquer usuário se auto-promover a 'owner'
--   C2 - qualquer um ler códigos de vinculação de terceiros (takeover)
--   C3 - qualquer um sequestrar o mapeamento chat_id -> user_id
--   H1 - views vazando e-mails e finanças de todos os usuários
--   M2 - convites enumeráveis por qualquer um
--   M4 - categorias_financeiras aberta para escrita
--
-- Esta migration é IDEMPOTENTE (DROP POLICY IF EXISTS antes de recriar).
-- O bot usa SERVICE_ROLE, que IGNORA RLS — portanto nenhuma destas
-- restrições afeta o funcionamento do bot.
-- =====================================================================

-- ---------------------------------------------------------------------
-- C1: perfis_usuario — impedir auto-promoção de role/status
-- ---------------------------------------------------------------------
-- Problema: a policy de UPDATE (016 + 019) não tinha WITH CHECK, então
-- qualquer usuário podia fazer UPDATE ... SET role='owner' no próprio perfil.
-- Solução: separar "editar meu perfil" (sem poder mudar role/status) de
-- "administrar perfis" (só owner, via função SECURITY DEFINER).

-- Função que retorna a role do usuário atual sem disparar recursão de RLS.
CREATE OR REPLACE FUNCTION minha_role()
RETURNS TEXT AS $$
  SELECT role FROM perfis_usuario WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Remove todas as policies de UPDATE anteriores desta tabela.
DROP POLICY IF EXISTS "perfis_update" ON perfis_usuario;
DROP POLICY IF EXISTS "perfis_owner_update_all" ON perfis_usuario;

-- (a) Usuário comum edita o PRÓPRIO perfil, mas NÃO pode alterar role/status.
--     O WITH CHECK garante que os valores de role e status permaneçam
--     iguais aos já gravados (comparação via subselect do próprio registro).
CREATE POLICY "perfis_update_self" ON perfis_usuario
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (
    auth.uid() = user_id
    AND role   = (SELECT p.role   FROM perfis_usuario p WHERE p.user_id = auth.uid())
    AND status = (SELECT p.status FROM perfis_usuario p WHERE p.user_id = auth.uid())
  );

-- (b) Owner administra qualquer perfil (inclusive role/status de outros).
CREATE POLICY "perfis_update_owner" ON perfis_usuario
  FOR UPDATE
  USING (minha_role() = 'owner')
  WITH CHECK (minha_role() = 'owner');

-- ---------------------------------------------------------------------
-- C1 (cont.): blindar a auto-promoção do primeiro owner
-- ---------------------------------------------------------------------
-- promover_primeiro_owner() (migration 020) continua válida — ela só
-- promove SE nenhum owner existir. Depois que você já é owner, ela
-- retorna 'já existe owner' e não faz nada. Mantida como está.

-- ---------------------------------------------------------------------
-- C2: codigos_vinculacao — remover o "OR true"
-- ---------------------------------------------------------------------
-- O bot lê via service_role (ignora RLS), então não precisa do OR true.
DROP POLICY IF EXISTS "codigos_select" ON codigos_vinculacao;
CREATE POLICY "codigos_select" ON codigos_vinculacao FOR SELECT
  USING (auth.uid() = user_id);

-- UPDATE dos códigos só deve vir do bot (service_role). Remover a policy
-- permissiva para anon/authenticated: sem policy de UPDATE, esses papéis
-- não conseguem atualizar (service_role continua podendo).
DROP POLICY IF EXISTS "codigos_update" ON codigos_vinculacao;

-- ---------------------------------------------------------------------
-- C3: usuarios_bot — escrita só pelo bot (service_role)
-- ---------------------------------------------------------------------
-- INSERT/UPDATE eram WITH CHECK(true)/USING(true) — qualquer um podia
-- repontar chat_id -> user_id. Remover essas policies deixa apenas o
-- service_role (que ignora RLS) escrevendo. SELECT do próprio permanece.
DROP POLICY IF EXISTS "usuarios_bot_insert" ON usuarios_bot;
DROP POLICY IF EXISTS "usuarios_bot_update" ON usuarios_bot;

-- ---------------------------------------------------------------------
-- H1: views que ignoram RLS — recriar com security_invoker
-- ---------------------------------------------------------------------
-- Views no Postgres rodam com os privilégios do dono e NÃO aplicam a RLS
-- das tabelas base, a menos que criadas com security_invoker = on
-- (Postgres 15+, suportado no Supabase). Assim, cada SELECT na view passa
-- a respeitar a RLS de perfis_usuario/transacoes do usuário que consulta.

-- admin_usuarios_resumo: expunha email + role + contagens de TODOS.
-- Com security_invoker, só owner (que tem policy perfis_owner_select_all)
-- enxerga linhas de outros; usuário comum vê só a própria.
DROP VIEW IF EXISTS admin_usuarios_resumo;
CREATE VIEW admin_usuarios_resumo
WITH (security_invoker = on) AS
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

-- resumo_financeiro_mensal: expunha agregados financeiros de todos.
DROP VIEW IF EXISTS resumo_financeiro_mensal;
CREATE VIEW resumo_financeiro_mensal
WITH (security_invoker = on) AS
SELECT
  date_trunc('month', data) AS mes,
  tipo,
  categoria,
  COUNT(*) AS quantidade,
  SUM(valor) AS total,
  user_id
FROM transacoes
GROUP BY date_trunc('month', data), tipo, categoria, user_id;

-- ---------------------------------------------------------------------
-- M4: categorias_financeiras — fechar escrita
-- ---------------------------------------------------------------------
-- SELECT compartilhado é intencional (categorias globais). INSERT aberto
-- (WITH CHECK true) permitia poluir a tabela — restringir a owner.
DROP POLICY IF EXISTS "categorias_fin_insert" ON categorias_financeiras;
CREATE POLICY "categorias_fin_insert" ON categorias_financeiras FOR INSERT
  WITH CHECK (minha_role() = 'owner');

-- ---------------------------------------------------------------------
-- M2: convites enumeráveis — validar por função, não por SELECT amplo
-- ---------------------------------------------------------------------
-- A policy "convites_validar" (019) permitia LISTAR todos os convites
-- válidos. Substituímos por uma função SECURITY DEFINER que só confirma
-- se UM código específico é válido, sem expor a lista.
DROP POLICY IF EXISTS "convites_validar" ON codigos_convite;

CREATE OR REPLACE FUNCTION validar_convite(p_codigo TEXT)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM codigos_convite
    WHERE codigo = p_codigo
      AND ativo = TRUE
      AND usado_por IS NULL
      AND expira_em > now()
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- A policy "convites_usar" (UPDATE) permanece: o usuário marca o próprio
-- código como usado (WITH CHECK usado_por = auth.uid()). Precisa localizar
-- a linha pelo código — mantemos uma policy de UPDATE que casa pelo código
-- válido, sem permitir SELECT amplo.
-- (convites_usar já existe na 019 e continua correta.)

-- ---------------------------------------------------------------------
-- Verificação (rodar manualmente no SQL editor do Supabase):
-- ---------------------------------------------------------------------
-- SELECT tablename, policyname, cmd, qual, with_check
--   FROM pg_policies
--  WHERE schemaname = 'public'
--    AND tablename IN ('perfis_usuario','codigos_vinculacao','usuarios_bot',
--                      'categorias_financeiras','codigos_convite')
--  ORDER BY tablename, cmd;
--
-- Teste com a ANON KEY (sessão de usuário comum) — todos devem FALHAR/vir vazios:
--   UPDATE perfis_usuario SET role='owner' WHERE user_id = auth.uid();  -- deve dar 0 rows
--   SELECT * FROM codigos_vinculacao;   -- só o próprio
--   SELECT * FROM admin_usuarios_resumo;-- só o próprio (a menos que owner)
--   SELECT validar_convite('CODIGO');   -- true/false, sem listar
