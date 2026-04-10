# Guia: Sistema de Convites, Painel Admin e Pomodoro Completo

## 1. Sistema de Convites (Cadastro Controlado)

### Por que existe?
Antes, qualquer pessoa com o link do dashboard podia criar conta livremente. Agora, **só quem tem um código de convite** consegue se cadastrar. Você (owner) gera os códigos e envia para quem quiser convidar.

### Como funciona

#### Gerar código de convite (você, owner)
1. No dashboard, clique na aba **Admin** (aparece só para você)
2. Escolha a validade: 1, 3, 7 ou 30 dias
3. Clique em **Gerar convite**
4. Um código de 6 caracteres aparece (ex: `A3B9C1`)
5. Copie e envie por WhatsApp/email para a pessoa

#### Usar código de convite (pessoa convidada)
1. Acessa o dashboard: `https://wendelcastro.github.io/organizador-tarefas/web/`
2. Clica em **"Criar conta"**
3. Cola o **código de convite** no primeiro campo
4. Preenche email e senha
5. Clica **"Criar conta"**
6. Se o código for válido → conta criada! Confere o email e faz login
7. Se inválido/expirado → mensagem de erro clara

#### Regras dos códigos
- Cada código é de **uso único** — após usar, ninguém mais consegue
- Código tem **validade** (expira na data configurada)
- Você pode gerar quantos quiser no painel Admin
- Códigos usados e expirados ficam no histórico para referência

### Migration necessária
Rode `supabase/019_convites_admin.sql` no SQL Editor do Supabase.

---

## 2. Painel Administrativo

### Acesso
- Aba **"Admin"** na barra de navegação inferior
- **Visível apenas** para usuários com `role='owner'`

### O que você pode fazer

#### Seção "Gerar código de convite"
- Escolha validade (1, 3, 7 ou 30 dias)
- Clique "Gerar convite"
- Código aparece para copiar e enviar

#### Seção "Convites"
Tabela com todos os códigos gerados:
- **Código** (6 chars)
- **Criado em** (data)
- **Expira em** (data)
- **Status**: Ativo (azul), Usado (verde), Expirado (vermelho), Desativado (cinza)

#### Seção "Usuários"
Tabela com todos os cadastrados:
- **Nome/ID** do usuário
- **Role**: Owner ou Usuário
- **Status**: ativo / desativado
- **Tarefas**: quantas tarefas o usuário criou
- **Último acesso**: quando entrou por último
- **Ações**: Desativar / Ativar / Excluir

### Ações administrativas

| Ação | O que faz | Reversível? |
|------|-----------|-------------|
| **Desativar** | Muda status para "desativado". Usuário não consegue mais operar. | Sim (ativar de volta) |
| **Ativar** | Reativa um usuário desativado. | Sim |
| **Excluir** | Remove o perfil do usuário. Dados ficam órfãos. | Não — pede dupla confirmação |

---

## 3. Alteração de Senha

### Esqueci minha senha
1. Na tela de login, clique em **"Esqueci minha senha"**
2. Digite seu email
3. Clique **"Enviar link de recuperação"**
4. Abra seu email e clique no link recebido
5. O dashboard abre com a tela de **nova senha**
6. Digite e confirme a nova senha
7. Pronto!

### Alterar senha (logado)
1. No header do dashboard, clique no **ícone de cadeado** (dourado)
2. O formulário de nova senha aparece
3. Digite e confirme
4. Clique **"Alterar senha"**

---

## 4. Técnica Pomodoro — Como Funciona

### O que é a Técnica Pomodoro?
Criada por Francesco Cirillo nos anos 80, é um método de gerenciamento de tempo que alterna períodos de **foco intenso** com **pausas curtas**. Comprovadamente aumenta produtividade e reduz fadiga mental.

### O ciclo completo (implementado na ferramenta)

```
[Foco 25 min] → [Pausa 5 min] → [Foco 25 min] → [Pausa 5 min]
→ [Foco 25 min] → [Pausa 5 min] → [Foco 25 min] → [Pausa LONGA 15 min]
```

| Fase | Duração | O que fazer |
|------|---------|-------------|
| **Foco 1/4** | 25 min | Trabalhe na tarefa sem interrupções |
| **Pausa curta** | 5 min | Levante, alongue, beba água, olhe para longe |
| **Foco 2/4** | 25 min | Continue trabalhando |
| **Pausa curta** | 5 min | Mesma coisa |
| **Foco 3/4** | 25 min | Continue |
| **Pausa curta** | 5 min | Descanse |
| **Foco 4/4** | 25 min | Último bloco! |
| **Pausa longa** | 15 min | Descanse de verdade: café, caminhada, desconecte |

**Tempo total**: ~2h10min por ciclo completo.

### Como usar na ferramenta

1. **Abra uma tarefa** (clique nela para ver detalhes)
2. Na seção **🍅 Pomodoro**, clique **"Iniciar"**
3. O **widget flutuante** aparece no canto inferior direito:
   - **Badge da fase**: "Foco 1/4" (verde), "Pausa curta" (azul), "Pausa longa" (roxo)
   - **Timer**: contagem regressiva MM:SS
   - **Dots**: 4 bolinhas indicando ciclos (cinza = pendente, dourado = atual, verde = completo)
   - **Foco total**: minutos acumulados de trabalho nesta tarefa
4. **Transições automáticas**: quando o timer zera, toca um som e avança para a próxima fase
5. **Notificações**: aviso no navegador informando o que fazer na nova fase
6. **Controles**:
   - ⏸️ **Pausar/Retomar**: se precisar de uma interrupção urgente
   - ⏹️ **Parar**: encerra o ciclo e salva o tempo
   - ⏭️ **Pular**: avança para a próxima fase (ex: pular uma pausa)

### Regras importantes
- **Durante o foco**: evite celular, redes sociais, conversas. Se alguém interromper, pause e retome depois.
- **Durante a pausa**: saia do computador! A pausa é para o cérebro descansar.
- **Não pule pausas**: elas são tão importantes quanto o foco. Sem pausa, a produtividade cai.
- **Completou 4 Pomodoros**: você ganhou uma pausa longa. Use-a bem.
- **Tempo salvo**: o tempo de foco (não de pausa!) é salvo automaticamente na tarefa.

### Sons de transição
- **880 Hz** (agudo): fim de um bloco de foco
- **660 Hz** (médio): fim de uma pausa curta
- **440 Hz** (grave): fim da pausa longa / ciclo completo

---

## 5. Migrations Necessárias (em ordem)

| Arquivo | O que faz |
|---------|-----------|
| `supabase/019_convites_admin.sql` | Tabela de convites, campos admin em perfis_usuario |

Rode no **SQL Editor** do Supabase (https://supabase.com/dashboard → seu projeto → SQL Editor).

---

## 6. Resumo de Novos Botões na Interface

| Botão | Onde | O que faz |
|-------|------|-----------|
| 🔒 Cadeado dourado | Header (ao lado do logout) | Alterar senha |
| **Admin** | Barra de navegação inferior | Painel administrativo (só owner) |
| **Pular fase** (⏭️) | Widget Pomodoro | Avança para próxima fase |
