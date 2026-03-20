-- Migration 007: Quadrante Eisenhower manual
-- Permite que o usuario escolha/mova tarefas entre quadrantes da Matriz

-- Valores: 'q1' (Fazer Agora), 'q2' (Agendar), 'q3' (Delegar), 'q4' (Eliminar), NULL (auto)
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS quadrante_eisenhower TEXT DEFAULT NULL
  CHECK (quadrante_eisenhower IN ('q1', 'q2', 'q3', 'q4'));
