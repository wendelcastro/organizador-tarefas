-- Migration 023: Corrige acesso à view admin_usuarios_resumo (erro 401)
-- =====================================================================
-- SINTOMA (produção, após aplicar a 021/022):
--   GET /rest/v1/admin_usuarios_resumo retorna 401 (permission denied)
--   para qualquer papel de cliente — inclusive o owner logado. O painel
--   Admin não consegue listar os usuários.
--
-- CAUSA:
--   A 021 recriou a view com security_invoker = on para respeitar RLS.
--   Só que a view faz JOIN em auth.users, e no Supabase os papéis anon
--   e authenticated NÃO têm SELECT no schema auth. Com security_invoker,
--   a consulta a auth.users roda com as permissões de quem chama → 42501.
--
-- SOLUÇÃO:
--   Voltar a view para o modo padrão (roda com privilégios do dono, que
--   lê auth.users normalmente), mas com o controle de acesso DENTRO da
--   própria view via WHERE:
--     - usuário comum → só a própria linha (só o próprio e-mail)
--     - owner (via minha_role(), SECURITY DEFINER da 022) → todas
--     - anon → nenhuma linha (auth.uid() é NULL e minha_role() é NULL)
--   Mesma proteção contra vazamento de e-mails/contagens que a 021
--   pretendia, sem depender de permissão no schema auth.
--
-- Esta migration é IDEMPOTENTE. Requer a 022 (função minha_role()).
-- =====================================================================

DROP VIEW IF EXISTS admin_usuarios_resumo;
CREATE VIEW admin_usuarios_resumo AS
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
LEFT JOIN auth.users u ON u.id = p.user_id
WHERE p.user_id = auth.uid()      -- usuário comum: só a própria linha
   OR minha_role() = 'owner';     -- owner: todas (painel admin)

-- ---------------------------------------------------------------------
-- Verificação (rodar após aplicar):
-- ---------------------------------------------------------------------
-- 1. Com a ANON KEY (deslogado):
--    GET /rest/v1/admin_usuarios_resumo?limit=1 → 200 e []
--
-- 2. Logado como owner no dashboard: aba Admin deve listar TODOS os
--    usuários com e-mail, status e contagens.
--
-- 3. Logado como usuário comum (se houver): a view retorna apenas a
--    própria linha.
