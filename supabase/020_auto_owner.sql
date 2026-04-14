-- Migration 020: Auto-promoção do primeiro usuário a owner
-- Se nenhum owner existe no sistema, o usuário que chamar esta função vira owner.
-- SECURITY DEFINER ignora RLS para contar owners em todas as linhas.

CREATE OR REPLACE FUNCTION promover_primeiro_owner()
RETURNS TEXT AS $$
DECLARE
  total_owners INT;
BEGIN
  -- Contar quantos owners existem (sem RLS, pois é SECURITY DEFINER)
  SELECT COUNT(*) INTO total_owners
  FROM perfis_usuario
  WHERE role = 'owner';

  IF total_owners > 0 THEN
    RETURN 'já existe owner';
  END IF;

  -- Nenhum owner: promover o usuário atual
  UPDATE perfis_usuario
  SET role = 'owner', updated_at = now()
  WHERE user_id = auth.uid();

  RETURN 'promovido a owner';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
