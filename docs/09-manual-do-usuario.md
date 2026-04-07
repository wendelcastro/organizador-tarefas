# Manual do Usuário — Organizador Pessoal

Bem-vindo! Esta é uma ferramenta para você organizar suas **tarefas, finanças, metas e calendário** usando **Telegram + dashboard web + inteligência artificial**. Tudo em um só lugar.

> Você não precisa saber nada de programação. Siga este manual passo a passo.

---

## O que a ferramenta faz

Você conversa normalmente com um **bot no Telegram** — por texto ou voz — e ele entende e organiza tudo automaticamente:

- **Tarefas**: "Reunião com João amanhã às 15h" → vira tarefa no dia certo
- **Finanças**: "Gastei 50 no almoço" → vira despesa categorizada
- **Várias de uma vez**: "Gastei 50 no uber e 80 no supermercado" → duas despesas
- **Receitas futuras**: "Vou receber 5000 do cliente X dia 20" → fica como pendente
- **Planejamento**: "Reunião semana que vem" → entende e agenda

Tudo que você manda aparece também num **site bonito** (dashboard) onde dá pra ver gráficos, estatísticas, marcar tarefas concluídas, etc.

---

## Parte 1 — Primeiros passos

### 1.1 Criar sua conta no dashboard

1. Abra no navegador: **https://wendelcastro.github.io/organizador-tarefas/web/**
2. Clique em **"Criar conta"** (ou "Cadastrar")
3. Preencha:
   - **Email**: o seu email pessoal
   - **Senha**: crie uma senha forte (mínimo 6 caracteres)
4. Clique em **"Cadastrar"**
5. Se o sistema pedir confirmação por email, abra sua caixa de entrada e clique no link recebido

Pronto! Você já tem conta. Mas ainda não está conectado ao Telegram.

### 1.2 Acessar o bot no Telegram

1. Abra o Telegram no seu celular (ou desktop)
2. Na barra de busca, digite o nome do bot que o Wendel te passou (ex: `@organizadorwendel_bot`)
3. Toque no nome do bot
4. Toque em **"Iniciar"** (ou digite `/start`)

O bot vai te responder com uma mensagem de boas-vindas.

### 1.3 Vincular seu Telegram à sua conta

Esse passo conecta seu chat do Telegram à sua conta do dashboard — sem isso, o bot não sabe quem você é.

**No dashboard:**
1. Faça login com seu email e senha
2. No topo da tela (canto superior direito), procure um **ícone azul de avião de papel** (📤)
3. Clique nele
4. Vai aparecer um **código de 6 caracteres** (exemplo: `A3B9C1`)
5. Clique no botão **"Copiar comando"** — isso copia `/vincular A3B9C1`

**No Telegram:**
1. Volte para a conversa com o bot
2. Cole o comando que você copiou (ou digite `/vincular A3B9C1`)
3. Envie

O bot vai responder: **"🎉 Conta vinculada com sucesso!"**

> O código expira em 15 minutos. Se demorar, gere um novo.

---

## Parte 2 — Como usar o bot no Telegram

Agora que você está vinculado, pode mandar qualquer coisa pro bot.

### 2.1 Criar tarefas (texto livre)

Você não precisa usar comandos. Só digita como fala:

- "Reunião com o cliente amanhã às 14h"
- "Fazer exercício hoje às 6 da manhã"
- "Ligar pro médico segunda-feira"
- "Entregar o relatório sexta"

O bot entende e te pergunta se está correto antes de salvar. Você responde **"sim"** ou **"não"**.

### 2.2 Criar várias tarefas de uma vez

```
"Amanhã tenho: dentista 9h, almoço com Paulo 12h, academia 18h"
```

O bot cria as 3 tarefas de uma vez só.

### 2.3 Registrar gastos e receitas

Também só digita normal:

- "Gastei 50 no almoço"
- "Paguei 320 de celular"
- "Recebi 3000 de salário"
- "Comprei um tênis por 250"
- **Vários de uma vez**: "Gastei 20 no café e 80 no uber"

O bot identifica o valor, a categoria (alimentação, transporte, etc.) e pergunta se confirma.

### 2.4 Registrar receitas que ainda vão cair

- "Vou receber 5000 da consultoria do cliente X dia 20"
- "Falta receber 8000 do trabalho X"

Fica marcado como **pendente**. Quando cair de verdade, você marca como recebido (veja 2.7).

### 2.5 Ver seus dados (comandos úteis)

Digite estes comandos no bot:

| Comando | O que faz |
|---------|-----------|
| `/tarefas` | Lista suas tarefas pendentes |
| `/planejar` | IA monta seu dia inteligentemente |
| `/coaching` | Dica personalizada baseada nos seus padrões |
| `/feedback` | Análise do seu dia |
| `/saldo` | Saldo financeiro do mês |
| `/extrato` | Últimas transações |
| `/orcamento` | Ver/definir orçamentos mensais |
| `/financeiro` | Resumo financeiro com IA |

### 2.6 Marcar tarefas como concluídas

Duas formas:
- **Pelo bot**: `/concluir` → aparece lista com botões, clica na tarefa
- **Pelo dashboard**: marca direto na lista (ver Parte 3)

### 2.7 Marcar receita pendente como recebida

- **Pelo bot**: `/recebido` → aparece lista com botões, clica na que recebeu
- **Pelo dashboard**: na aba Finanças, clica no botão amarelo **"Recebido"** na receita pendente

### 2.8 Enviar áudio em vez de texto

Aperte o botão de microfone do Telegram e fale normalmente:

> *"Gastei 50 reais no almoço com minha mãe"*

O bot transcreve e registra automaticamente. Funciona em português.

### 2.9 Definir orçamentos mensais

```
/orcamento Alimentação 800
/orcamento Transporte 300
/orcamento Lazer 200
```

Quando você chegar perto do limite, recebe alerta.

---

## Parte 3 — Como usar o dashboard (site)

Acesse: **https://wendelcastro.github.io/organizador-tarefas/web/**

Faça login com seu email e senha.

### 3.1 O que tem em cada aba

| Aba | O que mostra |
|-----|--------------|
| **Todas** | Todas as tarefas — tu pode filtrar, ordenar, marcar como concluída |
| **Hoje** | Só as tarefas de hoje |
| **Semana** | Calendário visual da semana |
| **Blocos** | Tarefas organizadas por horário do dia |
| **KPIs** | Gráficos de produtividade |
| **Matriz** | Matriz de Eisenhower (urgente x importante) |
| **Revisão** | Revisão semanal com gamificação |
| **Finanças** | Saldo, gastos por categoria, orçamento, metas financeiras |

### 3.2 Criando tarefa no dashboard (sem bot)

Clique no botão **"+ Nova tarefa"** no canto superior direito, preencha e salve.

### 3.3 Dark mode / Light mode

Clique no ícone de sol/lua no topo para trocar o tema.

### 3.4 Instalar como app (PWA)

No Chrome (celular ou desktop):
1. Abra o dashboard
2. No menu do navegador, toque em **"Instalar app"** ou **"Adicionar à tela inicial"**
3. Fica um ícone como se fosse um app nativo

---

## Parte 4 — Conectar Google Calendar (opcional)

Se você quiser que suas tarefas virem eventos no Google Calendar automaticamente, e também ver seus eventos do Google no dashboard, siga:

### 4.1 Conectar
No Telegram, digite:
```
/conectar_google
```

O bot te manda um link. Abre o link e:
1. Faz login na sua conta Google
2. Autoriza o app a acessar seu calendário (marca todas as permissões pedidas)
3. Vai aparecer uma mensagem de sucesso

Pronto. A partir de agora:
- Tarefas criadas no bot viram eventos no Google Calendar automaticamente
- Eventos do Google aparecem no dashboard (aba Semana)
- A sincronização roda a cada 15 minutos

### 4.2 Desconectar
```
/desconectar google
```

### 4.3 Forçar sincronização agora
```
/sync
```

---

## Parte 5 — Conectar Outlook/Teams (opcional)

Mesmo fluxo do Google:
```
/conectar_microsoft
```
Segue o link, autoriza, pronto.

---

## Parte 6 — Dúvidas frequentes

### O bot não responde
- Espera 10 segundos e tenta de novo (o servidor pode estar acordando)
- Se persistir, avisa o Wendel

### Mandei uma tarefa mas apareceu como gasto (ou vice-versa)
- O bot usa IA. Em 99% dos casos acerta. Se errar, **cancela** a confirmação e tenta reescrever com mais clareza
- Ex: "**criar** tarefa: pagar internet" (fica mais claro que é tarefa, não gasto)

### Esqueci minha senha do dashboard
- No dashboard, clica em "Esqueci minha senha" — chega um email com link para redefinir

### Posso usar o mesmo bot em vários celulares?
- Sim. Fica vinculado à sua **conta do Telegram**, não ao aparelho. Basta abrir o Telegram em outro celular ou PC.

### Meus dados estão seguros?
- Sim. Só você tem acesso aos seus dados. A ferramenta usa Supabase com Row Level Security — outros usuários não conseguem ver nada seu, mesmo que tentem.

### Como trocar de conta no Telegram?
- Você pode gerar um novo código no dashboard (de outra conta) e mandar `/vincular NOVOCODIGO` no Telegram. Isso substitui a vinculação anterior.

### O bot está em inglês, como troco para português?
- O bot já responde em português. Se aparecer em inglês, é o Telegram que está em inglês — troca no Settings do Telegram.

### Preciso pagar alguma coisa?
- Por enquanto não. O Wendel mantém a infra dele.

---

## Parte 7 — Comandos rápidos (cola aqui)

**Tarefas:**
- Texto livre ("reunião amanhã 14h")
- `/tarefas` — ver pendentes
- `/planejar` — planejar o dia
- `/concluir` — marcar como feito
- `/editar` — editar uma tarefa
- `/excluir` — apagar
- `/decompor` — quebrar em subtarefas

**Finanças:**
- "Gastei X em Y" (texto livre)
- `/gasto 50 almoço`
- `/receita 8000 salário`
- `/saldo` — saldo do mês
- `/extrato` — últimas transações
- `/orcamento Alimentação 800` — definir limite
- `/financeiro` — resumo com IA
- `/recebido` — marcar receita como recebida

**Análises:**
- `/resumo` — visão geral
- `/coaching` — dica IA
- `/feedback` — análise do dia
- `/relatorio` — semanal

**Calendário:**
- `/conectar_google`
- `/conectar_microsoft`
- `/agenda` — ver agenda
- `/sync` — sincronizar agora

**Outros:**
- `/vincular CODIGO` — conectar sua conta
- `/cancelar` — cancelar operação atual
- `/foco` — modo foco (silencia lembretes)
- `/status` — ver status do bot

---

## Precisa de ajuda?

Chama o Wendel. 😉
