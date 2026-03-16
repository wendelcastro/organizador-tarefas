-- ============================================================
-- FIX: Corrigir trigger que impede DELETE de tarefas
-- ============================================================
-- PROBLEMA: O trigger "registrar_historico" tenta inserir no
-- historico APOS deletar a tarefa, mas a FK (tarefa_id)
-- referencia tarefas(id) que ja foi deletado = ERRO.
-- O PostgreSQL faz rollback e a tarefa nunca e excluida.
--
-- SOLUCAO: Remover a FK do historico e usar tarefa_id como
-- referencia "soft" (sem constraint). Isso permite registrar
-- o historico mesmo apos a exclusao da tarefa.
-- ============================================================
-- COMO USAR:
-- 1. Acesse Supabase > SQL Editor
-- 2. Cole este conteudo e clique "Run"
-- ============================================================

-- 1. Remover a FK constraint do historico
ALTER TABLE historico DROP CONSTRAINT IF EXISTS historico_tarefa_id_fkey;

-- 2. Recriar o trigger para funcionar corretamente
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
    IF OLD.status != NEW.status THEN
      INSERT INTO historico (tarefa_id, acao, detalhes)
      VALUES (NEW.id, 'status_alterado', jsonb_build_object(
        'de', OLD.status,
        'para', NEW.status
      ));
    END IF;
    IF OLD.prioridade != NEW.prioridade THEN
      INSERT INTO historico (tarefa_id, acao, detalhes)
      VALUES (NEW.id, 'prioridade_alterada', jsonb_build_object(
        'de', OLD.prioridade,
        'para', NEW.prioridade
      ));
    END IF;
  ELSIF TG_OP = 'DELETE' THEN
    -- Sem FK, agora funciona: registra que a tarefa foi excluida
    INSERT INTO historico (tarefa_id, acao, detalhes)
    VALUES (OLD.id, 'excluida', jsonb_build_object('titulo', OLD.titulo));
  END IF;
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Pronto! Agora o DELETE funciona e o historico ainda registra tudo.
