# Organizador de Tarefas v2 - Config do Projeto

## Sobre
Sistema pessoal de organizacao de tarefas com IA inteligente.
Captura por voz/texto via Telegram, classifica com Claude API (Sonnet),
armazena no Supabase e visualiza num dashboard web.

## Stack
- **Bot**: Python 3.10+ + python-telegram-bot[job-queue] + Whisper (Groq)
- **IA**: Claude API (Sonnet) — cerebro que classifica, planeja e da feedback
- **Backend**: Supabase (PostgreSQL + API REST + Realtime)
- **Frontend**: HTML/CSS/JS (vanilla) hospedado no GitHub Pages
- **Deploy**: Koyeb (bot 24/7, Web Service com health check na porta 8000) + GitHub Pages (frontend)
- **Health Check**: http.server em thread daemon (porta 8000) — satisfaz Koyeb que exige resposta HTTP

## Categorias de Tarefas
- Trabalho (dar aulas, corrigir, preparar material)
- Consultoria (projetos externos de dados)
- Grupo Ser (institucional — Ser Educacional como empresa)
- Pessoal (estudos, saude, familia, projetos pessoais)

## Estrutura de Pastas
```
/bot          - Telegram Bot + AI Brain (Python)
/web          - Dashboard Web (HTML/CSS/JS single-file)
/docs         - Documentacao didatica completa
/supabase     - Migrations SQL (001, 002, 003)
```

## Arquivos Chave
- `bot/main.py` — Ponto de entrada, handlers, jobs programados, health check HTTP (porta 8000)
- `bot/ai_brain.py` — Cerebro IA: classificacao, resolucao temporal, sobrecarga, multiplas tarefas
- `web/index.html` — Dashboard Premium (gamificacao, drag&drop, historico semanal, habitos, timeline, bulk, dark/light, realtime)
- `supabase/003_melhorias_inteligentes.sql` — Migration v2 (tempo estimado, recorrencia, delegacao, contexto IA)
- `Dockerfile` — Build para Koyeb (python:3.11-slim + ffmpeg, EXPOSE 8000)
- `Procfile` — Declaracao de worker para PaaS
- `supabase/004_gamificacao_historico_habitos.sql` — Migration v3 (gamificacao, historico semanal, habitos)

## Comandos do Bot
/start, /tarefas, /planejar, /feedback, /resumo, /concluir, /editar, /relatorio, /foco, /decompor, /cancelar

## Supabase
- URL: (configurar em .env)
- Anon Key: (configurar em .env)
- Tabelas: tarefas, categorias, historico, configuracoes, contexto_ia, gamificacao, historico_semanal, xp_log
- Views: resumo_semanal, carga_por_dia

## Chaves API (.env)
- TELEGRAM_BOT_TOKEN — @BotFather
- SUPABASE_URL + SUPABASE_ANON_KEY — supabase.com
- ANTHROPIC_API_KEY — console.anthropic.com
- GROQ_API_KEY — console.groq.com (opcional, para audio)

## Regras
1. Nunca commitar .env ou chaves de API
2. Documentar cada etapa para fins didaticos
3. Commits em portugues, descritivos
4. Testar localmente antes de subir
5. Ser proativo: analisar junto, antecipar problemas, pensar como product owner
6. Relatorio semanal automatico na sexta as 17h (nao domingo)
