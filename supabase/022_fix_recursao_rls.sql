-- Migration 022: Corrige recursão infinita nas policies RLS (erro 42P17)
-- =====================================================================
-- SINTOMA (produção, após aplicar a 021):
--   SELECT em perfis_usuario, admin_usuarios_resumo e codigos_convite
--   retorna 500 — "infinite recursion detected in policy for relation
--   perfis_usuario". Isso quebra o carregamento de perfil no dashboard
--   (detecção de owner, abas Metas/Admin) e o painel de convites.
--
-- CAUSA:
--   Uma policy de uma tabela NÃO pode consultar a própria tabela — o
--   Postgres detecta o ciclo (avaliar a policy dispara a própria policy)
--   e aborta com 42P17. Ficaram três casos assim:
--     1) perfis_owner_select_all (019) — EXISTS em perfis_usuario dentro
--        de policy de perfis_usuario
--     2) perfis_owner_delete (019) — idem
--     3) perfis_update_self (021) — subselects em perfis_usuario no
--        WITH CHECK da própria perfis_usuario
--   As policies convites_owner_* (019) também consultam perfis_usuario;
--   não são recursivas por si, mas disparam as policies acima ao avaliar
--   o EXISTS — por isso codigos_convite também dava 500.
--
-- SOLUÇÃO:
--   Fazer todas as checagens via funções SECURITY DEFINER (executam como
--   o dono da tabela e portanto NÃO disparam RLS): minha_role() (criada
--   na 021, recriada aqui com search_path fixo) e meu_status() (nova).
--
-- Esta migration é IDEMPOTENTE. O bot usa SERVICE_ROLE e não é afetado.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Funções auxiliares (SECURITY DEFINER = não disparam RLS)
-- ---------------------------------------------------------------------
-- search_path fixo: boa prática obrigatória em SECURITY DEFINER para
-- impedir que um schema malicioso no path troque a tabela consultada.
CREATE OR REPLACE FUNCTION minha_role()
RETURNS TEXT AS $$
  SELECT role FROM public.perfis_usuario WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION meu_status()
RETURNS TEXT AS $$
  SELECT status FROM public.perfis_usuario WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- ---------------------------------------------------------------------
-- 2) perfis_usuario — recriar as policies sem auto-referência
-- ---------------------------------------------------------------------
-- SELECT: cada um vê o próprio perfil; owner vê todos (painel admin).
DROP POLICY IF EXISTS "perfis_owner_select_all" ON perfis_usuario;
CREATE POLICY "perfis_owner_select_all" ON perfis_usuario
  FOR SELECT USING (auth.uid() = user_id OR minha_role() = 'owner');

-- DELETE: só owner, e nunca o próprio perfil.
DROP POLICY IF EXISTS "perfis_owner_delete" ON perfis_usuario;
CREATE POLICY "perfis_owner_delete" ON perfis_usuario
  FOR DELETE USING (minha_role() = 'owner' AND user_id != auth.uid());

-- UPDATE do próprio perfil sem poder mudar role/status (regra C1 da 021):
-- o WITH CHECK compara o valor NOVO da linha com o valor atual retornado
-- pelas funções — se tentar gravar role/status diferente, falha.
DROP POLICY IF EXISTS "perfis_update_self" ON perfis_usuario;
CREATE POLICY "perfis_update_self" ON perfis_usuario
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (
    auth.uid() = user_id
    AND role   = minha_role()
    AND status = meu_status()
  );

-- UPDATE administrativo (021, já usava minha_role) — recriada por clareza.
DROP POLICY IF EXISTS "perfis_update_owner" ON perfis_usuario;
CREATE POLICY "perfis_update_owner" ON perfis_usuario
  FOR UPDATE
  USING (minha_role() = 'owner')
  WITH CHECK (minha_role() = 'owner');

-- ---------------------------------------------------------------------
-- 3) codigos_convite — policies de owner via minha_role()
-- ---------------------------------------------------------------------
DROP POLICY IF EXISTS "convites_owner_select" ON codigos_convite;
CREATE POLICY "convites_owner_select" ON codigos_convite
  FOR SELECT USING (minha_role() = 'owner');

DROP POLICY IF EXISTS "convites_owner_insert" ON codigos_convite;
CREATE POLICY "convites_owner_insert" ON codigos_convite
  FOR INSERT WITH CHECK (minha_role() = 'owner');

DROP POLICY IF EXISTS "convites_owner_update" ON codigos_convite;
CREATE POLICY "convites_owner_update" ON codigos_convite
  FOR UPDATE USING (minha_role() = 'owner');

-- ---------------------------------------------------------------------
-- Verificação (rodar no SQL editor após aplicar):
-- ---------------------------------------------------------------------
-- 1. Não pode haver policy de perfis_usuario citando a própria tabela:
--    SELECT policyname, qual, with_check FROM pg_policies
--     WHERE tablename = 'perfis_usuario';
--
-- 2. Com a ANON KEY (via REST ou dashboard deslogado):
--    GET /rest/v1/perfis_usuario?select=user_id&limit=1  → 200 e []
--    GET /rest/v1/codigos_convite?select=codigo&limit=1  → 200 e []
--    GET /rest/v1/admin_usuarios_resumo?limit=1          → 200 e []
--
-- 3. Logado como owner no dashboard: aba Admin deve listar convites e
--    usuários; logado como usuário comum: vê apenas o próprio perfil.
