-- Migration 017: Correção crítica de RLS nas tabelas financeiras
-- =====================================================================
-- PROBLEMA: as policies originais da migration 012 tinham duas brechas:
--   1) "OR user_id IS NULL" em SELECT/UPDATE/DELETE — permitia a qualquer
--      usuário autenticado ver/alterar registros órfãos de outros usuários
--   2) INSERT com "WITH CHECK (true)" — permitia inserir linhas para
--      qualquer user_id (ou sem user_id), quebrando isolamento
--
-- ESTA MIGRATION:
--   a) Atribui todos os registros órfãos (user_id IS NULL) ao owner
--      (primeiro usuário com role='owner' na tabela perfis_usuario).
--   b) Torna user_id NOT NULL nas tabelas afetadas.
--   c) Recria as policies corretamente, filtrando estritamente por
--      auth.uid() = user_id em todas as operações.
--
-- Rodar após a migration 016 (perfis_usuario) e a 012 (financas).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Backfill: atribuir registros órfãos ao owner
-- ---------------------------------------------------------------------
DO $$
DECLARE
  v_owner UUID;
BEGIN
  SELECT user_id INTO v_owner
  FROM perfis_usuario
  WHERE role = 'owner'
  ORDER BY created_at
  LIMIT 1;

  IF v_owner IS NULL THEN
    RAISE NOTICE 'Nenhum owner encontrado em perfis_usuario. Pulando backfill.';
  ELSE
    UPDATE transacoes        SET user_id = v_owner WHERE user_id IS NULL;
    UPDATE orcamento_mensal  SET user_id = v_owner WHERE user_id IS NULL;
    UPDATE metas_financeiras SET user_id = v_owner WHERE user_id IS NULL;
    RAISE NOTICE 'Registros órfãos atribuídos ao owner %', v_owner;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- 2) Tornar user_id obrigatório (NOT NULL)
-- ---------------------------------------------------------------------
ALTER TABLE transacoes        ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE orcamento_mensal  ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE metas_financeiras ALTER COLUMN user_id SET NOT NULL;

-- ---------------------------------------------------------------------
-- 3) Remover policies antigas inseguras
-- ---------------------------------------------------------------------
DROP POLICY IF EXISTS "transacoes_select" ON transacoes;
DROP POLICY IF EXISTS "transacoes_insert" ON transacoes;
DROP POLICY IF EXISTS "transacoes_update" ON transacoes;
DROP POLICY IF EXISTS "transacoes_delete" ON transacoes;

DROP POLICY IF EXISTS "orcamento_select" ON orcamento_mensal;
DROP POLICY IF EXISTS "orcamento_insert" ON orcamento_mensal;
DROP POLICY IF EXISTS "orcamento_update" ON orcamento_mensal;
DROP POLICY IF EXISTS "orcamento_delete" ON orcamento_mensal;

DROP POLICY IF EXISTS "metas_fin_select" ON metas_financeiras;
DROP POLICY IF EXISTS "metas_fin_insert" ON metas_financeiras;
DROP POLICY IF EXISTS "metas_fin_update" ON metas_financeiras;
DROP POLICY IF EXISTS "metas_fin_delete" ON metas_financeiras;

-- ---------------------------------------------------------------------
-- 4) Recriar policies seguras (auth.uid() = user_id estrito)
-- ---------------------------------------------------------------------

-- TRANSACOES
CREATE POLICY "transacoes_select" ON transacoes
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "transacoes_insert" ON transacoes
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "transacoes_update" ON transacoes
  FOR UPDATE USING (auth.uid() = user_id)
               WITH CHECK (auth.uid() = user_id);

CREATE POLICY "transacoes_delete" ON transacoes
  FOR DELETE USING (auth.uid() = user_id);

-- ORCAMENTO_MENSAL
CREATE POLICY "orcamento_select" ON orcamento_mensal
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "orcamento_insert" ON orcamento_mensal
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "orcamento_update" ON orcamento_mensal
  FOR UPDATE USING (auth.uid() = user_id)
               WITH CHECK (auth.uid() = user_id);

CREATE POLICY "orcamento_delete" ON orcamento_mensal
  FOR DELETE USING (auth.uid() = user_id);

-- METAS_FINANCEIRAS
CREATE POLICY "metas_fin_select" ON metas_financeiras
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "metas_fin_insert" ON metas_financeiras
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "metas_fin_update" ON metas_financeiras
  FOR UPDATE USING (auth.uid() = user_id)
               WITH CHECK (auth.uid() = user_id);

CREATE POLICY "metas_fin_delete" ON metas_financeiras
  FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------
-- 5) Verificação final (mostra as policies ativas após a migration)
-- ---------------------------------------------------------------------
-- Rode manualmente para conferir:
-- SELECT schemaname, tablename, policyname, cmd, qual, with_check
-- FROM pg_policies
-- WHERE tablename IN ('transacoes','orcamento_mensal','metas_financeiras')
-- ORDER BY tablename, policyname;
