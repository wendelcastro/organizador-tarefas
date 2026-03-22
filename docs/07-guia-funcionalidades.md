# Manual do Usuario — Organizador de Tarefas v3

> Guia completo de todas as funcionalidades do sistema.
> Cada recurso explicado com exemplos praticos para Telegram e Dashboard.

---

## Indice

1. [Criacao de Tarefas](#1-criacao-de-tarefas)
2. [Gerenciamento de Tarefas](#2-gerenciamento-de-tarefas)
3. [Planejamento e IA](#3-planejamento-e-ia)
4. [Calendario e Agenda](#4-calendario-e-agenda)
5. [Busca e Anexos](#5-busca-e-anexos)
6. [Mapeamento de Energia](#6-mapeamento-de-energia)
7. [Gamificacao](#7-gamificacao)
8. [Matriz de Eisenhower](#8-matriz-de-eisenhower)
9. [Pomodoro Timer](#9-pomodoro-timer)
10. [Subtarefas e Decomposicao](#10-subtarefas-e-decomposicao)
11. [Dashboard — Views e Navegacao](#11-dashboard-views-e-navegacao)
12. [Automacoes](#12-automacoes)
13. [Habitos e Rotinas](#13-habitos-e-rotinas)
14. [Historico Semanal](#14-historico-semanal)
15. [Reflexoes Diarias](#15-reflexoes-diarias)
16. [Modo Foco](#16-modo-foco)
17. [Diagnostico](#17-diagnostico)

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

### Cancelar operacao (`/cancelar`)

Cancela qualquer operacao em andamento (confirmacao, edicao, etc).

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

## 11. Dashboard — Views e Navegacao

### View "Todas"

Lista todas as tarefas com filtros por:
- **Categoria**: Trabalho, Consultoria, Grupo Ser, Pessoal
- **Prioridade**: Alta, Media, Baixa
- **Status**: Pendente, Em andamento, Concluida

**Stat cards clicaveis** no topo:
- Total, Pendentes, Concluidas, Atrasadas, Reunioes
- Clicar num card filtra as tarefas correspondentes

### View "Hoje"

Mostra apenas as tarefas do dia com **timeline vertical**:
- Indicador "Agora" na posicao atual do dia
- Tarefas com horario posicionadas no horario correto
- Tarefas sem horario listadas abaixo
- Eventos do calendario integrados na timeline
- Dots de energia clicaveis por periodo

### View "Semana"

Calendario semanal com 7 dias:
- Cards de tarefas dentro de cada dia
- Drag&drop entre dias para reagendar
- Responsive: em mobile empilha os dias
- Badge com contagem de tarefas por dia

### View "Revisao Semanal"

Dashboard de metricas da semana:
- Taxa de conclusao (%)
- Heatmap de produtividade por dia
- Distribuicao por categoria (pizza/barra)
- Tempo pessoal vs trabalho
- Tracker de habitos (grid por subcategoria)
- Navegacao entre semanas (< >) para retrospectiva
- Campo de anotacao semanal

### View "KPIs"

Indicadores chave de performance para acompanhamento de longo prazo.

### Acoes em lote (Bulk)

1. Segure **Shift** e clique em multiplos cards para seleciona-los
2. Uma barra de acoes aparece no topo
3. Opcoes: **Concluir todos** ou **Excluir todos**

### Drag & Drop

- **Entre status**: Arraste cards para mudar de Pendente -> Em andamento -> Concluida
- **Entre dias**: No calendario semanal, arraste entre dias para reagendar
- **Entre quadrantes**: Na Matriz de Eisenhower, arraste entre Q1/Q2/Q3/Q4

### Modo claro/escuro

Toggle no canto superior direito. A preferencia e salva no `localStorage` e persiste entre sessoes.

### PWA (instalar como app)

O dashboard pode ser instalado como app nativo:
1. Abra no Chrome (celular ou desktop)
2. Clique em "Instalar" (banner ou menu do navegador)
3. O dashboard aparece como app com icone na home screen

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

## 14. Historico Semanal

### Salvar snapshot

Na view Revisao Semanal do dashboard, clique em "Salvar Semana" para criar um snapshot das metricas.

### Anotacoes

Cada semana pode ter uma anotacao pessoal:
- "Semana puxada, muitas reunioes"
- "Consegui manter a academia 4x"
- "Preciso melhorar tempo pessoal"

### Navegacao

Use os botoes < > para navegar entre semanas anteriores e comparar evolucao.

---

## 15. Reflexoes Diarias

O bot pode enviar uma pergunta reflexiva no final do dia (ex: 22h):

```
Reflexao do dia:

Qual foi a tarefa mais significativa que voce completou hoje e por que?
```

Sua resposta e salva no banco (tabela `reflexoes`) para consulta futura.

---

## 16. Modo Foco

### Ativar

```
/foco 2h         — 2 horas de foco
/foco 45min      — 45 minutos
/foco             — 1 hora (padrao)
```

Durante o modo foco:
- Lembretes de **baixa prioridade** sao silenciados
- Lembretes de **alta prioridade** continuam chegando
- O bot avisa quando o tempo acabar

### Desativar

```
/foco off
/foco sair
/foco desligar
```

---

## 17. Diagnostico

### Status (`/status`)

Verifica a conexao com todas as APIs e mostra o status das variaveis de ambiente.

```
/status
```

Resposta:
```
Diagnostico do Sistema

  Supabase: Conectado (12ms)
  Gemini API: Conectada
  Claude API: Nao configurada
  Groq API: Conectada
  Google Calendar: Conectado (15 eventos)
  Microsoft Calendar: Nao configurado

Variaveis:
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
2. **Use `/energia` de manha** — melhora a qualidade do planejamento
3. **Audio e mais rapido** — grave um audio listando tudo de uma vez
4. **Envie a semana inteira** — "Segunda: X, Terca: Y, Quarta: Z"
5. **Use `/coaching` quando travar** — a IA da dicas baseadas nos seus padroes
6. **Confie no Eisenhower** — arraste tarefas para os quadrantes certos
7. **Pomodoro para tarefas grandes** — 25min de foco vence a procrastinacao
8. **Salve anotacoes com `/anexar`** — tudo fica pesquisavel depois
9. **Revise toda sexta** — use a view Revisao Semanal para retrospectiva
10. **Proteja tempo pessoal** — a IA ja te lembra disso no feedback

---

*Manual criado para o Organizador de Tarefas v3 — cada funcionalidade explicada para uso e ensino.*
