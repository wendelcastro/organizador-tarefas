# Manual do Usuario — Organizador de Tarefas v3

> Guia completo de todas as funcionalidades do sistema.
> Cada recurso explicado com exemplos praticos para Telegram e Dashboard.

---

## Índice

1. [Criação de Tarefas](#1-criação-de-tarefas)
2. [Gerenciamento de Tarefas](#2-gerenciamento-de-tarefas)
3. [Planejamento e IA](#3-planejamento-e-ia)
4. [Calendário e Agenda](#4-calendário-e-agenda)
5. [Busca e Anexos](#5-busca-e-anexos)
6. [Mapeamento de Energia](#6-mapeamento-de-energia)
7. [Gamificação](#7-gamificação)
8. [Matriz de Eisenhower](#8-matriz-de-eisenhower)
9. [Pomodoro Timer](#9-pomodoro-timer)
10. [Subtarefas e Decomposição](#10-subtarefas-e-decomposição)
11. [Dashboard — Views e Navegação](#11-dashboard-views-e-navegação)
12. [Automações](#12-automações)
13. [Hábitos e Rotinas](#13-hábitos-e-rotinas)
14. [Histórico Semanal e Anotações](#14-histórico-semanal-e-anotações)
15. [Anexos e Upload de Arquivos](#15-anexos-e-upload-de-arquivos)
16. [Busca com Navegação e Highlight](#16-busca-com-navegação-e-highlight)
17. [Reflexões Diárias](#17-reflexões-diárias)
18. [Modo Foco](#18-modo-foco)
19. [Sistema de Ajuda In-App](#19-sistema-de-ajuda-in-app)
20. [PWA — Instalar como App](#20-pwa-instalar-como-app)
21. [Diagnóstico](#21-diagnóstico)

---

## 1. Criacao de Tarefas

### Via Telegram (texto natural)

A forma mais poderosa de criar tarefas. Basta enviar uma mensagem com linguagem natural e a IA faz o resto.

**Exemplos:**

```
"reuniao amanha com Carlos do Grupo Ser as 10h"
```
A IA detecta:
- Titulo: "Reuniao com Carlos"
- Categoria: Grupo Ser (reconheceu "Carlos" + "Grupo Ser" pelo contexto)
- Prazo: amanha (resolvido para a data real)
- Horario: 10:00
- Prioridade: alta (reuniao com data)
- Tempo estimado: 60min

```
"preciso corrigir provas e preparar slide para aula de quinta"
```
A IA detecta **2 tarefas** na mesma mensagem:
- Tarefa 1: "Corrigir provas" (Trabalho, sem data)
- Tarefa 2: "Preparar slide para aula" (Trabalho, quinta-feira)

```
"pede pro Joao revisar o relatorio ate sexta"
```
A IA detecta **delegacao**:
- Titulo: "Revisar relatorio"
- Delegado para: Joao
- Prazo: sexta-feira

```
"toda segunda tenho reuniao de alinhamento as 9h"
```
A IA detecta **recorrencia**:
- Titulo: "Reuniao de alinhamento"
- Recorrencia: semanal
- Dia: segunda-feira
- Horario: 09:00

**Expressoes temporais que a IA entende:**
- "amanha", "hoje", "ontem"
- "segunda", "terca", ..., "domingo" (proxima ocorrencia)
- "semana que vem", "proxima semana"
- "daqui 3 dias", "daqui uma semana"
- "dia 25/03", "25 de marco"
- "fim do mes", "final da semana"
- "toda segunda", "todo dia", "quinzenalmente"

### Via Telegram (audio)

Grave um audio no Telegram com a mesma linguagem natural. O bot:
1. Baixa o audio
2. Transcreve usando Whisper (via Groq API)
3. Processa o texto resultante da mesma forma

**Requisito:** Variavel `GROQ_API_KEY` configurada no `.env`

### Fluxo de confirmacao

Apos a IA processar sua mensagem, o bot responde com um resumo e pede confirmacao:

```
Tarefa detectada:
  Reuniao com Carlos
  Grupo Ser | alta | amanha 10:00
  ~60min

Confirma? (sim/nao/editar)
```

Voce pode responder:
- **"sim"**, **"ok"**, **"confirma"** — salva a tarefa
- **"nao"**, **"cancela"** — descarta
- **"muda pra sexta"** — a IA ajusta e pede confirmacao novamente
- **"prioridade baixa"** — ajusta a prioridade

### Via Dashboard

No dashboard web, voce pode criar tarefas clicando no botao "+" ou usando o formulario de criacao (quando disponivel na view Todas).

### Lista semanal completa

Voce pode enviar uma semana inteira de uma vez:

```
Segunda:
- Reuniao 9h
- Corrigir provas

Terca:
- Aula de IA 14h
- Preparar material

Quarta:
- Consultoria no cliente
```

A IA detecta cada dia e cria todas as tarefas com as datas corretas.

### Deteccao de status na mensagem

Se voce enviar uma atualizacao de status, a IA detecta:
- "feito ja" / "concluido" / "pronto" — marca como concluida
- "em andamento" / "comecei" — marca como em_andamento
- "nao fiz" / "adiado" — mantém como pendente

---

## 2. Gerenciamento de Tarefas

### Listar tarefas (`/tarefas`)

Lista todas as tarefas pendentes ordenadas por prioridade e data.

```
/tarefas
```

Resposta do bot:
```
Tarefas pendentes (5):

  Reuniao com Carlos
  Grupo Ser | alta | 23/03 10:00

  Corrigir provas de IA
  Trabalho | media | sem data

  ...
```

### Concluir tarefa (`/concluir`)

Mostra um teclado inline com botoes para cada tarefa pendente.

```
/concluir
```

O bot mostra:
```
Qual tarefa concluir?
[Reuniao com Carlos (23/03)]
[Corrigir provas de IA]
[Preparar slide]
[Cancelar]
```

Clique no botao da tarefa desejada. O bot confirma e atualiza o banco.

**No dashboard:** Clique no toggle de status do card (circulo) para alternar entre pendente -> em andamento -> concluida. Ou arraste o card para a coluna desejada.

### Editar tarefa (`/editar`)

Selecione a tarefa por botao inline e depois descreva a mudanca em texto livre.

```
/editar
```
(selecione a tarefa)
```
muda pra sexta e prioridade alta
```

A IA interpreta a mudanca e atualiza os campos corretos.

**No dashboard:** Clique no card da tarefa para abrir o modal de detalhe. La voce pode editar todos os campos diretamente.

### Excluir tarefa (`/excluir`)

Mostra um teclado inline com botões para escolher qual tarefa excluir.

```
/excluir
```

O bot mostra:
```
Qual tarefa quer excluir?
[🗑️ Reuniao com Carlos (23/03)]
[🗑️ Corrigir provas de IA]
[🗑️ Preparar slide]
```

Clique no botão da tarefa que deseja remover. A exclusão é definitiva.

**No dashboard:** Abra o detalhe da tarefa e clique em "Excluir", ou use a seleção em lote.

### Limpar duplicatas (`/limpar`)

Analisa todas as tarefas pendentes e encontra grupos de tarefas com títulos similares (possíveis duplicatas).

```
/limpar
```

Resposta do bot:
```
🔍 Encontrei 2 grupo(s) de tarefas similares:

Grupo 1: (3 tarefas)
  • Reunião com Carlos — 23/03
  • Reuniao com Carlos do Ser — 24/03
  • Reunião Carlos — sem data

Total: 3 tarefas em 1 grupo similar.
Use /excluir para remover as duplicatas.
```

O algoritmo usa similaridade de texto (SequenceMatcher ≥ 70%) para detectar títulos parecidos. Útil quando você cria tarefas por voz e a IA gera variações do mesmo título.

### Cancelar operação (`/cancelar`)

Cancela qualquer operação em andamento (confirmação, edição, etc).

```
/cancelar
```

---

## 3. Planejamento e IA

### Planejar o dia (`/planejar`)

A IA analisa suas tarefas pendentes, seu nivel de energia registrado, e monta um plano com blocos de tempo.

```
/planejar
```

Resposta:
```
Plano do dia — 22/03

MANHA (energia alta):
  08:00-09:00 — Corrigir provas de IA (cognitivo)
  09:00-10:00 — Reuniao com Carlos

TARDE (energia media):
  14:00-15:30 — Aula de IA
  16:00-17:00 — Responder emails (admin)

NOITE:
  Estudar ingles (30min)

Carga: 85% | 4h30 ocupadas
```

**Dica:** Use `/energia` antes de `/planejar` para que a IA saiba seus niveis de energia e aloque tarefas cognitivas nos melhores periodos.

Depois do planejamento, voce pode conversar com a IA:
- "troca a aula de horario"
- "tira o ingles de hoje"
- "adiciona revisao de artigo as 11h"

### Feedback do dia (`/feedback`)

A IA avalia como foi seu dia (tarefas concluidas vs pendentes) com tom de coach motivacional.

```
/feedback
```

Resposta:
```
Parabens, 4 de 6 tarefas concluidas (67%)!

Pontos fortes:
- Reunioes todas feitas no horario
- Trabalho bem distribuido

Ponto de atencao:
- Ingles e leitura ficaram pra tras pelo 3o dia seguido
- Sugestao: proteja 30min no inicio da manha pra habitos pessoais

Amanha voce tem 3 tarefas. Dia mais leve — aproveite!
```

### Resumo rapido (`/resumo`)

Numeros simples e diretos sobre suas tarefas.

```
/resumo
```

Resposta:
```
Resumo:
  Total: 12
  Pendentes: 5
  Concluidas esta semana: 7
  Atrasadas: 2
  Reunioes pendentes: 1
  Alta prioridade: 3
```

### Relatorio semanal (`/relatorio`)

Relatorio completo da semana gerado pela IA, com analise de padroes.

```
/relatorio
```

### Coaching IA (`/coaching`)

Dica personalizada baseada nos seus padroes de tarefas.

```
/coaching
```

Resposta:
```
Coaching IA

Observei que suas tarefas de "Consultoria" tendem a acumular
nas quartas e quintas. Considere distribuir 1-2 tarefas de
consultoria para segunda e terca, quando voce tem menos carga.

Seu streak atual e de 4 dias! Continue assim para chegar ao
proximo nivel.

Dica pratica: tente o "2-minute rule" — se uma tarefa leva
menos de 2 minutos, faca agora em vez de adicionar na lista.
```

---

## 4. Calendario e Agenda

### Conectar Google Calendar (`/conectar_google`)

Inicia o fluxo OAuth2 para autorizar o bot a ler seus eventos do Google Calendar.

```
/conectar_google
```

O bot envia um link. Clique nele, autorize com sua conta Google, e volte ao Telegram.

**Requisitos:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `BOT_PUBLIC_URL` e `OAUTH_SECRET_KEY` configurados no `.env`

### Conectar Microsoft Outlook/Teams (`/conectar_microsoft`)

Mesmo processo para Outlook e Teams.

```
/conectar_microsoft
```

**Requisitos:** `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `BOT_PUBLIC_URL` e `OAUTH_SECRET_KEY` configurados no `.env`

### Ver agenda do dia (`/agenda`)

Mostra todos os eventos do dia de todos os calendarios conectados.

```
/agenda
```

Resposta:
```
Agenda de Hoje (22/03)

  09:00-10:00 — Standup diario (Google)
  10:00-11:00 — Reuniao pedagógica (Teams) · Entrar
  14:00-15:30 — Aula de IA (Google)
  16:00-17:00 — 1:1 com coordenador (Teams) · Entrar
```

Eventos com link de reuniao (Meet, Teams, Zoom) mostram o botao "Entrar" com o link clicavel.

### Forcar sincronizacao (`/sync`)

Forca uma sincronizacao imediata de todos os calendarios conectados.

```
/sync
```

Resposta:
```
Sync completo!
Google Calendar: 15 eventos
Google Tasks: 3 tarefas
Outlook: 8 eventos
```

**Sincronizacao automatica:** Alem do `/sync` manual, o bot sincroniza automaticamente a cada 15 minutos.

### Desconectar calendario (`/desconectar`)

Remove a conexao com um calendario. Os tokens OAuth sao apagados do banco.

```
/desconectar google
/desconectar microsoft
```

### No dashboard

Os eventos dos calendarios aparecem:
- Na **timeline** da view Hoje (misturados com tarefas)
- No **calendario semanal** (cards com icone de cor: verde para Google, azul para Microsoft)
- Na **busca** (resultados do tipo "evento")

---

## 5. Busca e Anexos

### Buscar (`/buscar`)

Busca unificada em tarefas, eventos do calendario, anotacoes semanais e anexos.

```
/buscar reuniao com Carlos
```

Resposta:
```
Resultados para "reuniao com Carlos" (3 encontrados)

  Reuniao com Carlos
  Grupo Ser · 23/03 · pendente

  Standup com Carlos
  22/03 10:00 · google

  Notas da reuniao de acompanhamento
  "Carlos mencionou que..."
```

A busca procura por correspondencia parcial (ILIKE) no titulo de tarefas, titulo de eventos, anotacoes semanais e titulo/conteudo de anexos.

**No dashboard:** Use a barra de busca no topo da pagina. Os resultados aparecem em tempo real conforme voce digita.

### Anexar conteudo (`/anexar`)

Salva um texto como anexo pesquisavel. Util para anotacoes longas, transcricoes de reuniao, links importantes.

**Modo 1 — Responder a mensagem:**
1. Tenha uma mensagem no chat (ex: transcricao de audio)
2. Responda a essa mensagem com `/anexar Titulo do anexo`
3. O conteudo da mensagem original e salvo como anexo

**Modo 2 — Duas etapas:**
1. Envie `/anexar Titulo do anexo`
2. O bot pede o conteudo
3. Envie o texto na mensagem seguinte

```
/anexar Notas da reuniao de alinhamento
```

Bot:
```
Titulo: Notas da reuniao de alinhamento
Agora envie o conteudo:
```

Voce:
```
Carlos pediu para revisar o cronograma do projeto.
Prazo final: 30/03. Maria vai fazer a parte de dados.
```

Bot:
```
Anexo salvo: Notas da reuniao de alinhamento (142 caracteres)
```

Depois, voce pode encontrar esse conteudo com `/buscar cronograma` ou `/buscar Maria dados`.

---

## 6. Mapeamento de Energia

### Via Telegram (`/energia`)

Registra seu nivel de energia para um periodo do dia.

```
/energia 4 manha    — energia 4/5 de manha
/energia 2 tarde    — energia 2/5 de tarde
/energia 3          — auto-detecta periodo pelo horario atual
```

**Niveis:**
- 1 — Exausto (vermelho)
- 2 — Baixa (laranja)
- 3 — Normal (amarelo)
- 4 — Boa (verde claro)
- 5 — Energia total (verde)

**Periodos:**
- Manha: 6h-11h
- Tarde: 12h-17h
- Noite: 18h+

### Via Dashboard

Na view Hoje, o dashboard mostra dots clicaveis para cada periodo. Clique nos dots para registrar sua energia diretamente na interface.

### Como a IA usa seus dados de energia

Quando voce usa `/planejar`, a IA consulta seus registros de energia e:
- Aloca tarefas **cognitivas** (estudar, programar, escrever) nos periodos de energia alta
- Aloca tarefas **administrativas** (emails, organizar, revisar) nos periodos de energia baixa
- Sugere pausas em periodos de energia muito baixa

---

## 7. Gamificacao

### Sistema de XP

Cada tarefa concluida gera XP:
- Tarefa basica: 10 XP
- Bonus por prazo cumprido: +5 XP
- Bonus por alta prioridade: +5 XP
- Bonus por streak ativo: +3 XP

### Niveis (1-10)

| Nivel | Titulo | XP necessario |
|-------|--------|--------------|
| 1 | Iniciante Organizado | 0 |
| 2 | Aprendiz de Gestao | 100 |
| 3 | Planejador Atento | 300 |
| 4 | Executor Consistente | 600 |
| 5 | Mestre do Foco | 1000 |
| 6 | Estrategista | 1500 |
| 7 | Produtividade Ninja | 2100 |
| 8 | Lider de Tempo | 2800 |
| 9 | Guru da Organizacao | 3600 |
| 10 | Professor Nivel S | 4500 |

### Streaks

Dias consecutivos em que voce conclui pelo menos 70% das tarefas do dia. O streak:
- Aumenta em 1 a cada dia produtivo
- Reseta para 0 se voce nao atingir 70% em um dia
- Seu melhor streak fica salvo como recorde

### No Dashboard

- **Progress Ring**: Circulo SVG animado no topo mostrando % de conclusao do dia
- **Barra de XP**: Barra de progresso do nivel atual para o proximo
- **Streak counter**: Numero de dias consecutivos produtivos
- **Nivel e titulo**: Exibidos ao lado do seu progresso

---

## 8. Matriz de Eisenhower

A Matriz de Eisenhower divide suas tarefas em 4 quadrantes baseados em **urgencia** e **importancia**:

| | Urgente | Nao urgente |
|---|---------|------------|
| **Importante** | Q1: Fazer agora | Q2: Agendar |
| **Nao importante** | Q3: Delegar | Q4: Eliminar |

### Auto-classificacao

A IA classifica automaticamente suas tarefas nos quadrantes:
- **Q1 (Fazer agora)**: prazo proximo + alta prioridade
- **Q2 (Agendar)**: sem prazo urgente + alta/media prioridade
- **Q3 (Delegar)**: baixa prioridade + prazo definido (ou delegadas)
- **Q4 (Eliminar)**: baixa prioridade + sem prazo

Tarefas auto-classificadas mostram um badge "auto" no card.

### Override manual (drag&drop)

Voce pode arrastar qualquer tarefa entre quadrantes no dashboard. A classificacao manual sobrepoe a automatica e fica salva no banco (coluna `quadrante_eisenhower`).

### No Dashboard

A view de Eisenhower mostra os 4 quadrantes lado a lado (desktop) ou empilhados (mobile). Cada quadrante tem um header colorido com contagem de tarefas.

---

## 9. Pomodoro Timer

Timer de 25 minutos integrado ao dashboard, vinculado a uma tarefa especifica.

### Como usar

1. No dashboard, clique no icone de play em qualquer card de tarefa
2. O timer aparece no topo da pagina com o nome da tarefa
3. Controles: Play/Pause, Stop
4. Ao terminar os 25min, voce recebe uma notificacao
5. O tempo acumulado e salvo por tarefa

### Tracking de tempo

- O tempo e salvo no `localStorage` do navegador em tempo real (a cada 30 segundos)
- Ao finalizar o Pomodoro, o tempo e somado na coluna `tempo_gasto_min` da tarefa no banco
- No card da tarefa, voce pode ver "estimado: 120min | gasto: 50min"

---

## 10. Subtarefas e Decomposicao

### Decompor tarefa (`/decompor`)

A IA quebra uma tarefa grande em 3-6 subtarefas concretas com tempo estimado.

```
/decompor
```

(selecione a tarefa "Preparar aula de IA")

Resposta:
```
Decomposicao: Preparar aula de IA

1. Revisar ementa e selecionar topicos (20min)
2. Pesquisar exemplos praticos (30min)
3. Criar slides (45min)
4. Preparar exercicio pratico (25min)
5. Testar apresentacao (15min)

Total estimado: 2h15
Confirma decomposicao? (sim/nao)
```

Ao confirmar, as subtarefas sao criadas na tabela `subtarefas` vinculadas a tarefa original.

### No Dashboard

As subtarefas aparecem como checklist dentro do card da tarefa (ou no modal de detalhe). Cada subtarefa pode ser marcada como concluida individualmente, e o progresso e exibido como barra.

---

## 11. Dashboard — Views e Navegação

O dashboard possui **7 views** acessíveis tanto pelo menu superior (desktop) quanto pela barra de navegação inferior (mobile).

### View "Todas"

**O que faz:** Lista todas as tarefas com filtros avançados.

**Onde:** Dashboard web — botão "Todas" no menu.

**Filtros disponíveis:**
- **Categoria**: Trabalho, Consultoria, Grupo Ser, Pessoal
- **Prioridade**: Alta, Média, Baixa
- **Status**: Pendente, Em andamento, Concluída

**Stat cards clicáveis** no topo:
- Total, Pendentes, Concluídas, Atrasadas, Reuniões
- Clicar num card filtra as tarefas correspondentes

### View "Hoje"

**O que faz:** Mostra apenas as tarefas e eventos do dia com timeline visual.

**Onde:** Dashboard web — botão "Hoje" (com badge de contagem).

**Elementos:**
- Indicador "Agora" na posição atual do dia
- Tarefas com horário posicionadas no horário correto
- Tarefas sem horário listadas abaixo
- Eventos do calendário integrados na timeline (Google verde, Microsoft azul)
- Dots de energia clicáveis por período (Manhã/Tarde/Noite)
- Preview da anotação semanal (se houver anotação na semana atual)

### View "Semana" (Calendário)

**O que faz:** Calendário semanal com 7 dias lado a lado.

**Onde:** Dashboard web — botão "Semana".

**Elementos:**
- Cards de tarefas dentro de cada dia
- Drag & drop entre dias para reagendar
- Responsive: em mobile empilha os dias
- Badge com contagem de tarefas por dia

### View "Revisão Semanal"

**O que faz:** Dashboard de métricas e retrospectiva da semana.

**Onde:** Dashboard web — botão "Revisão" (com badge de anotação quando há texto salvo).

**Elementos:**
- Taxa de conclusão (%)
- Heatmap de produtividade por dia (grid 365 dias)
- Distribuição por categoria (pizza/barra)
- Tempo pessoal vs trabalho
- Tracker de hábitos (grid por subcategoria)
- Navegação entre semanas (< >) para retrospectiva
- Campo de anotação semanal (textarea persistido no banco)
- Botão "Salvar Semana" para criar snapshot das métricas

### View "Matriz" (Eisenhower)

**O que faz:** Divide tarefas em 4 quadrantes de urgência vs importância.

**Onde:** Dashboard web — botão "Matriz".

**Elementos:**
- 4 quadrantes: Fazer Agora (Q1), Agendar (Q2), Delegar (Q3), Eliminar (Q4)
- Auto-classificação pela IA (badge "auto")
- Drag & drop entre quadrantes para reclassificação manual
- Contagem de tarefas por quadrante no header colorido
- Suporta drag & drop mobile (touch events)

### View "Blocos" (Blocos de Tempo)

**O que faz:** Visualização das tarefas por período do dia.

**Onde:** Dashboard web — botão "Blocos".

**Elementos:**
- 3 blocos visuais: Manhã (6h-11h), Tarde (12h-17h), Noite (18h+)
- Tarefas posicionadas no bloco correspondente ao horário
- Integrado com dados de energia (se registrado)
- Visual limpo para planejamento do dia

### View "KPIs"

**O que faz:** Indicadores de performance para acompanhamento de longo prazo.

**Onde:** Dashboard web — botão "KPIs".

**Elementos:**
- Productivity Score (pontuação de produtividade)
- Gráfico de barras: últimas 8 semanas de taxa de conclusão
- Gráfico donut: distribuição por categoria
- Sparkline: tendência de conclusão
- Distribuição por categoria com cores e percentuais

### Ações em lote (Bulk)

**O que faz:** Selecionar e agir sobre múltiplas tarefas de uma vez.

**Onde:** Dashboard web — view "Todas" e "Hoje".

**Como usar:**
1. Clique no botão **"☑ Selecionar"** ao lado das abas de status
2. Cada card ganha um checkbox — clique nos cards que deseja selecionar
3. Uma barra de ações aparece na parte inferior com o contador de selecionados
4. Opções: **Concluir** ou **Excluir** as tarefas selecionadas
5. Clique em **Cancelar** para sair do modo seleção

**Atalho:** Segure **Shift** e clique em um card para entrar no modo seleção diretamente.

A barra de ações some automaticamente ao trocar de view ou quando nenhuma tarefa está selecionada.

### Drag & Drop

**O que faz:** Reorganizar tarefas arrastando cards.

**Onde:** Dashboard web — views Todas, Semana, Matriz.

**Tipos:**
- **Entre status**: Arraste cards para mudar de Pendente -> Em andamento -> Concluída
- **Entre dias**: No calendário semanal, arraste entre dias para reagendar
- **Entre quadrantes**: Na Matriz de Eisenhower, arraste entre Q1/Q2/Q3/Q4
- **Upload de arquivo**: Arraste arquivo para a drop zone no modal de detalhe

### Modo claro/escuro

**O que faz:** Alterna entre tema escuro (padrão) e claro.

**Onde:** Dashboard web — toggle no canto superior direito.

A preferência é salva no `localStorage` e persiste entre sessões.

---

## 12. Automacoes

Automacoes que rodam sozinhas, sem voce precisar fazer nada:

### Resumo matinal (7:30)
Todo dia as 7:30, o bot envia:
- Quantas tarefas para hoje
- Lista com prioridade e horarios
- Eventos do calendario
- Sugestao de reagendamento para atrasadas
- Carga estimada do dia (%)

### Check-in meio-dia (13:00)
As 13:00, o bot envia:
- Progresso do dia (concluidas/total)
- Tarefas restantes para a tarde

### Relatorio semanal (sexta 17:00)
Toda sexta as 17:00, o bot envia:
- Relatorio completo da semana
- Taxa de conclusao por categoria
- Padroes identificados
- Sugestoes para a proxima semana

### Lembretes de tarefas (15min antes)
Para qualquer tarefa com horario definido, o bot envia lembrete 15 minutos antes.

### Lembretes de eventos do calendario (15min antes)
Para eventos sincronizados do Google/Microsoft, o bot envia lembrete 15 minutos antes com link de reuniao (se disponivel).

### Tarefas recorrentes (6:00)
Todo dia as 6:00, o bot verifica tarefas recorrentes e cria novas instancias para o dia.

### Sync de calendarios (a cada 15min)
A cada 15 minutos, o bot sincroniza eventos dos calendarios conectados.

### Keep-alive (a cada 4min)
Ping interno para evitar que o Koyeb coloque o servico em sleep no free tier.

---

## 13. Habitos e Rotinas

### Tipos de item

O sistema suporta 3 tipos de item:
- **Tarefa**: Item unico com prazo (padrao)
- **Habito**: Item recorrente para tracking (ex: "Academia")
- **Rotina**: Item fixo no horario (ex: "Cafe da manha 7h")

### Subcategorias pessoais

Na categoria "Pessoal", existem subcategorias para tracking:
- Academia
- Leitura
- Corrida
- Beach Tennis
- Estudo
- Meditacao
- Ingles

### Tracker de habitos

Na view Revisao Semanal, um grid mostra quais habitos foram feitos em cada dia da semana (check/x por dia).

---

## 14. Histórico Semanal e Anotações

### Salvar snapshot

**O que faz:** Cria um registro permanente das métricas da semana.

**Onde:** Dashboard web — view Revisão Semanal — botão "Salvar Semana".

**Passo a passo:**
1. Abra a view "Revisão" no dashboard
2. Veja as métricas da semana (taxa de conclusão, distribuição, hábitos)
3. Escreva uma anotação no campo de texto (opcional mas recomendado)
4. Clique em "Salvar Semana"
5. O snapshot fica salvo na tabela `historico_semanal`

### Anotações semanais

**O que faz:** Permite escrever observações sobre a semana que ficam salvas e pesquisáveis.

**Onde:** Dashboard web — view Revisão Semanal (campo textarea).

**Exemplos:**
- "Semana puxada, muitas reuniões do Grupo Ser"
- "Consegui manter a academia 4x — streak de 12 dias"
- "Preciso melhorar tempo pessoal — muito Trabalho"

### Visibilidade das anotações

As anotações aparecem em **3 lugares** no dashboard:

1. **Badge no menu "Revisão"**: Um ponto dourado aparece no botão de Revisão quando há anotação na semana atual, indicando que há algo escrito.

2. **Preview na view Hoje**: Na view Hoje, um card resumido mostra a anotação da semana atual com opção de clicar para ir à Revisão.

3. **Pesquisável via busca**: As anotações são incluídas nos resultados da busca global (barra de busca e `/buscar`).

### Navegação entre semanas

Use os botões < > para navegar entre semanas anteriores e comparar evolução. O histórico de semanas passadas mostra métricas + anotação de cada período.

---

## 15. Anexos e Upload de Arquivos

### Via Telegram (`/anexar`)

**O que faz:** Salva um texto como anexo pesquisável vinculado ao sistema.

**Onde:** Telegram — comando `/anexar`.

**Modo 1 — Responder a mensagem:**
1. Tenha uma mensagem no chat (ex: transcrição de áudio)
2. Responda a essa mensagem com `/anexar Título do anexo`
3. O conteúdo da mensagem original é salvo como anexo

**Modo 2 — Duas etapas:**
1. Envie `/anexar Título do anexo`
2. O bot pede o conteúdo
3. Envie o texto na mensagem seguinte

**Exemplo:**
```
/anexar Notas da reunião de alinhamento
```
Bot:
```
Título: Notas da reunião de alinhamento
Agora envie o conteúdo:
```
Você:
```
Carlos pediu para revisar o cronograma do projeto.
Prazo final: 30/03. Maria vai fazer a parte de dados.
```

### Via Dashboard (upload de arquivos)

**O que faz:** Permite anexar arquivos arrastando para dentro do modal de detalhe da tarefa.

**Onde:** Dashboard web — modal de detalhe de qualquer tarefa.

**Passo a passo:**
1. Clique em um card de tarefa para abrir o modal de detalhe
2. Role até a seção "Anexos"
3. Para adicionar:
   - **Drag & Drop**: Arraste um arquivo do computador para a área tracejada "Solte o arquivo aqui"
   - **Clique**: Clique na área tracejada para abrir o seletor de arquivos
4. O arquivo é carregado e o nome aparece na área
5. Os metadados são salvos na tabela `anexos` (coluna `metadata` em JSONB)

**Tipos suportados:**
- `texto` — notas, anotações manuais
- `transcricao` — áudios transcritos vinculados a tarefas
- `link` — URLs com descrição
- `arquivo` — PDFs, imagens, documentos (metadata: nome, tamanho, tipo MIME)

### Pesquisa em anexos

Todos os anexos são pesquisáveis:
- Via bot: `/buscar cronograma` encontra anexos cujo título ou conteúdo contenha "cronograma"
- Via dashboard: a barra de busca inclui anexos nos resultados

---

## 16. Busca com Navegação e Highlight

### Via Telegram (`/buscar`)

**O que faz:** Busca unificada em tarefas, eventos, anotações e anexos.

**Onde:** Telegram — comando `/buscar`.

```
/buscar reunião com Carlos
```

O bot busca em 4 fontes e retorna resultados unificados com ícone por tipo.

### Via Dashboard (barra de busca)

**O que faz:** Busca em tempo real com highlight e navegação.

**Onde:** Dashboard web — barra de busca no topo da página.

**Passo a passo:**
1. Clique na barra de busca (ou pressione `/` para focar)
2. Digite o termo (ex: "Carlos")
3. Os resultados aparecem em dropdown conforme você digita (debounce 300ms)
4. O termo buscado é **destacado (highlight)** em amarelo nos resultados
5. Cada resultado mostra:
   - Ícone por tipo (tarefa, evento, anotação, anexo)
   - Título com highlight
   - Metadados (categoria, data, status)
   - Preview do conteúdo (para anexos e anotações)
6. **Clique no resultado** para navegar até o item:
   - Tarefa: abre o modal de detalhe
   - Evento: navega para a view Hoje
   - Anotação: navega para a view Revisão da semana correspondente

---

## 17. Reflexões Diárias

**O que faz:** O bot envia uma pergunta reflexiva no final do dia para autoavaliação.

**Onde:** Telegram (mensagem automática do bot).

O bot pode enviar uma pergunta reflexiva no final do dia (ex: 22h):

```
Reflexão do dia:

Qual foi a tarefa mais significativa que você completou hoje e por quê?
```

Sua resposta é salva no banco (tabela `reflexoes`) para consulta futura.

---

## 18. Modo Foco

**O que faz:** Silencia lembretes de baixa prioridade por um período definido.

**Onde:** Telegram — comando `/foco`.

### Ativar

```
/foco 2h         — 2 horas de foco
/foco 45min      — 45 minutos
/foco             — 1 hora (padrão)
```

Durante o modo foco:
- Lembretes de **baixa prioridade** são silenciados
- Lembretes de **alta prioridade** continuam chegando
- O bot avisa quando o tempo acabar

### Desativar

```
/foco off
/foco sair
/foco desligar
```

---

## 19. Sistema de Ajuda In-App

**O que faz:** Guia o usuário dentro do dashboard com 3 camadas de ajuda.

**Onde:** Dashboard web — disponível em todas as views.

### Camada 1: Tour de Onboarding

Quando o usuário acessa o dashboard pela primeira vez (ou clica em "Iniciar Tour"):

1. Um overlay escuro destaca um elemento da interface
2. Um popup explicativo aparece ao lado com seta apontando
3. Botões "Próximo" e "Pular" para avançar ou encerrar
4. O tour passa pelos principais elementos: menu, filtros, stat cards, cards de tarefa

**Como ativar manualmente:** Clique no botão "?" no header > "Iniciar Tour" na Central de Ajuda.

### Camada 2: Tooltips Contextuais (botões "?")

Cada seção do dashboard tem um pequeno botão "?" que, ao ser clicado:

1. Exibe um card flutuante com explicação da seção
2. O card tem seta apontando para o elemento pai
3. Fecha ao clicar fora do card

**Exemplo:** Na seção de Gamificação, o "?" explica o sistema de XP, níveis e streaks.

### Camada 3: Central de Ajuda

O botão no header abre um modal completo com:

1. Guias organizados por funcionalidade
2. Explicação de cada view
3. Dicas de atalhos e gestos
4. Dicas contextuais baseadas na view ativa

**Como acessar:** Clique no botão "Central de Ajuda" no header do dashboard.

---

## 20. PWA — Instalar como App

**O que faz:** O dashboard pode ser instalado como app nativo no celular ou desktop.

**Onde:** Navegador (Chrome, Edge, Safari).

### Como instalar

1. Abra o dashboard no Chrome (celular ou desktop)
2. Clique em "Instalar" (banner automático ou menu do navegador > "Instalar app")
3. O dashboard aparece como app com ícone na home screen

### Funcionalidade offline

O dashboard usa um **Service Worker** (`sw.js`) com estratégia **network-first**:
- Tenta buscar dados da rede primeiro
- Se a rede falhar, usa cache local
- Arquivos estáticos (HTML, CSS, JS, fontes) são cacheados na primeira visita
- Dados do Supabase são atualizados quando há conexão

### Arquivos PWA

| Arquivo | Função |
|---------|--------|
| `web/manifest.json` | Define nome, ícones, cores e comportamento do app |
| `web/sw.js` | Service Worker com cache network-first |

---

## 21. Diagnóstico

### Status (`/status`)

**O que faz:** Verifica a conexão com todas as APIs e mostra o status das variáveis de ambiente.

**Onde:** Telegram — comando `/status`.

```
/status
```

Resposta:
```
Diagnóstico do Sistema

  Supabase: Conectado (12ms)
  Gemini API: Conectada
  Claude API: Não configurada
  Groq API: Conectada
  Google Calendar: Conectado (15 eventos)
  Microsoft Calendar: Não configurado

Variáveis:
  TELEGRAM_BOT_TOKEN: ok
  SUPABASE_URL: ok
  GEMINI_API_KEY: ok
  ANTHROPIC_API_KEY: ausente
  GROQ_API_KEY: ok
  GOOGLE_CLIENT_ID: ok
  BOT_PUBLIC_URL: ok
```

---

## Dicas de Produtividade

1. **Comece o dia com `/planejar`** — a IA monta blocos de tempo baseados na sua energia
2. **Use `/energia` de manhã** — melhora a qualidade do planejamento
3. **Áudio é mais rápido** — grave um áudio listando tudo de uma vez
4. **Envie a semana inteira** — "Segunda: X, Terça: Y, Quarta: Z"
5. **Use `/coaching` quando travar** — a IA dá dicas baseadas nos seus padrões
6. **Confie no Eisenhower** — arraste tarefas para os quadrantes certos
7. **Pomodoro para tarefas grandes** — 25min de foco vence a procrastinação
8. **Salve anotações com `/anexar`** — tudo fica pesquisável depois
9. **Revise toda sexta** — use a view Revisão Semanal para retrospectiva
10. **Proteja tempo pessoal** — a IA já te lembra disso no feedback
11. **Use a busca** — `/buscar` no Telegram ou barra de busca no dashboard encontra qualquer coisa
12. **Explore a ajuda** — clique nos botões "?" do dashboard para aprender cada seção

---

*Manual criado para o Organizador de Tarefas v3 — cada funcionalidade explicada para uso e ensino.*
