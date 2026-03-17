# Arquitetura do Organizador de Tarefas v2

> Documentacao didatica - cada decisao explicada

## Visao Geral

```
[Wendel manda audio/texto]
        |
        v
[Telegram Bot] --- transcreve audio (Whisper via Groq)
        |
        v
[AI Brain v2] --- classifica, resolve datas, detecta multiplas,
        |         analisa sobrecarga, sugere realocacao,
        |         aprende contexto (memoria)
        v
[Supabase] --- armazena tudo (PostgreSQL + Realtime)
        |
        v
[Dashboard Web] --- visualiza no navegador (GitHub Pages)

        === AUTOMACOES (rodam sozinhas via JobQueue) ===

[07:30] Resumo matinal ──> Telegram
[06:00] Tarefas recorrentes ──> Supabase
[HH:MM - 15min] Lembrete ──> Telegram
[Sexta 17:00] Relatorio semanal ──> Telegram
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
- **Modelo**: Claude Sonnet (`claude-sonnet-4-20250514`) — equilibrio entre inteligencia e custo
- **Funcoes**:
  - Classificar tarefas em 4 categorias com contexto profundo
  - Resolver expressoes temporais ("amanha", "sexta", "daqui 3 dias")
  - Detectar multiplas tarefas numa mensagem
  - Analisar sobrecarga do dia (baseada em tempo estimado real)
  - Sugerir realocacao para dias mais leves
  - Gerar planejamento diario com blocos de tempo
  - Dar feedback construtivo (tom de coach)
  - Gerar relatorio semanal com padroes
  - Aprender contexto (ex: "Carlos = Grupo Ser") via tabela `contexto_ia`
- **Seguranca**: Pos-processamento em Python valida datas e corrige erros da IA
- **Fallback**: Se Claude falha, classificacao por keywords assume

### Supabase (A Secretaria)
- **O que e?** Um "Firebase open source" - banco de dados + API pronta + Realtime
- **Por que?**
  - Plano gratis generoso (500MB, 50k requests/mes)
  - PostgreSQL (banco robusto)
  - API REST automatica (nao precisa criar backend)
  - Realtime (dashboard atualiza sozinho via WebSocket)
- **Tabelas**:
  - `tarefas` — todas as tarefas (com novos campos v2)
  - `categorias` — Trabalho, Consultoria, Grupo Ser, Pessoal
  - `historico` — log de todas as mudancas (trigger automatico)
  - `configuracoes` — chat_id, fuso horario, etc.
  - `contexto_ia` — memoria de longo prazo da IA (v2)
- **Views**:
  - `resumo_semanal` — numeros agregados
  - `carga_por_dia` — ocupacao por dia para realocacao (v2)

### Dashboard Web (O Mural)
- **Stack**: HTML + CSS + JavaScript puro (sem frameworks)
  - Por que sem React/Vue? Simplicidade. Para um dashboard pessoal, vanilla JS e suficiente
  - Menos coisas para aprender de uma vez
  - Deploy instantaneo no GitHub Pages
- **Funcionalidades**:
  - 3 views: Todas | Hoje | Semana
  - Filtros por categoria, prioridade e status
  - Calendario semanal responsivo (empilha no mobile)
  - Cards com tempo estimado, delegacao, recorrencia
  - Banner de alerta para tarefas atrasadas
  - Modal de detalhe completo
  - Edicao e exclusao com confirmacao
  - Realtime via Supabase (atualiza sem refresh)

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
  - `relatorio_semanal_auto` — sexta-feira as 17:00
  - `verificar_recorrentes` — todos os dias as 6:00
  - `_enviar_lembrete` — 15min antes de cada tarefa com horario

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
     - prazo: 2026-03-17 (resolveu "amanha")
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

### 2. Automacoes
```
[07:30] Bot envia no Telegram:
  "Bom dia! 5 tarefas para hoje (~380min)
   🔴 Reuniao com Carlos 🕐 10:00
   🔴 Aula de IA 🕐 14:00
   🟡 Corrigir provas
   🟡 Preparar slide
   ⚪ Estudar ingles
   ⚠️ 2 atrasadas"

[09:45] Bot envia lembrete:
  "Em 15 minutos: Reuniao com Carlos (Grupo Ser)
   🔗 Entrar na reuniao"

[Sexta 17:00] Bot envia relatorio semanal:
  "Relatorio Semanal: 15/03 a 20/03
   Concluidas: 12/18 (67%)
   Trabalho: 5/7 ✅
   Grupo Ser: 3/4 ✅
   Consultoria: 2/3
   Pessoal: 2/4
   Ingles: ✅ Leitura: ❌
   Sugestao: priorize tempo pessoal na proxima semana"
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
| google_event_id | text | ID do Google Calendar (futuro) |
| origem | text | telegram, dashboard, claude_code |
| **tempo_estimado_min** | **integer** | **Tempo estimado em minutos (v2)** |
| **recorrencia** | **text** | **diaria, semanal, quinzenal, mensal (v2)** |
| **recorrencia_dia** | **integer** | **Dia da recorrencia (v2)** |
| **delegado_para** | **text** | **Nome de quem recebeu a tarefa (v2)** |
| **tarefa_pai_id** | **uuid** | **Referencia ao modelo de recorrencia (v2)** |
| created_at | timestamptz | Quando foi criada |
| updated_at | timestamptz | Ultima atualizacao (trigger automatico) |
| completed_at | timestamptz | Quando foi concluida (trigger automatico) |

### Tabela: contexto_ia (v2)
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

### Tabela: historico
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| tarefa_id | uuid | Referencia a tarefa (sem FK — permite registro de exclusoes) |
| acao | text | criada, status_alterado, prioridade_alterada, excluida |
| detalhes | jsonb | Dados extras (titulo, de/para status, etc.) |
| created_at | timestamptz | Quando aconteceu |

### View: carga_por_dia (v2)
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
| Claude API (Sonnet) | ~R$0,01/tarefa | ~R$5-15/mes com uso pessoal |
| Koyeb (deploy bot) | Gratis | 1 instancia, 512MB RAM |
| **Total mensal estimado** | **~R$5-15/mes** | Apenas a Claude API tem custo |

---

*Arquitetura documentada para ensino — cada decisao explicada com o porquê.*
