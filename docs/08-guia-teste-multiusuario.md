# Guia de Teste — Multi-usuário

Este guia serve para validar que tudo está funcionando depois das mudanças de multi-usuário. Segue a ordem, não pule etapas.

## Antes de começar

1. As migrations 015 e 016 precisam ter rodado no Supabase:
   - `015_multiusuario.sql` — cria tabelas `usuarios_bot` e `codigos_vinculacao`
   - `016_perfis_usuario.sql` — cria tabela `perfis_usuario` com roles
2. Bot do Koyeb precisa ter sido redeployed com o código mais novo
3. Dashboard no GitHub Pages precisa estar atualizado (automático quando fazemos push)

---

## Etapa 1 — Rodar as migrations no Supabase

### 1.1 Rodar 015 (se ainda não rodou)
Abre o Supabase → SQL Editor → New query → cola o conteúdo de `supabase/015_multiusuario.sql` → Run.

**Esperado:** Mensagem "Success. No rows returned."

### 1.2 Rodar 016
Mesmo processo com `supabase/016_perfis_usuario.sql`.

**Esperado:** Uma linha adicionada em `perfis_usuario` para cada usuário que já existe em `auth.users`.

### 1.3 Marcar você como owner
No SQL Editor:

```sql
-- Ver seu UUID
SELECT id, email FROM auth.users WHERE email = 'seu-email-aqui';

-- Copiar o UUID e colar abaixo
UPDATE perfis_usuario
SET role = 'owner'
WHERE user_id = 'cole-o-uuid-aqui';

-- Confirmar
SELECT user_id, role FROM perfis_usuario WHERE role = 'owner';
```

**Esperado:** Uma linha retornada com seu user_id e role='owner'.

---

## Etapa 2 — Verificar seus dados antigos

### 2.1 Conferir que nada sumiu
No SQL Editor:

```sql
-- Contar seus dados por tipo
SELECT 'tarefas' as tipo, COUNT(*) FROM tarefas WHERE user_id = 'seu-uuid'
UNION ALL
SELECT 'transacoes', COUNT(*) FROM transacoes WHERE user_id = 'seu-uuid'
UNION ALL
SELECT 'orcamento_mensal', COUNT(*) FROM orcamento_mensal WHERE user_id = 'seu-uuid'
UNION ALL
SELECT 'anexos', COUNT(*) FROM anexos WHERE user_id = 'seu-uuid';
```

**Esperado:** Os números que você esperava ver (tarefas históricas, transações, etc).

### 2.2 Se algum dado antigo não tem user_id
Dados criados antes da autenticação podem ter `user_id = NULL`. Para associá-los a você:

```sql
-- PRIMEIRO: ver quantos registros órfãos existem
SELECT 'tarefas' as tipo, COUNT(*) FROM tarefas WHERE user_id IS NULL
UNION ALL
SELECT 'transacoes', COUNT(*) FROM transacoes WHERE user_id IS NULL;

-- Se houver órfãos E VOCÊ TEM CERTEZA QUE SÃO SEUS, adote-os:
UPDATE tarefas SET user_id = 'seu-uuid' WHERE user_id IS NULL;
UPDATE transacoes SET user_id = 'seu-uuid' WHERE user_id IS NULL;
```

> **Atenção**: Só faça isso se você tem certeza. Se outra pessoa já vinculou antes e criou dados sem user_id por algum bug, você pode "roubar" os dados dela.

---

## Etapa 3 — Testar você (dono) no dashboard

### 3.1 Login
1. Abra https://wendelcastro.github.io/organizador-tarefas/web/
2. Faça login com seu email e senha
3. **Esperado**: Dashboard carrega normalmente, tarefas e finanças aparecem como antes

### 3.2 Ver view Metas
1. Clique em **Metas** no menu
2. **Esperado**: Vê o plano 2026 completo (Carreira, Finanças, Marca, Saúde)
3. Se aparecer "Em breve", significa que seu perfil não está como `owner`. Volta no Supabase e roda o UPDATE do passo 1.3

### 3.3 Gerar código de vinculação do Telegram
1. No topo da tela, clique no ícone **azul de avião de papel** (ao lado do logout)
2. **Esperado**: Modal aparece com código de 6 caracteres (ex: `A3B9C1`) e instruções
3. Copie o código

### 3.4 Vincular seu Telegram
1. Abre o bot no Telegram (aquele que você já usa)
2. Envia: `/vincular A3B9C1` (o código do passo 3.3)
3. **Esperado**: Mensagem "🎉 Conta vinculada com sucesso"

### 3.5 Testar comandos no Telegram
1. `/tarefas` → deve listar suas tarefas
2. `/saldo` → deve mostrar seu saldo financeiro
3. Mandar: "estudar python amanhã 14h" → bot cria tarefa
4. Mandar: "gastei 50 no almoço" → bot cria despesa

Se tudo isso funcionou, **você está OK e seus dados antigos estão intactos**.

---

## Etapa 4 — Testar um segundo usuário (esposa ou amigo)

### 4.1 Criar conta no dashboard
1. Pessoa acessa https://wendelcastro.github.io/organizador-tarefas/web/
2. Clica em "Criar conta" ou "Cadastrar"
3. Preenche email e senha
4. Confirma email (se Supabase exigir — ver Etapa 5)
5. Faz login

### 4.2 Verificar isolamento
1. Pessoa loga e vai na view **Todas** → deve estar vazia (0 tarefas)
2. View **Finanças** → vazio ou "Nenhuma transação"
3. View **Metas** → "Em breve" (não vê seu plano 2026) ✓

### 4.3 Gerar código e vincular Telegram
1. Clica no ícone de avião azul → copia o código
2. Abre o mesmo bot do Telegram (é o mesmo bot, diferente pessoa)
3. Manda `/start`
4. Manda `/vincular ABC123`
5. **Esperado**: "🎉 Conta vinculada"

### 4.4 Criar dados de teste
No Telegram:
1. Manda: "comprar pão amanhã"
2. Manda: "gastei 20 no café"
3. Volta pro dashboard (F5)
4. **Esperado**: Aparece 1 tarefa e 1 despesa — **SÓ DELAS, não suas**

### 4.5 Testar isolamento cruzado (importante!)
1. **Você** (no seu Telegram): manda `/saldo`
2. **Esperado**: Saldo **SEM** os R$20 de café da outra pessoa
3. **Você** (no dashboard): aba Finanças → **Esperado**: não vê os R$20

Se isolou corretamente, **multi-usuário está funcionando**.

---

## Etapa 5 — Configuração do Supabase Auth (se bloquear cadastro)

Se a pessoa tentar criar conta e receber erro "confirm email", significa que o Supabase está exigindo confirmação. Duas opções:

### Opção A (recomendada para amigos): desativar confirmação
1. Supabase → Authentication → Providers → Email
2. Desmarca "Confirm email"
3. Save

### Opção B (mais seguro): configurar SMTP
1. Supabase → Authentication → Email Templates
2. Configurar servidor SMTP (Mailgun, Resend, Gmail, etc.)
3. Mais trabalho mas mais profissional

---

## O que testar depois (checklist rápido)

Após as etapas acima, dá pra fazer um teste rápido de saúde:

- [ ] Você vê só seus dados
- [ ] Outro usuário vê só os dados dele
- [ ] Ambos conseguem criar tarefa via texto livre
- [ ] Ambos conseguem criar gasto via texto livre
- [ ] `/saldo` retorna valores diferentes para cada um
- [ ] Botão "Vincular Telegram" gera código novo
- [ ] `/coaching` gera resposta (pelo menos 100 chars)
- [ ] `/feedback` gera resposta
- [ ] View Metas: você vê; outros veem "Em breve"

---

## Problemas comuns e soluções

### "Você ainda não vinculou sua conta" no Telegram
→ Esqueceu de vincular. Gera código no dashboard e manda `/vincular CODIGO`

### Código "não encontrado ou já usado"
→ Código expira em 15 minutos. Gera um novo.

### Dashboard mostra view Metas vazia para você
→ Seu role ainda é `user`. Roda o UPDATE do passo 1.3 no Supabase.

### Bot não responde
→ Koyeb pode ter dormido. Acessa a URL do bot uma vez (`https://xxx.koyeb.app/`) para acordar, depois tenta no Telegram.

### "Erro ao gerar código" ao clicar no botão
→ Migration 015 não rodou. Verifica no Supabase se a tabela `codigos_vinculacao` existe.

### Dados antigos sumiram do dashboard
→ Eles podem ter `user_id = NULL`. Ver passo 2.2.
