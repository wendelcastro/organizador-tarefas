# Arquitetura do Organizador de Tarefas v3

> Documentacao didatica - cada decisao explicada

## Visao Geral

```
[Wendel manda audio/texto]
        |
        v
[Telegram Bot] --- transcreve audio (Whisper via Groq)
        |
        v
[AI Brain v2] --- Gemini 2.5 Flash (primario) | Claude (fallback)
        |         classifica, resolve datas, detecta multiplas,
        |         analisa sobrecarga, sugere realocacao,
        |         aprende contexto (memoria), detecta conflitos,
        |         decomposicao de tarefas, alerta preditivo,
        |         planejamento por energia, coaching
        v
[Supabase] --- armazena tudo (PostgreSQL + Realtime)
        |
        v
[Dashboard Web] --- visualiza no navegador (GitHub Pages, PWA)

        === SINCRONIZACAO DE CALENDARIOS ===

[Google Calendar] --OAuth2--> [calendar_sync.py] --> [Supabase: eventos_calendario]
[Microsoft Outlook] --OAuth2--> [calendar_sync.py] --> [Supabase: eventos_calendario]
[Google Tasks] --OAuth2--> [calendar_sync.py] --> [Supabase: tarefas]

        === AUTOMACOES (rodam sozinhas via JobQueue) ===

[06:00] Tarefas recorrentes ──> Supabase
[07:30] Resumo matinal + reagendamento ──> Telegram
[13:00] Check-in do meio-dia ──> Telegram
[HH:MM - 15min] Lembrete de tarefa ──> Telegram
[HH:MM - 15min] Lembrete de evento calendario ──> Telegram
[A cada 15min] Sync calendarios ──> Supabase
[Sexta 17:00] Relatorio semanal ──> Telegram
[A cada 4min] Keep-alive (ping) ──> Koyeb health check
```

## Por que cada tecnologia?

### Telegram Bot (A Recepcao)
- **Por que Telegram e nao WhatsApp?**
  - WhatsApp: API oficial e paga (Meta Business), alternativas nao-oficiais = risco de bloqueio
  - Telegram: API de bots e gratuita, oficial, sem risco, suporta audio nativo
- **Linguagem**: Python (simples, muitas bibliotecas prontas)
- **Biblioteca**: `python-telegram-bot[job-queue]` (a mais usada, com agendamento integrado)
- **Transcricao**: Whisper via Groq API (gratuito, rapido)

### AI Brain v2 (O Cerebro)
- **Modelo primario**: Gemini 2.5 Flash (`gemini-2.5-flash`) — gratuito, rapido, excelente para classificacao
- **Modelo fallback**: Claude Sonnet (`claude-sonnet-4-20250514`) — usado se Gemini falhar
- **Arquitetura dual-provider**: AIBrain aceita `provider="gemini"` ou `provider="claude"`, com metodos `_call_gemini()`, `_call_claude()` e um router `_call_llm()` que direciona para o provider correto. Troca de provider e transparente para o resto do codigo.
- **Funcoes**:
  - Classificar tarefas em 4 categorias com contexto profundo
  - Resolver expressoes temporais ("amanha", "sexta", "daqui 3 dias")
  - Detectar multiplas tarefas numa mensagem
  - Analisar sobrecarga do dia (baseada em tempo estimado real)
  - Sugerir realocacao para dias mais leves
  - Gerar planejamento diario com blocos de tempo (usando dados de energia)
  - Dar feedback construtivo (tom de coach)
  - Gerar relatorio semanal com padroes
  - Aprender contexto (ex: "Carlos = Grupo Ser") via tabela `contexto_ia`
  - Decompor tarefas grandes em 3-6 subtarefas com tempo estimado
  - Detectar conflitos de horario entre reunioes antes de salvar
  - Alerta preditivo de sobrecarga para dias futuros
  - Sugerir reagendamento automatico de tarefas atrasadas
  - Planejamento por energia: cognitivas de manha, administrativas de tarde
  - Coaching personalizado: analisa padroes e gera dicas actionaveis
  - Analise de padroes melhorada: categorias, dias da semana, habitos
- **Parsing de lista semanal**: Usuario pode enviar semana inteira organizada por dia (Segunda/Terca/etc) e todas as tarefas sao detectadas
- **Deteccao de status**: "feito ja" -> concluida, "em andamento" -> em_andamento, "nao fiz" -> pendente
- **Seguranca**: Pos-processamento em Python valida datas e corrige erros da IA
- **Resiliencia**: Retry com backoff exponencial para APIs (429/503)
- **Fallback inteligente**: Se a IA falha, classificacao por keywords assume — com deteccao de multiplas tarefas por cabecalhos de dia
- **Message splitting**: Mensagens com 20+ tarefas sao divididas em blocos para respeitar o limite de 4096 caracteres do Telegram

### Calendar Sync (O Elo)

Este modulo (`bot/calendar_sync.py`) integra calendarios externos ao sistema. Funciona assim:

```
1. Usuario envia /conectar_google no Telegram
2. Bot gera URL de autorizacao OAuth2 com state assinado (HMAC)
3. Usuario clica, autoriza no Google, e redirecionado para callback
4. Bot recebe authorization code, troca por access_token + refresh_token
5. Tokens salvos na tabela 'configuracoes' do Supabase (criptografia do Supabase)
6. Job a cada 15 min: busca eventos dos proximos 7 dias via API
7. Eventos normalizados para schema unificado e salvos em 'eventos_calendario'
8. Lembretes agendados 15min antes de cada evento proximo
```

**Decisoes de arquitetura:**

- **Por que nao webhook?** O plano gratuito do Koyeb nao garante IP fixo, e webhooks do Google Calendar exigem dominio verificado. Polling a cada 15min e simples e suficiente para uso pessoal.
- **Por que httpx e nao requests?** httpx e mais moderno, suporta async (futuro), e ja e dependencia do projeto.
- **Por que salvar tokens no Supabase?** Para que o bot no Koyeb (que nao tem disco persistente) mantenha os tokens entre restarts. Alternativa seria usar variavel de ambiente, mas tokens precisam de refresh periodico.
- **Schema unificado**: Eventos do Google e Microsoft tem formatos diferentes. O modulo normaliza para um formato unico na tabela `eventos_calendario` (titulo, data_inicio, data_fim, meeting_link, etc).

**Funcionalidades:**
- Google Calendar: leitura de eventos, criacao de eventos a partir de tarefas
- Google Tasks: leitura de listas de tarefas
- Microsoft Outlook/Teams: leitura de eventos
- Deteccao automatica de links de reuniao (Meet, Teams, Zoom) nos eventos
- Refresh automatico de tokens expirados

### Sistema de Busca e Anexos

```
/buscar reuniao com Carlos
        |
        v
    Busca em paralelo:
    ├── tarefas (titulo ILIKE)
    ├── eventos_calendario (titulo ILIKE)
    ├── historico_semanal (annotation ILIKE)
    └── anexos (titulo + conteudo ILIKE)
        |
        v
    Resultados unificados com icones por tipo
```

**Indices de busca:**
- `idx_anexos_conteudo`: indice GIN com `to_tsvector('portuguese', conteudo)` — busca full-text em portugues
- `idx_tarefas_titulo_busca`: indice GIN com `to_tsvector('portuguese', titulo)` — busca em titulos de tarefas

**Tipos de anexo:**
- `texto`: notas, anotacoes manuais
- `transcricao`: audios transcritos vinculados a tarefas
- `link`: URLs com descricao
- `arquivo`: referencia a arquivos (metadata em JSONB)

### Mapeamento de Energia

```
/energia 4 manha
        |
        v
    Salva na tabela energia_diaria:
    { data: "2026-03-22", periodo: "manha", nivel: 4 }
        |
        v
    /planejar consulta energia_diaria
    e aloca tarefas cognitivas nos periodos de alta energia
```

**Periodos**: manha (6-11h), tarde (12-17h), noite (18+)
**Niveis**: 1 (exausto) a 5 (energia total)
**Constraint**: UNIQUE(data, periodo) — upsert automatico

O dashboard tambem permite registrar energia via dots clicaveis na interface.

### Supabase (A Secretaria)
- **O que e?** Um "Firebase open source" - banco de dados + API pronta + Realtime
- **Por que?**
  - Plano gratis generoso (500MB, 50k requests/mes)
  - PostgreSQL (banco robusto)
  - API REST automatica (nao precisa criar backend)
  - Realtime (dashboard atualiza sozinho via WebSocket)

### Dashboard Web (O Mural)
- **Stack**: HTML + CSS + JavaScript puro (sem frameworks)
  - Por que sem React/Vue? Simplicidade. Para um dashboard pessoal, vanilla JS e suficiente
  - Menos coisas para aprender de uma vez
  - Deploy instantaneo no GitHub Pages
- **PWA**: Manifest.json permite instalar como app nativo no celular/desktop
- **Funcionalidades**:
  - 5 views: Todas | Hoje | Semana | Revisao Semanal | KPIs
  - Filtros por categoria, prioridade e status
  - Barra de busca global (tarefas, eventos, anotacoes, anexos)
  - Calendario semanal responsivo (empilha no mobile)
  - Cards com tempo estimado, delegacao, recorrencia
  - Banner de alerta para tarefas atrasadas
  - Modal de detalhe completo
  - Edicao e exclusao com confirmacao
  - Realtime via Supabase (atualiza sem refresh)
  - Timeline vertical do dia com indicador "Agora" (view Hoje)
  - Toggle rapido de status (3 estados: pendente -> em_andamento -> concluida)
  - Acoes em lote: Shift+Click multi-selecao, concluir/excluir em massa
  - Revisao semanal: metricas, heatmap de conclusao, distribuicao por categoria
  - Modo claro/escuro com toggle e persistencia (localStorage)
  - Matriz de Eisenhower com 4 quadrantes e drag&drop
  - Pomodoro timer vinculado a tarefas (25min, play/pause/stop)
  - Mapeamento de energia (dots clicaveis por periodo)
  - Subtarefas com checklist e progresso visual

### GitHub Pages (O Endereco)
- **O que e?** Hospedagem gratuita de sites estaticos direto do GitHub
- **Custo**: Zero
- **URL**: https://wendelcastro.github.io/organizador-tarefas/web/
- **Limitacao**: Apenas arquivos estaticos — perfeito porque o Supabase faz o papel do backend

### JobQueue / APScheduler (O Relogio)
- **O que e?** Sistema de agendamento integrado ao python-telegram-bot
- **Funcao**: Executa tarefas automaticas em horarios definidos
- **Jobs programados**:
  - `resumo_matinal` — todos os dias as 7:30
  - `checkin_meiodia` — todos os dias as 13:00
  - `relatorio_semanal_auto` — sexta-feira as 17:00
  - `verificar_recorrentes` — todos os dias as 6:00
  - `sync_calendarios` — a cada 15 minutos
  - `_enviar_lembrete` — 15min antes de cada tarefa com horario
  - `enviar_lembrete_calendario` — 15min antes de cada evento sincronizado
  - `keep_alive` — ping a cada 4 minutos (anti-sleep Koyeb)

## Fluxo detalhado

### 1. Captura com IA (Telegram)
```
Wendel: [audio] "Amanha tenho reuniao com Carlos do Grupo Ser as 10h
                 e preciso corrigir as provas de IA"

Bot: Transcreve (Whisper/Groq)
  -> "amanha tenho reuniao com carlos do grupo ser as 10h
      e preciso corrigir as provas de ia"

AI Brain v2:
  1. Detecta 2 tarefas na mensagem
  2. Tarefa 1:
     - titulo: "Reuniao com Carlos"
     - categoria: Grupo Ser (detectou "Carlos" + "Grupo Ser")
     - prioridade: alta (reuniao amanha)
     - prazo: 2026-03-23 (resolveu "amanha")
     - horario: 10:00
     - tempo_estimado_min: 60
  3. Tarefa 2:
     - titulo: "Corrigir provas de IA"
     - categoria: Trabalho (detectou "provas")
     - prioridade: media
     - prazo: null (nao especificou)
     - tempo_estimado_min: 120

  4. Salva contexto: "Carlos = Grupo Ser" (para proximas vezes)
  5. Analisa sobrecarga: amanha ja tem 4 tarefas (380min)
     -> "Dia pesado (97%). Sugestao: mover provas pra quarta (32% ocupado)"

Bot responde com 2 cards + alerta de sobrecarga
Wendel confirma -> Salva no Supabase -> Dashboard atualiza em tempo real
```

### 2. Sincronizacao de Calendario
```
[A cada 15 min] Job sync_calendarios_job roda:
  1. Carrega tokens do Supabase (configuracoes)
  2. Se token expirado: refresh automatico
  3. Google Calendar API: GET /calendars/primary/events?timeMin=hoje&timeMax=+7dias
  4. Microsoft Graph: GET /me/calendarview?startDateTime=...&endDateTime=...
  5. Para cada evento:
     - Normaliza formato (titulo, data, horario, meeting_link)
     - Detecta plataforma de reuniao (Meet, Teams, Zoom)
     - Upsert na tabela eventos_calendario (UNIQUE external_id + provider)
  6. Agenda lembretes para eventos proximos (15min antes)
```

### 3. Automacoes
```
[07:30] Bot envia no Telegram:
  "Bom dia! 5 tarefas para hoje (~380min)
   + 3 eventos do calendario
   Sugestao: reagendar 2 atrasadas"

[09:45] Bot envia lembrete de evento:
  "Em 15 minutos: Reuniao com Carlos (Google Calendar)
   Entrar: https://meet.google.com/xxx"

[Sexta 17:00] Bot envia relatorio semanal:
  "Relatorio Semanal: 17/03 a 22/03
   Concluidas: 12/18 (67%)
   Trabalho: 5/7
   Coaching: priorize tempo pessoal"
```

## Modelo de dados (Supabase)

### Tabela: tarefas
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico (gerado automaticamente) |
| titulo | text | Descricao da tarefa |
| notas | text | Observacoes adicionais |
| categoria | text | Trabalho, Consultoria, Grupo Ser, Pessoal |
| prioridade | text | alta, media, baixa |
| status | text | pendente, em_andamento, concluida, cancelada |
| prazo | date | Data limite (pode ser null) |
| horario | time | Horario fixo (pode ser null) |
| meeting_link | text | Link de reuniao (Zoom, Meet, Teams) |
| meeting_platform | text | zoom, meet, teams, outro |
| google_event_id | text | ID do Google Calendar |
| origem | text | telegram, dashboard, claude_code |
| tempo_estimado_min | integer | Tempo estimado em minutos |
| tempo_gasto_min | integer | Tempo gasto real (Pomodoro tracking) |
| recorrencia | text | diaria, semanal, quinzenal, mensal |
| recorrencia_dia | integer | Dia da recorrencia |
| delegado_para | text | Nome de quem recebeu a tarefa |
| tarefa_pai_id | uuid | Referencia ao modelo de recorrencia |
| quadrante_eisenhower | text | q1 (Fazer), q2 (Agendar), q3 (Delegar), q4 (Eliminar) |
| created_at | timestamptz | Quando foi criada |
| updated_at | timestamptz | Ultima atualizacao (trigger automatico) |
| completed_at | timestamptz | Quando foi concluida (trigger automatico) |

### Tabela: subtarefas
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| tarefa_id | uuid | FK para tarefas (CASCADE on delete) |
| titulo | text | Descricao da subtarefa |
| concluida | boolean | Se esta concluida |
| ordem | integer | Ordem de exibicao |
| created_at | timestamptz | Quando foi criada |

### Tabela: eventos_calendario
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| external_id | text | ID do evento na plataforma de origem |
| provider | text | google ou microsoft |
| titulo | text | Nome do evento |
| descricao | text | Descricao do evento |
| local_evento | text | Local fisico ou virtual |
| data_inicio | timestamptz | Inicio do evento |
| data_fim | timestamptz | Fim do evento |
| dia | date | Data do evento (para queries por dia) |
| horario_inicio | text | Horario formatado (HH:MM) |
| horario_fim | text | Horario formatado (HH:MM) |
| all_day | boolean | Se e evento de dia inteiro |
| meeting_link | text | Link de reuniao (Meet, Teams, Zoom) |
| meeting_platform | text | Plataforma detectada |
| recorrente | boolean | Se faz parte de serie recorrente |
| synced_at | timestamptz | Ultima sincronizacao |
| created_at | timestamptz | Quando foi criado |

### Tabela: anexos
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| tarefa_id | uuid | FK para tarefas (opcional, CASCADE) |
| evento_id | uuid | FK para evento (opcional) |
| tipo | text | texto, transcricao, link, arquivo |
| titulo | text | Titulo do anexo |
| conteudo | text | Conteudo textual |
| url | text | URL (para tipo link/arquivo) |
| metadata | jsonb | Dados extras (tamanho, formato, etc) |
| created_at | timestamptz | Quando foi criado |

### Tabela: energia_diaria
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| data | date | Data do registro |
| periodo | text | manha, tarde ou noite |
| nivel | integer | 1 (exausto) a 5 (energia total) |
| notas | text | Observacao opcional |
| created_at | timestamptz | Quando foi criado |

### Tabela: reflexoes
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| data | date | Data da reflexao |
| pergunta | text | Pergunta reflexiva gerada pela IA |
| resposta | text | Resposta do usuario |
| created_at | timestamptz | Quando foi criada |

### Tabela: contexto_ia
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| chave | text | Identificador do contexto (ex: "pessoa_carlos") |
| valor | text | O que a IA aprendeu (ex: "Carlos esta associado a Grupo Ser") |
| tipo | text | pessoa, padrao, preferencia, geral |
| confianca | float | 0.0 a 1.0 — quao confiavel e o contexto |
| vezes_usado | integer | Quantas vezes foi usado (reforco) |
| created_at | timestamptz | Quando foi criado |
| updated_at | timestamptz | Ultima atualizacao |

### Tabela: gamificacao
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| xp_total | integer | Pontos de experiencia acumulados |
| nivel | integer | Nivel atual (1-10) |
| streak_atual | integer | Dias consecutivos produtivos |
| melhor_streak | integer | Recorde de streak |
| updated_at | timestamptz | Ultima atualizacao |

### Tabela: historico_semanal
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| week_start | date | Inicio da semana |
| metrics | jsonb | Snapshot de metricas da semana |
| annotation | text | Anotacao do usuario sobre a semana |
| created_at | timestamptz | Quando foi criado |

### Tabela: xp_log
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| tarefa_id | uuid | Tarefa que gerou o XP |
| xp_ganho | integer | Quantidade de XP |
| motivo | text | Descricao do motivo |
| created_at | timestamptz | Quando foi registrado |

### Tabela: historico
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| tarefa_id | uuid | Referencia a tarefa (sem FK — permite registro de exclusoes) |
| acao | text | criada, status_alterado, prioridade_alterada, excluida |
| detalhes | jsonb | Dados extras (titulo, de/para status, etc.) |
| created_at | timestamptz | Quando aconteceu |

### Tabela: configuracoes
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| chave | text | Nome da configuracao |
| valor | text | Valor (pode ser JSON serializado para tokens) |
| created_at | timestamptz | Quando foi criada |

### View: carga_por_dia
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| dia | date | Data |
| total_tarefas | integer | Quantidade de tarefas no dia |
| minutos_estimados | integer | Soma dos tempos estimados |
| reunioes_fixas | integer | Tarefas com horario definido |
| alta_prioridade | integer | Tarefas de prioridade alta |

## Custo total estimado

| Servico | Custo | Observacao |
|---------|-------|-----------|
| Telegram Bot API | Gratis | Sem limite |
| Supabase (plano free) | Gratis | 500MB banco, 50K requests/mes |
| GitHub Pages | Gratis | Hospedagem do dashboard |
| Groq (Whisper) | Gratis | Transcricao de audio |
| Gemini 2.5 Flash | Gratis | IA principal |
| Google Calendar API | Gratis | Sincronizacao |
| Microsoft Graph API | Gratis | Sincronizacao |
| Claude API (Sonnet) | ~R$5-15/mes | Fallback opcional |
| Koyeb (deploy bot) | Gratis | 1 instancia, 512MB RAM |
| **Total mensal estimado** | **R$0/mes** | 100% gratuito com Gemini como IA principal |

---

*Arquitetura documentada para ensino — cada decisao explicada com o porque.*
