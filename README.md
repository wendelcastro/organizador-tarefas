# Organizador de Tarefas Inteligente v2

> Sistema pessoal de gestao de tarefas com IA que PENSA.
> Captura por voz/texto no Telegram, classifica com Claude API,
> armazena no Supabase e visualiza num dashboard web.

**Dashboard ao vivo**: [wendelcastro.github.io/organizador-tarefas/web](https://wendelcastro.github.io/organizador-tarefas/web/)

---

## O Que Este Projeto Faz

Voce manda um audio ou texto no Telegram dizendo:

> "Amanha tenho reuniao com Carlos do Grupo Ser as 10h e preciso corrigir as provas"

A IA:
1. **Transcreve** o audio (Whisper via Groq)
2. **Detecta 2 tarefas** na mesma mensagem
3. **Classifica** cada uma (Grupo Ser + Trabalho)
4. **Resolve "amanha"** para a data correta (ex: 2026-03-17)
5. **Analisa se o dia esta sobrecarregado** e sugere realocar
6. **Pergunta antes de salvar** — voce confirma ou ajusta
7. **Salva no banco** e o dashboard atualiza em tempo real
8. **Envia lembrete** 15min antes da reuniao

---

## Funcionalidades Implementadas

### IA (AI Brain v2)
- [x] Classificacao inteligente em 4 categorias (Trabalho, Consultoria, Grupo Ser, Pessoal)
- [x] Resolucao temporal robusta: "amanha", "sexta", "semana que vem", "daqui 3 dias", "dia 25/03", "fim do mes"
- [x] Validacao pos-Claude: Python corrige se a IA errar a data
- [x] Analise de sobrecarga real (baseada em tempo estimado, nao contagem)
- [x] Sugestao de realocacao para dias mais leves
- [x] Deteccao de multiplas tarefas numa mensagem
- [x] Memoria de contexto (aprende que "Carlos = Grupo Ser")
- [x] Deteccao de delegacao ("pede pro Joao")
- [x] Deteccao de recorrencia ("toda segunda")
- [x] Analise de padroes de produtividade
- [x] Estimativa de tempo por tipo de tarefa

### Bot Telegram (10 comandos)
- [x] `/start` — Boas-vindas + salva chat ID
- [x] `/tarefas` — Lista pendentes com prioridade
- [x] `/planejar` — Planejamento inteligente do dia
- [x] `/feedback` — Feedback construtivo (tom de coach)
- [x] `/resumo` — Resumo rapido com numeros
- [x] `/concluir` — Inline keyboard interativo (escolhe qual tarefa)
- [x] `/editar` — Edita tarefa por inline keyboard + texto livre
- [x] `/relatorio` — Relatorio semanal on-demand
- [x] `/foco` — Modo foco (silencia lembretes de baixa prioridade)
- [x] `/cancelar` — Cancela operacao atual

### Automacoes (rodam sozinhas)
- [x] Resumo matinal as 7:30 no Telegram
- [x] Relatorio semanal toda sexta as 17:00
- [x] Lembretes 15min antes de tarefas com horario
- [x] Criacao automatica de tarefas recorrentes as 6:00

### Dashboard Web
- [x] Tres views: Todas | Hoje | Semana
- [x] Filtros por categoria, prioridade e status
- [x] Calendario semanal responsivo (empilha no mobile)
- [x] Cards com tempo estimado, delegacao, recorrencia
- [x] Banner de alerta para tarefas atrasadas
- [x] Badge com contagem no botao "Hoje"
- [x] Modal de detalhe completo da tarefa
- [x] Edicao e exclusao direto no dashboard
- [x] Realtime via Supabase (atualiza sem refresh)
- [x] Design escuro, mobile-first

---

## Tecnologias

| Componente | Tecnologia | Funcao |
|------------|-----------|--------|
| Bot | Python 3.10+ | Logica do bot Telegram |
| Bot Framework | python-telegram-bot 22+ | Interacao com Telegram API |
| IA | Claude API (Sonnet) | Classificacao, planejamento, feedback |
| Transcricao | Groq API (Whisper) | Audio para texto |
| Banco de dados | Supabase (PostgreSQL) | Armazenamento + API REST + Realtime |
| Frontend | HTML/CSS/JS (vanilla) | Dashboard single-file |
| Hospedagem web | GitHub Pages | Dashboard publico gratuito |
| Agendamento | APScheduler (via PTB JobQueue) | Lembretes, resumo matinal, relatorio |

---

## Como Rodar do Zero (Passo a Passo)

### Pre-requisitos
- Python 3.10 ou superior
- Git instalado
- Conta no Telegram
- Conta no Supabase (gratis)
- Conta na Anthropic (Claude API)
- (Opcional) Conta no Groq (para audio — gratis)
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
- `httpx` — cliente HTTP para APIs

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

1. Cole o conteudo de `supabase/001_criar_tabelas.sql` e clique **Run**
2. Cole o conteudo de `supabase/002_fix_delete_trigger.sql` e clique **Run**
3. Cole o conteudo de `supabase/003_melhorias_inteligentes.sql` e clique **Run**

Cada script cria tabelas, triggers e views necessarias.

### Passo 7: Obter chaves de API

**Claude API (obrigatorio para modo inteligente):**
1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma conta e adicione creditos ($5 minimo)
3. Va em **API Keys** > **Create Key**
4. Copie a chave (formato: `sk-ant-api03-...`)

**Groq API (opcional — para transcricao de audio):**
1. Acesse [console.groq.com](https://console.groq.com)
2. Crie uma conta (gratis)
3. Va em **API Keys** > **Create API Key**
4. Copie a chave

### Passo 8: Configurar variaveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com seus valores:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqr
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
ANTHROPIC_API_KEY=sk-ant-api03-...
GROQ_API_KEY=gsk_...
```

### Passo 9: Rodar o bot

```bash
python bot/main.py
```

Deve aparecer:
```
Claude API conectada — modo inteligente v2 ativado!
Iniciando Organizador de Tarefas v2...
Modo: INTELIGENTE v2 (Claude)
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

---

## Deploy 24/7 Gratuito

O bot para quando voce fecha o terminal. Para rodar permanentemente, use uma das opcoes abaixo.

### Opcao A: Koyeb (mais simples — sem Linux)

Koyeb e uma plataforma de deploy que oferece **1 instancia gratuita** (512MB RAM, 0.1 vCPU).

1. Crie conta em [koyeb.com](https://www.koyeb.com) (nao precisa de cartao)
2. Clique em **Create Service > Web Service**
3. Conecte ao seu GitHub e selecione o repositorio
4. Configure:
   - **Builder**: Dockerfile
   - **Instance type**: Free
   - **Region**: Frankfurt ou Washington
5. Adicione as variaveis de ambiente (mesmas do .env):
   - `TELEGRAM_BOT_TOKEN`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `ANTHROPIC_API_KEY`
   - `GROQ_API_KEY`
6. Clique **Deploy**
7. Pronto! O bot roda 24/7 e reinicia automaticamente se cair.

O projeto ja inclui um `Dockerfile` pronto para o Koyeb.

### Opcao B: Oracle Cloud Always Free (mais robusto)

Oracle oferece **VMs gratuitas para sempre** (ate 4 CPUs ARM, 24GB RAM).

1. Crie conta em [cloud.oracle.com](https://cloud.oracle.com/free)
2. Va em **Compute > Instances > Create Instance**
3. Selecione **Ampere A1** (ARM) — Shape: VM.Standard.A1.Flex
4. Escolha Ubuntu 22.04, 1 OCPU, 6GB RAM
5. Baixe a chave SSH e crie a instancia
6. Conecte via SSH:
```bash
ssh -i sua_chave.key ubuntu@IP_DA_INSTANCIA
```
7. Instale Python e dependencias:
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```
8. Clone o projeto:
```bash
git clone https://github.com/wendelcastro/organizador-tarefas.git
cd organizador-tarefas
python3 -m venv venv
source venv/bin/activate
pip install -r bot/requirements.txt
```
9. Crie o .env:
```bash
cp .env.example .env
nano .env  # preencha com suas chaves
```
10. Crie um servico systemd (roda 24/7 e reinicia sozinho):
```bash
sudo tee /etc/systemd/system/organizador-bot.service << 'EOF'
[Unit]
Description=Organizador de Tarefas Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/organizador-tarefas
ExecStart=/home/ubuntu/organizador-tarefas/venv/bin/python bot/main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/organizador-tarefas/.env

[Install]
WantedBy=multi-user.target
EOF
```
11. Ative e inicie:
```bash
sudo systemctl daemon-reload
sudo systemctl enable organizador-bot
sudo systemctl start organizador-bot
```
12. Verifique:
```bash
sudo systemctl status organizador-bot
# Deve mostrar "active (running)"
```

O bot agora roda permanentemente, reinicia se cair, e sobrevive a reboots.

---

## Comandos do Bot

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/start` | Boas-vindas e configuracao | `/start` |
| `/tarefas` | Lista todas as pendentes | `/tarefas` |
| `/planejar` | IA monta seu dia com blocos de tempo | `/planejar` |
| `/feedback` | IA avalia seu dia (tom de coach) | `/feedback` |
| `/resumo` | Numeros rapidos (pendentes, atrasadas) | `/resumo` |
| `/concluir` | Botoes inline para escolher qual concluir | `/concluir` |
| `/editar` | Botoes inline + texto para editar campo | `/editar` |
| `/relatorio` | Relatorio semanal completo | `/relatorio` |
| `/foco 2h` | Silencia lembretes por 2 horas | `/foco 1h30` |
| `/cancelar` | Cancela qualquer operacao em andamento | `/cancelar` |

**Mensagens naturais (sem comando):**

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
├── .env.example          # Template vazio (vai pro Git)
├── .gitignore            # Ignora .env, __pycache__, etc.
├── CLAUDE.md             # Instrucoes para o Claude Code
├── README.md             # Este arquivo
├── Dockerfile            # Para deploy no Koyeb
├── Procfile              # Para deploy em PaaS
│
├── bot/                  # Bot Telegram + IA
│   ├── main.py           # Ponto de entrada, handlers, jobs programados
│   ├── ai_brain.py       # Cerebro IA (Claude API, resolucao temporal, sobrecarga)
│   └── requirements.txt  # Dependencias Python
│
├── web/                  # Dashboard (GitHub Pages)
│   └── index.html        # Single-file: HTML + CSS + JS
│
├── supabase/             # Scripts do banco de dados
│   ├── 001_criar_tabelas.sql        # Tabelas, triggers, views
│   ├── 002_fix_delete_trigger.sql   # Fix da FK do historico
│   └── 003_melhorias_inteligentes.sql # Novos campos v2
│
└── docs/                 # Documentacao didatica
    ├── 01-git-github-guia.md
    ├── 02-arquitetura-do-projeto.md
    ├── 03-supabase-guia.md
    ├── 04-seguranca-boas-praticas.md
    └── 05-deploy-24h.md
```

---

## Custos

| Servico | Custo | Observacao |
|---------|-------|-----------|
| Telegram Bot API | Gratis | Sem limite |
| Supabase | Gratis | 500MB banco, 50K requests/mes |
| GitHub Pages | Gratis | Hospedagem do dashboard |
| Groq (Whisper) | Gratis | Transcricao de audio |
| Claude API (Sonnet) | ~R$0,01/tarefa | ~R$5-15/mes com uso pessoal |
| Koyeb (deploy) | Gratis | 1 instancia, 512MB RAM |
| **Total estimado** | **~R$5-15/mes** | Apenas a Claude API tem custo |

---

## O Que Aprendi Construindo Isso

Este projeto foi construido do zero com a ajuda do Claude Code. Cada etapa ensinou conceitos reais:

### Conceitos de Programacao
- **API REST**: Como funciona request/response, headers, status codes — usado no Supabase e Claude API
- **Estado de conversa (State Machine)**: Bot tem estados (idle, confirming, editing, chatting) que controlam o fluxo
- **Event Delegation**: Dashboard usa um unico listener no container pai em vez de onclick em cada botao
- **Realtime/WebSockets**: Supabase envia atualizacoes para o dashboard sem precisar recarregar

### Conceitos de IA
- **System Prompt Engineering**: Escrito com categorias detalhadas, exemplos, regras de classificacao
- **Pos-processamento**: Python valida e corrige o que a IA retorna (datas, categorias)
- **Contexto acumulativo**: IA aprende associacoes (pessoa + categoria) para melhorar com o tempo
- **Fallback gracioso**: Se a IA falha, classificacao por keywords assume

### Conceitos de Infraestrutura
- **Git/GitHub**: Versionamento, branches, push, pull, .gitignore
- **GitHub Pages**: Deploy automatico de sites estaticos
- **Variaveis de ambiente (.env)**: Seguranca de chaves de API
- **Migrations SQL**: Evolucao incremental do banco de dados (001, 002, 003)
- **Triggers e Views**: Automatizacao no banco (historico, resumo)
- **Deploy 24/7**: Systemd services, Docker, PaaS

### Conceitos de Produto
- **Mobile-first**: Dashboard projetado para celular primeiro
- **Confirmacao antes de salvar**: IA nunca salva sem aprovacao do usuario
- **Sobrecarga mental**: Sistema protege tempo pessoal (ingles, leitura)
- **Feedback sem julgamento**: Tom de coach, nao de chefe

---

## Status do Projeto

| Feature | Status |
|---------|--------|
| Bot Telegram com IA | Funcionando |
| Dashboard web | Funcionando |
| Resolucao temporal | Funcionando |
| Multiplas tarefas | Funcionando |
| Lembretes automaticos | Funcionando |
| Resumo matinal 7:30 | Funcionando |
| Relatorio semanal sex 17h | Funcionando |
| Tarefas recorrentes | Funcionando |
| Google Calendar sync | Planejado |
| Notificacoes push no dashboard | Planejado |

---

*Construido com Claude Code — cada linha de codigo explicada, cada decisao documentada.*
