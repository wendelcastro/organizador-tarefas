-- Migration 014: Limpar duplicatas de tarefas recorrentes
-- Remove cópias duplicadas criadas pelo antigo sistema _criar_copias_recorrencia_semanal

-- ========== ANÁLISE (rodar primeiro para ver o que será deletado) ==========
-- SELECT titulo, prazo, COUNT(*) as total
-- FROM tarefas
-- WHERE status != 'concluida'
-- GROUP BY titulo, prazo
-- HAVING COUNT(*) > 1
-- ORDER BY total DESC;

-- ========== LIMPEZA ==========
-- Mantém apenas a tarefa MAIS ANTIGA de cada grupo (título + prazo) que tem recorrencia='diaria'
-- Se não tem nenhuma com recorrencia, mantém a mais antiga

WITH duplicatas AS (
  SELECT
    id,
    titulo,
    prazo,
    recorrencia,
    created_at,
    ROW_NUMBER() OVER (
      PARTITION BY titulo, prazo
      ORDER BY
        CASE WHEN recorrencia = 'diaria' THEN 0 ELSE 1 END,
        created_at ASC
    ) AS rn
  FROM tarefas
  WHERE status != 'concluida'
    AND prazo IS NOT NULL
)
DELETE FROM tarefas
WHERE id IN (
  SELECT id FROM duplicatas WHERE rn > 1
);

-- ========== RESULTADO ==========
-- SELECT 'Após limpeza:' as info;
-- SELECT titulo, prazo, COUNT(*) as total
-- FROM tarefas
-- WHERE status != 'concluida'
-- GROUP BY titulo, prazo
-- HAVING COUNT(*) > 1
-- ORDER BY total DESC;
