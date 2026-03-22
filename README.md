# Organizador de Tarefas Inteligente v3

> Sistema pessoal de gestao de tarefas com IA que PENSA.
> Captura por voz/texto no Telegram, classifica com Gemini 2.5 Flash (gratuito),
> sincroniza Google Calendar + Outlook/Teams, armazena no Supabase
> e visualiza num dashboard web completo com gamificacao, Eisenhower, Pomodoro e PWA.

**Dashboard ao vivo**: [wendelcastro.github.io/organizador-tarefas/web](https://wendelcastro.github.io/organizador-tarefas/web/)

---

## O Que Este Projeto Faz

Voce manda um audio ou texto no Telegram dizendo:

> "Amanha tenho reuniao com Carlos do Grupo Ser as 10h e preciso corrigir as provas"

A IA:
1. **Transcreve** o audio (Whisper via Groq)
2. **Detecta 2 tarefas** na mesma mensagem
3. **Classifica** cada uma (Grupo Ser + Trabalho)
4. **Resolve "amanha"** para a data correta (ex: 2026-03-23)
5. **Analisa se o dia esta sobrecarregado** e sugere realocar
6. **Pergunta antes de salvar** — voce confirma ou ajusta
7. **Salva no banco** e o dashboard atualiza em tempo real
8. **Envia lembrete** 15min antes da reuniao
9. **Sincroniza** com seus calendarios Google e Microsoft

---

## Funcionalidades Implementadas

### IA (AI Brain v2)
- [x] Classificacao inteligente em 4 categorias (Trabalho, Consultoria, Grupo Ser, Pessoal)
- [x] Resolucao temporal robusta: "amanha", "sexta", "semana que vem", "daqui 3 dias", "dia 25/03", "fim do mes"
- [x] Dual provider: Gemini 2.5 Flash (primario, gratuito) + Claude Sonnet (fallback)
- [x] Validacao pos-IA: Python corrige se a IA errar a data
- [x] Analise de sobrecarga real (baseada em tempo estimado, nao contagem)
- [x] Sugestao de realocacao para dias mais leves
- [x] Deteccao de multiplas tarefas numa mensagem
- [x] Memoria de contexto (aprende que "Carlos = Grupo Ser")
- [x] Deteccao de delegacao ("pede pro Joao")
- [x] Deteccao de recorrencia ("toda segunda")
- [x] Analise de padroes de produtividade (categorias, dias, habitos)
- [x] Estimativa de tempo por tipo de tarefa
- [x] Decomposicao de tarefas grandes em subtarefas (`/decompor`)
- [x] Deteccao de conflitos de horario entre reunioes
- [x] Alerta preditivo de sobrecarga para dias futuros
- [x] Sugestao de reagendamento automatico de atrasadas
- [x] Planejamento por energia (cognitivas manha, admin tarde)
- [x] Coaching personalizado baseado em padroes (`/coaching`)
- [x] Retry com backoff exponencial (tolerancia a falhas da API)
- [x] Parsing de lista semanal completa (Segunda/Terca/etc com multiplas tarefas por dia)
- [x] Deteccao de status na mensagem ("feito ja" -> concluida, "em andamento", "nao fiz" -> pendente)
- [x] Fallback inteligente: mesmo sem IA, detecta multiplas tarefas por cabecalhos de dia
- [x] Splitting automatico de mensagens longas (20+ tarefas, limite 4096 chars do Telegram)

### Bot Telegram (21 comandos)
- [x] `/start` — Boas-vindas + salva chat ID
- [x] `/tarefas` — Lista pendentes com prioridade
- [x] `/planejar` — Planejamento inteligente do dia (usa dados de energia)
- [x] `/feedback` — Feedback construtivo (tom de coach)
- [x] `/resumo` — Resumo rapido com numeros
- [x] `/concluir` — Inline keyboard interativo (escolhe qual tarefa)
- [x] `/editar` — Edita tarefa por inline keyboard + texto livre
- [x] `/relatorio` — Relatorio semanal on-demand
- [x] `/foco` — Modo foco (silencia lembretes de baixa prioridade)
- [x] `/decompor` — Quebra tarefa grande em subtarefas com tempo estimado
- [x] `/coaching` — Dica personalizada da IA baseada nos seus padroes
- [x] `/energia` — Registrar nivel de energia do periodo (1-5)
- [x] `/buscar` — Busca em tarefas, eventos, anotacoes e anexos
- [x] `/anexar` — Salvar texto/transcricao como anexo pesquisavel
- [x] `/conectar_google` — Conectar Google Calendar via OAuth2
- [x] `/conectar_microsoft` — Conectar Outlook/Teams via OAuth2
- [x] `/desconectar` — Desconectar um calendario (google ou microsoft)
- [x] `/sync` — Forcar sincronizacao de calendarios
- [x] `/agenda` — Ver eventos do dia de todos os calendarios conectados
- [x] `/status` — Diagnostico: testa conexao com APIs e mostra status
- [x] `/cancelar` — Cancela operacao atual

### Automacoes (rodam sozinhas)
- [x] Resumo matinal as 7:30 no Telegram (com sugestao de reagendamento de atrasadas)
- [x] Check-in do meio-dia as 13:00 (progresso do dia)
- [x] Relatorio semanal toda sexta as 17:00
- [x] Lembretes 15min antes de tarefas com horario
- [x] Lembretes 15min antes de eventos do calendario sincronizado
- [x] Criacao automatica de tarefas recorrentes as 6:00
- [x] Alerta preditivo de sobrecarga ao adicionar tarefas
- [x] Deteccao automatica de conflitos de horario
- [x] Sync de calendarios a cada 15 minutos
- [x] Keep-alive interno: ping a cada 4 minutos para evitar sleep no free tier do Koyeb

### Dashboard Web (7 views)
- [x] 7 views: Todas | Hoje | Semana | Revisão Semanal | Matriz Eisenhower | Blocos de Tempo | KPIs
- [x] Filtros por categoria, prioridade e status
- [x] Stat cards clicáveis (Total, Pendentes, Concluídas, Atrasadas, Reuniões)
- [x] Barra de busca global com highlight e navegação (tarefas, eventos, anotações, anexos)
- [x] Calendário semanal responsivo (empilha no mobile)
- [x] Cards com tempo estimado, delegação, recorrência
- [x] Banner de alerta para tarefas atrasadas
- [x] Badge com contagem no botão "Hoje"
- [x] Modal de detalhe completo da tarefa (edição de todos os campos, subtarefas, anexos, Pomodoro)
- [x] Edição e exclusão direto no dashboard
- [x] Realtime via Supabase (atualiza sem refresh)
- [x] Design escuro, mobile-first
- [x] Modo claro/escuro com toggle e persistência (localStorage)
- [x] Anotações semanais com preview na view Hoje, badge no menu, histórico clicável e pesquisável
- [x] Upload de anexos com drag & drop de arquivos direto no modal de detalhe

### Timeline e Blocos de Tempo
- [x] Timeline vertical do dia com indicador "Agora" (view Hoje)
- [x] Blocos de tempo visual (Manhã/Tarde/Noite) na view dedicada
- [x] Toggle rápido de status (pendente -> em andamento -> concluída)
- [x] Ações em lote: Shift+Click para multi-seleção + concluir/excluir em massa

### Sistema de Ajuda In-App
- [x] Tour de onboarding para novos usuários (highlight de elementos com popup explicativo)
- [x] Botões de tooltip "?" em cada seção com explicações contextuais
- [x] Central de Ajuda completa (modal com guias organizados por funcionalidade)
- [x] Dicas contextuais por view (cada tela mostra dicas relevantes)

### Gamificacao
- [x] Sistema de XP: pontos por tarefa concluida (bonus por prazo e prioridade)
- [x] 10 niveis com titulos: "Iniciante Organizado" ate "Professor Nivel S"
- [x] Streaks: dias consecutivos com 70%+ de conclusao
- [x] Progress Ring: circulo SVG animado mostrando progresso do dia
- [x] Barra de XP com progresso para proximo nivel

### Matriz de Eisenhower
- [x] 4 quadrantes: Fazer Agora (Q1), Agendar (Q2), Delegar (Q3), Eliminar (Q4)
- [x] Auto-classificacao baseada em prazo + prioridade (com badge "auto")
- [x] Override manual: arrastar cards entre quadrantes
- [x] Persistencia no banco (coluna `quadrante_eisenhower` na tabela tarefas)

### Pomodoro Timer
- [x] Timer de 25 minutos integrado ao dashboard
- [x] Vinculado a tarefa especifica (tracking de tempo por tarefa)
- [x] Play/Pause/Stop com feedback visual
- [x] Tempo acumulado salvo por tarefa (localStorage + banco)
- [x] Coluna `tempo_gasto_min` na tabela tarefas

### Drag & Drop
- [x] Arrastar cards entre status (Pendente/Em andamento/Concluida)
- [x] Arrastar cards entre dias no calendario semanal
- [x] Arrastar cards entre quadrantes da Matriz de Eisenhower
- [x] Feedback visual durante arrasto (opacidade + borda)

### Mapeamento de Energia
- [x] Registro de energia por periodo (manha/tarde/noite, 1-5)
- [x] Via bot (`/energia 4 manha`) e dashboard (dots clicaveis)
- [x] Dados usados pelo `/planejar` para alocar tarefas cognitivas em periodos de alta energia
- [x] Tabela `energia_diaria` no Supabase

### Busca e Anexos
- [x] Busca full-text em tarefas, eventos, anotações semanais e anexos
- [x] Barra de busca no dashboard com resultados em tempo real e highlight do termo buscado
- [x] Navegação entre resultados (clique no resultado abre/navega até o item)
- [x] Anexos do tipo texto, transcrição, link ou arquivo
- [x] Upload de arquivos via drag & drop no modal de detalhe da tarefa
- [x] Índices GIN com `to_tsvector('portuguese')` para busca em português

### Integracao de Calendarios
- [x] Google Calendar: OAuth2, sync automatico, lembretes
- [x] Microsoft Outlook/Teams: OAuth2, sync automatico, lembretes
- [x] Google Tasks: leitura das listas de tarefas do Google
- [x] Sync a cada 15 minutos (job automatico)
- [x] Lembretes no Telegram 15min antes de eventos
- [x] Eventos aparecem no dashboard (timeline e calendario semanal)
- [x] Criacao de eventos no Google Calendar a partir de tarefas
- [x] Deteccao automatica de links de reuniao (Meet, Teams, Zoom)

### Subtarefas
- [x] Decomposicao de tarefas em subtarefas via `/decompor`
- [x] Checklist com progresso visual no dashboard
- [x] Tabela `subtarefas` com FK para tarefas

### Histórico Semanal e Anotações
- [x] Snapshot de cada semana salvo automaticamente ou por botão
- [x] Campo de anotação por semana ("semana puxada", "muitas entregas")
- [x] Navegação entre semanas anteriores (< >) na view Revisão
- [x] Lista de semanas passadas com métricas
- [x] Badge de notificação no menu "Revisão" quando há anotação na semana
- [x] Preview da anotação da semana na view Hoje
- [x] Histórico de anotações clicável para navegação rápida
- [x] Anotações incluídas na busca global (pesquisáveis)

### Habitos e Vida (Organizador de Vida)
- [x] Tipos de item: Tarefa, Habito, Rotina (tratamento visual diferente)
- [x] Subcategorias pessoais: Academia, Leitura, Corrida, Beach Tennis, Estudo, Meditacao, Ingles
- [x] Tracker de habitos na Revisao Semanal (grid por subcategoria)
- [x] Rotinas fixas com horarios para consistencia

### Reflexoes Diarias
- [x] Pergunta reflexiva noturna enviada pelo bot
- [x] Respostas salvas no banco (tabela `reflexoes`)

### PWA (Progressive Web App)
- [x] Manifest.json para instalação no celular/desktop
- [x] Service Worker com cache network-first (funciona offline com dados em cache)
- [x] Funciona como app nativo quando instalado
- [x] Ícone na home screen do celular

---

## Tecnologias

| Componente | Tecnologia | Funcao |
|------------|-----------|--------|
| Bot | Python 3.10+ | Logica do bot Telegram |
| Bot Framework | python-telegram-bot 22+ | Interacao com Telegram API |
| IA (primaria) | Gemini 2.5 Flash (Google) | Classificacao, planejamento, feedback, coaching (gratuito) |
| IA (fallback) | Claude API (Sonnet) | Fallback caso Gemini falhe |
| Transcricao | Groq API (Whisper) | Audio para texto |
| Banco de dados | Supabase (PostgreSQL) | Armazenamento + API REST + Realtime |
| Calendar Sync | Google Calendar API + Microsoft Graph | Sincronizacao de eventos via OAuth2 |
| HTTP Client | httpx | Chamadas HTTP para APIs externas |
| Frontend | HTML/CSS/JS (vanilla) | Dashboard single-file PWA |
| Hospedagem web | GitHub Pages | Dashboard publico gratuito |
| Agendamento | APScheduler (via PTB JobQueue) | Lembretes, resumo matinal, relatorio, sync calendarios |
| Health Check | http.server (stdlib Python) | Responde OK para PaaS (Koyeb) |
| Deploy | Koyeb (Docker) ou Oracle Cloud (systemd) | Bot rodando 24/7 gratuito |

---

## Como Rodar do Zero (Passo a Passo)

### Pre-requisitos
- Python 3.10 ou superior
- Git instalado
- Conta no Telegram
- Conta no Supabase (gratis)
- Conta no Google AI Studio (Gemini API — gratis)
- (Opcional) Conta na Anthropic (Claude API — fallback, pago)
- (Opcional) Conta no Groq (para audio — gratis)
- (Opcional) Google Cloud Console (para Google Calendar — gratis)
- (Opcional) Azure Portal (para Microsoft Calendar — gratis)
- (Opcional) ffmpeg instalado (para converter audio)

### Passo 1: Clonar o projeto

```bash
git clone https://github.com/wendelcastro/organizador-tarefas.git
cd organizador-tarefas
```

### Passo 2: Criar ambiente virtual (recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Passo 3: Instalar dependencias

```bash
pip install -r bot/requirements.txt
```

Isso instala:
- `python-telegram-bot[job-queue]` — framework do bot + agendamento
- `python-dotenv` — carrega variaveis do .env
- `httpx` — cliente HTTP para APIs (Supabase, Google, Microsoft)

### Passo 4: Criar o bot no Telegram

1. Abra o Telegram e busque `@BotFather`
2. Envie `/newbot`
3. Escolha um nome (ex: "Organizador Wendel")
4. Escolha um username (ex: `organizador_wendel_bot`)
5. Copie o **token** que o BotFather retornar (formato: `1234567890:ABCdefGHI...`)

### Passo 5: Criar projeto no Supabase

1. Acesse [supabase.com](https://supabase.com) e crie uma conta
2. Clique em **New Project**
3. Escolha organizacao, nome (ex: "organizador-tarefas"), senha do banco, regiao (South America)
4. Aguarde a criacao (~2 minutos)
5. Va em **Settings > API** e copie:
   - **Project URL** (ex: `https://abc123.supabase.co`)
   - **anon public key** (comeca com `eyJ...`)

### Passo 6: Rodar as migrations SQL

No Supabase, va em **SQL Editor** > **New query** e rode na ordem:

1. `supabase/001_criar_tabelas.sql` — Tabelas base
2. `supabase/002_fix_delete_trigger.sql` — Fix FK
3. `supabase/003_melhorias_inteligentes.sql` — Campos v2
4. `supabase/004_gamificacao_historico_habitos.sql` — Gamificacao e habitos
5. `supabase/005_pomodoro_reflexoes.sql` — Pomodoro e reflexoes
6. `supabase/006_energy_mapping.sql` — Mapeamento de energia
7. `supabase/007_eisenhower_quadrant.sql` — Matriz de Eisenhower
8. `supabase/008_subtarefas.sql` — Subtarefas/checklist
9. `supabase/009_eventos_calendario.sql` — Eventos de calendario
10. `supabase/010_anexos_busca.sql` — Anexos e busca full-text

Cada script cria tabelas, triggers, views e indices necessarios.

### Passo 7: Obter chaves de API

Voce precisa de 3 chaves obrigatorias + varias opcionais. Veja o `.env.example` para a lista completa.

**A) Token do Bot Telegram (TELEGRAM_BOT_TOKEN) — obrigatorio:**
1. Abra o Telegram e busque `@BotFather`
2. Envie `/newbot`
3. Escolha um nome e username
4. Copie o token (formato: `1234567890:ABCdefGHI...`)

**B) URL e Chave do Supabase (SUPABASE_URL + SUPABASE_ANON_KEY) — obrigatorio:**
1. Acesse [supabase.com](https://supabase.com) > seu projeto
2. Va em **Settings > API**
3. Copie a **Project URL** e a **anon public key**
4. **NAO** copie a chave "service_role"

**C) Chave do Gemini (GEMINI_API_KEY) — recomendado, gratis:**
1. Acesse [aistudio.google.com](https://aistudio.google.com)
2. Clique em **Get API Key** > **Create API Key**
3. Copie a chave (formato: `AIza...`)

**D) Chave da Claude API (ANTHROPIC_API_KEY) — opcional, fallback:**
1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Va em **Settings > API Keys** > **Create Key**
3. Copie a chave (formato: `sk-ant-api03-...`)

**E) Chave do Groq (GROQ_API_KEY) — opcional, para audio:**
1. Acesse [console.groq.com](https://console.groq.com)
2. Va em **API Keys** > **Create API Key**
3. Copie a chave (formato: `gsk_...`)

**F) Google Calendar (GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET) — opcional:**
Veja o guia completo em `docs/06-guia-integracao-calendarios.md`

**G) Microsoft Calendar (MICROSOFT_CLIENT_ID + MICROSOFT_CLIENT_SECRET) — opcional:**
Veja o guia completo em `docs/06-guia-integracao-calendarios.md`

**Resumo das chaves:**
| Variavel | Onde gerar | Custo | Obrigatorio? |
|----------|-----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | @BotFather | Gratis | Sim |
| `SUPABASE_URL` | supabase.com | Gratis | Sim |
| `SUPABASE_ANON_KEY` | supabase.com | Gratis | Sim |
| `GEMINI_API_KEY` | aistudio.google.com | Gratis | Recomendado |
| `ANTHROPIC_API_KEY` | console.anthropic.com | ~R$5-15/mes | Nao (fallback) |
| `GROQ_API_KEY` | console.groq.com | Gratis | Nao (audio) |
| `GOOGLE_CLIENT_ID` | console.cloud.google.com | Gratis | Nao (calendario) |
| `GOOGLE_CLIENT_SECRET` | console.cloud.google.com | Gratis | Nao (calendario) |
| `MICROSOFT_CLIENT_ID` | portal.azure.com | Gratis | Nao (calendario) |
| `MICROSOFT_CLIENT_SECRET` | portal.azure.com | Gratis | Nao (calendario) |
| `BOT_PUBLIC_URL` | URL do seu deploy | — | Se usar calendario |
| `OAUTH_SECRET_KEY` | Voce define | — | Se usar calendario |

### Passo 8: Configurar variaveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com seus valores (veja `.env.example` para descricao de cada variavel).

### Passo 9: Rodar o bot

```bash
python bot/main.py
```

Deve aparecer:
```
Gemini API conectada — modo inteligente v2 ativado!
Iniciando Organizador de Tarefas v2...
Modo: INTELIGENTE v2 (Gemini 2.5 Flash)
Bot v2 rodando! Mande /start no Telegram.
Jobs programados: resumo 7:30, relatorio sex 17:00, recorrentes 6:00
```

### Passo 10: Testar

1. Abra seu bot no Telegram
2. Envie `/start`
3. Envie uma mensagem: "reuniao amanha com Carlos do Grupo Ser as 14h"
4. O bot deve classificar corretamente e pedir confirmacao
5. Confirme com "ok"
6. Abra o dashboard e veja a tarefa aparecer

### Passo 11: Dashboard

**Local:** Abra `web/index.html` no navegador

**GitHub Pages (publico):**
1. Va no seu repo no GitHub > **Settings > Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, Folder: `/ (root)`
4. Save — em 2 minutos estara em `https://seu-usuario.github.io/organizador-tarefas/web/`

### Passo 12: Calendarios (opcional)

Para sincronizar Google Calendar e/ou Microsoft Outlook/Teams:
1. Siga o guia completo em `docs/06-guia-integracao-calendarios.md`
2. Configure as variaveis `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `BOT_PUBLIC_URL`, `OAUTH_SECRET_KEY` no `.env`
3. No Telegram, use `/conectar_google` ou `/conectar_microsoft`
4. Use `/sync` para forcar a primeira sincronizacao
5. Use `/agenda` para ver os eventos do dia

---

## Deploy 24/7 Gratuito

O bot para quando voce fecha o terminal. Para rodar permanentemente, veja `docs/05-deploy-24h.md`.

**Opcoes:**
- **Koyeb** (mais simples, sem Linux) — 5 minutos de setup, auto-deploy via git push
- **Oracle Cloud** (mais robusto) — VM gratuita para sempre, 30 minutos de setup

---

## Comandos do Bot

### Comandos de tarefas

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/start` | Boas-vindas e configuracao | `/start` |
| `/tarefas` | Lista todas as pendentes | `/tarefas` |
| `/concluir` | Botoes inline para escolher qual concluir | `/concluir` |
| `/editar` | Botoes inline + texto para editar campo | `/editar` |
| `/decompor` | Quebra tarefa grande em subtarefas | `/decompor` |
| `/cancelar` | Cancela qualquer operacao em andamento | `/cancelar` |

### Comandos de planejamento e IA

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/planejar` | IA monta seu dia com blocos de tempo | `/planejar` |
| `/feedback` | IA avalia seu dia (tom de coach) | `/feedback` |
| `/resumo` | Numeros rapidos (pendentes, atrasadas) | `/resumo` |
| `/relatorio` | Relatorio semanal completo | `/relatorio` |
| `/coaching` | Dica personalizada baseada nos seus padroes | `/coaching` |
| `/energia` | Registra nivel de energia de um periodo | `/energia 4 manha` |
| `/foco 2h` | Silencia lembretes por 2 horas | `/foco 1h30` |

### Comandos de busca e anexos

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/buscar` | Busca em tarefas, eventos, anotacoes e anexos | `/buscar reuniao com Carlos` |
| `/anexar` | Salva texto como anexo pesquisavel | `/anexar Notas da aula` |

### Comandos de calendario

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/conectar_google` | Conecta Google Calendar via OAuth | `/conectar_google` |
| `/conectar_microsoft` | Conecta Outlook/Teams via OAuth | `/conectar_microsoft` |
| `/desconectar` | Desconecta um calendario | `/desconectar google` |
| `/sync` | Forca sincronizacao imediata | `/sync` |
| `/agenda` | Mostra eventos do dia | `/agenda` |

### Diagnostico

| Comando | O que faz |
|---------|-----------|
| `/status` | Testa APIs e mostra status das variaveis |

### Mensagens naturais (sem comando)

| Voce manda | O que acontece |
|-----------|---------------|
| "reuniao amanha com Carlos as 10h" | Classifica, resolve data, pede confirmacao |
| "preciso corrigir provas e preparar aula" | Detecta 2 tarefas, confirma ambas |
| "pede pro Joao revisar o relatorio" | Cria tarefa delegada ao Joao |
| "toda segunda tenho reuniao de alinhamento" | Cria tarefa recorrente semanal |
| [audio] "tenho consulta medica sexta" | Transcreve + classifica + resolve "sexta" |

---

## Estrutura de Pastas

```
organizador-tarefas/
├── .env                  # Chaves de API (NUNCA vai pro Git)
├── .env.example          # Template com descricao de cada variavel
├── .gitignore            # Ignora .env, __pycache__, etc.
├── CLAUDE.md             # Instrucoes para o Claude Code
├── README.md             # Este arquivo
├── Dockerfile            # Para deploy no Koyeb
├── Procfile              # Para deploy em PaaS
│
├── bot/                  # Bot Telegram + IA + Calendar
│   ├── main.py           # Ponto de entrada, 21 handlers, jobs, health check, OAuth
│   ├── ai_brain.py       # Cerebro IA (Gemini/Claude, classificacao, coaching, decomposicao)
│   ├── calendar_sync.py  # Sync Google Calendar + Microsoft Outlook/Teams (OAuth2)
│   └── requirements.txt  # Dependencias Python (3 pacotes)
│
├── web/                  # Dashboard (GitHub Pages)
│   ├── index.html        # Single-file: HTML + CSS + JS (PWA, sistema de ajuda)
│   ├── manifest.json     # PWA manifest para instalação
│   └── sw.js             # Service Worker (cache network-first para PWA offline)
│
├── supabase/             # Scripts do banco de dados (rodar na ordem)
│   ├── 001_criar_tabelas.sql           # Tabelas base
│   ├── 002_fix_delete_trigger.sql      # Fix FK do historico
│   ├── 003_melhorias_inteligentes.sql  # Campos v2 (tempo, recorrencia, delegacao)
│   ├── 004_gamificacao_historico_habitos.sql  # Gamificacao, historico, habitos
│   ├── 005_pomodoro_reflexoes.sql      # Pomodoro tracking, reflexoes
│   ├── 006_energy_mapping.sql          # Mapeamento de energia
│   ├── 007_eisenhower_quadrant.sql     # Matriz de Eisenhower
│   ├── 008_subtarefas.sql             # Subtarefas/checklist
│   ├── 009_eventos_calendario.sql      # Eventos de calendario
│   └── 010_anexos_busca.sql           # Anexos + busca full-text
│
└── docs/                 # Documentacao didatica
    ├── 01-git-github-guia.md              # Guia de Git/GitHub
    ├── 02-arquitetura-do-projeto.md       # Arquitetura completa
    ├── 03-supabase-guia.md                # Guia do Supabase
    ├── 04-seguranca-boas-praticas.md      # Seguranca e boas praticas
    ├── 05-deploy-24h.md                   # Deploy gratuito 24/7
    ├── 06-guia-integracao-calendarios.md  # Google Calendar + Microsoft
    └── 07-guia-funcionalidades.md         # Manual do usuario completo
```

---

## Custos

| Servico | Custo | Observacao |
|---------|-------|-----------|
| Telegram Bot API | Gratis | Sem limite |
| Supabase | Gratis | 500MB banco, 50K requests/mes |
| GitHub Pages | Gratis | Hospedagem do dashboard |
| Groq (Whisper) | Gratis | Transcricao de audio |
| Gemini 2.5 Flash | Gratis | IA principal |
| Google Calendar API | Gratis | Sincronizacao de eventos |
| Microsoft Graph API | Gratis | Sincronizacao de eventos |
| Claude API (Sonnet) | ~R$5-15/mes | Fallback opcional |
| Koyeb (deploy 24/7) | Gratis | 1 instancia, 512MB RAM |
| **Total estimado** | **R$0/mes** | 100% gratuito com Gemini como IA principal |

---

## O Que Aprendi Construindo Isso

Este projeto foi construido do zero com a ajuda do Claude Code. Cada etapa ensinou conceitos reais:

### Conceitos de Programação
- **API REST**: Request/response, headers, status codes — Supabase, Gemini, Google Calendar
- **OAuth2**: Fluxo de autorização com Google e Microsoft, tokens, refresh, state CSRF com HMAC
- **Estado de conversa (State Machine)**: Bot tem 9 estados que controlam o fluxo
- **Event Delegation**: Dashboard usa listener único no container pai
- **Realtime/WebSockets**: Supabase envia atualizações sem refresh
- **PWA**: Manifest, Service Worker com cache network-first, instalação no celular
- **Full-Text Search**: Índices GIN com `to_tsvector('portuguese')` no PostgreSQL
- **Drag & Drop API**: Nativo do HTML5, incluindo upload de arquivos via drop zone
- **In-App Help System**: Tour de onboarding, tooltips contextuais, Central de Ajuda

### Conceitos de IA
- **System Prompt Engineering**: Categorias detalhadas, exemplos, regras
- **Pos-processamento**: Python valida e corrige respostas da IA
- **Contexto acumulativo**: IA aprende associacoes com o tempo
- **Dual provider**: Gemini primario + Claude fallback, router transparente
- **Retry com backoff exponencial**: Tolerancia a falhas 429/503
- **Coaching personalizado**: IA analisa padroes e gera dicas

### Conceitos de Infraestrutura
- **Git/GitHub**: Versionamento, branches, push, .gitignore
- **GitHub Pages**: Deploy automatico de sites estaticos
- **Variaveis de ambiente (.env)**: Seguranca de chaves
- **Migrations SQL**: Evolucao incremental do banco (001 a 010)
- **Docker**: Container para deploy consistente
- **Health Check HTTP**: Mini servidor para PaaS
- **Thread daemon**: Processos paralelos sem interferencia

### Conceitos de Produto
- **Mobile-first**: Dashboard projetado para celular
- **Gamificacao**: XP, niveis, streaks para motivacao
- **Matriz de Eisenhower**: Priorizacao visual com drag&drop
- **Pomodoro**: Gestao de tempo integrada
- **Mapeamento de energia**: Dados de energia influenciam planejamento
- **Busca contextual**: Full-text search em portugues
- **Integracao de calendarios**: Visao unificada de todos os compromissos

---

## Status do Projeto

| Feature | Status |
|---------|--------|
| Bot Telegram com IA (21 comandos) | Funcionando |
| Dashboard web (7 views + PWA) | Funcionando |
| Gamificação (XP, níveis, streaks) | Funcionando |
| Matriz de Eisenhower (drag&drop) | Funcionando |
| Blocos de Tempo (Manhã/Tarde/Noite) | Funcionando |
| Pomodoro Timer | Funcionando |
| Mapeamento de energia | Funcionando |
| Busca global com highlight + Anexos | Funcionando |
| Upload de anexos com drag & drop | Funcionando |
| Drag & Drop (status + calendário + Eisenhower) | Funcionando |
| Histórico semanal com anotações | Funcionando |
| Anotações: badge, preview, histórico clicável | Funcionando |
| Hábitos e rotinas de vida | Funcionando |
| Subtarefas/checklist | Funcionando |
| Resolução temporal | Funcionando |
| Múltiplas tarefas | Funcionando |
| Lembretes automáticos | Funcionando |
| Resumo matinal 7:30 | Funcionando |
| Relatório semanal sex 17h | Funcionando |
| Tarefas recorrentes | Funcionando |
| Google Calendar sync | Funcionando |
| Microsoft Outlook/Teams sync | Funcionando |
| Reflexões diárias | Funcionando |
| Coaching IA | Funcionando |
| Sistema de ajuda in-app (tour, tooltips, Central) | Funcionando |
| Service Worker (cache offline) | Funcionando |

---

*Construido com Claude Code + Gemini 2.5 Flash — cada linha de codigo explicada, cada decisao documentada.*
