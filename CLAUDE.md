# Organizador de Tarefas v3 - Config do Projeto

## Sobre
Sistema pessoal de organização de tarefas com IA inteligente.
Captura por voz/texto via Telegram, classifica com Gemini 2.5 Flash (gratuito, com Claude como fallback),
armazena no Supabase, sincroniza calendários (Google + Microsoft) e visualiza num dashboard web com
gamificação, Eisenhower, Pomodoro, busca full-text, anexos com drag & drop, mapeamento de energia,
sistema de ajuda in-app e PWA com Service Worker.

## Stack
- **Bot**: Python 3.10+ + python-telegram-bot[job-queue] + Whisper (Groq)
- **IA**: Gemini 2.5 Flash (primário, gratuito) + Claude Sonnet (fallback) — cérebro que classifica, planeja e dá feedback
- **Backend**: Supabase (PostgreSQL + API REST + Realtime + Full-Text Search com índice GIN português)
- **Frontend**: HTML/CSS/JS (vanilla) hospedado no GitHub Pages — PWA instalável com Service Worker
- **Deploy**: Koyeb (bot 24/7, Web Service com health check na porta 8000) + GitHub Pages (frontend)
- **Health Check**: http.server em thread daemon (porta 8000) — satisfaz Koyeb que exige resposta HTTP
- **Calendar Sync**: OAuth2 com Google Calendar + Microsoft Outlook/Teams (HMAC-signed state), sync a cada 15 min

## Categorias de Tarefas
- Trabalho (dar aulas, corrigir, preparar material)
- Consultoria (projetos externos de dados)
- Grupo Ser (institucional — Ser Educacional como empresa)
- Pessoal (estudos, saude, familia, projetos pessoais)

## Estrutura de Pastas
```
/bot          - Telegram Bot + AI Brain + Calendar Sync (Python)
/web          - Dashboard Web (HTML/CSS/JS single-file) + PWA (manifest + Service Worker)
/docs         - Documentação didática completa (7 guias)
/supabase     - Migrations SQL (001 a 010)
```

## Arquivos Chave
- `bot/main.py` — Ponto de entrada, handlers (23 comandos), jobs programados, health check HTTP (porta 8000), OAuth callbacks
- `bot/ai_brain.py` — Cérebro IA: dual provider (Gemini/Claude), classificação, resolução temporal, sobrecarga, múltiplas tarefas, coaching, decomposição
- `bot/calendar_sync.py` — Integração Google Calendar + Microsoft Outlook/Teams (OAuth2, sync, lembretes, criação de eventos, Google Tasks)
- `web/index.html` — Dashboard Premium (7 views, gamificação, drag&drop, Eisenhower, Pomodoro, busca com highlight, anexos com drag & drop, energia, histórico semanal, hábitos, timeline, bulk, dark/light, realtime, PWA, sistema de ajuda in-app)
- `web/manifest.json` — PWA manifest para instalação no celular/desktop
- `web/sw.js` — Service Worker para cache network-first (PWA offline)
- `Dockerfile` — Build para Koyeb (python:3.11-slim + ffmpeg, EXPOSE 8000)
- `Procfile` — Declaração de worker para PaaS

### Migrations SQL (rodar na ordem)
- `supabase/001_criar_tabelas.sql` — Tabelas base (tarefas, categorias, historico, configuracoes)
- `supabase/002_fix_delete_trigger.sql` — Fix FK do historico
- `supabase/003_melhorias_inteligentes.sql` — V2: tempo estimado, recorrencia, delegacao, contexto IA
- `supabase/004_gamificacao_historico_habitos.sql` — V3: gamificacao (XP, niveis, streaks), historico semanal, habitos
- `supabase/005_pomodoro_reflexoes.sql` — Pomodoro tracking (tempo_gasto_min), reflexoes diarias
- `supabase/006_energy_mapping.sql` — Mapeamento de energia por periodo (manha/tarde/noite)
- `supabase/007_eisenhower_quadrant.sql` — Coluna quadrante_eisenhower na tabela tarefas
- `supabase/008_subtarefas.sql` — Subtarefas/checklist vinculadas a tarefas
- `supabase/009_eventos_calendario.sql` — Tabela eventos_calendario para sync Google/Microsoft
- `supabase/010_anexos_busca.sql` — Tabela anexos + indices full-text search (portugues)

## Comandos do Bot (23 comandos)

### Tarefas
- `/start` — Boas-vindas + salva chat ID
- `/tarefas` — Lista pendentes com prioridade
- `/concluir` — Inline keyboard interativo para concluir
- `/editar` — Edita tarefa por inline keyboard + texto livre
- `/excluir` — Inline keyboard para excluir tarefa
- `/limpar` — Detecta tarefas duplicadas/similares para limpeza
- `/decompor` — Quebra tarefa grande em subtarefas com tempo estimado
- `/cancelar` — Cancela operacao atual

### Planejamento e IA
- `/planejar` — Planejamento inteligente do dia (com dados de energia)
- `/feedback` — Feedback construtivo do dia (tom de coach)
- `/resumo` — Resumo rapido com numeros
- `/relatorio` — Relatorio semanal on-demand
- `/coaching` — Dica personalizada baseada nos padroes de tarefas
- `/energia` — Registrar nivel de energia do periodo (1-5)
- `/foco` — Modo foco (silencia lembretes de baixa prioridade)

### Busca e Anexos
- `/buscar` — Busca em tarefas, eventos, anotacoes e anexos
- `/anexar` — Salvar texto/transcricao como anexo pesquisavel

### Calendario
- `/conectar_google` — Conectar Google Calendar via OAuth2
- `/conectar_microsoft` — Conectar Microsoft Teams/Outlook via OAuth2
- `/desconectar` — Desconectar um calendario (google ou microsoft)
- `/sync` — Forcar sincronizacao de todos os calendarios
- `/agenda` — Ver eventos do dia de todos os calendarios

### Diagnostico
- `/status` — Testa conexao com APIs e mostra status das variaveis de ambiente

## Supabase
- URL: (configurar em .env)
- Anon Key: (configurar em .env)

### Tabelas (18)
- `tarefas` — Todas as tarefas (com tempo estimado, recorrência, delegação, quadrante Eisenhower, tempo gasto, eh_habito)
- `tarefas_diarias_log` — Log de conclusão diária de hábitos (tarefa_id + data, UNIQUE)
- `categorias` — Trabalho, Consultoria, Grupo Ser, Pessoal
- `historico` — Log de todas as mudanças (trigger automático)
- `configuracoes` — Chat ID, fuso horário, tokens OAuth (Google/Microsoft)
- `contexto_ia` — Memória de longo prazo da IA (pessoa, padrão, preferência)
- `gamificacao` — XP total, nível, streak atual, melhor streak
- `historico_semanal` — Snapshots de métricas por semana + anotações pesquisáveis
- `xp_log` — Log detalhado de ganho de XP por tarefa
- `subtarefas` — Checklist vinculada a tarefas (título, concluída, ordem)
- `eventos_calendario` — Eventos sincronizados do Google Calendar e Outlook/Teams
- `anexos` — Textos, transcrições, links e arquivos vinculados a tarefas/eventos (com índice full-text)
- `energia_diaria` — Nível de energia por período do dia (1-5, manhã/tarde/noite)
- `reflexoes` — Reflexões diárias com pergunta e resposta
- `perfis_usuario` — Perfil com role (owner/user), status (ativo/desativado), nome, último acesso
- `usuarios_bot` — Mapeamento chat_id Telegram → user_id Supabase
- `codigos_vinculacao` — Códigos temporários para vincular Telegram à conta
- `codigos_convite` — Códigos de convite para cadastro (uso único, com validade)

### Views
- `resumo_semanal` — Números agregados da semana
- `carga_por_dia` — Ocupação por dia para análise de sobrecarga
- `habitos_streak` — Streak e feitos em 30 dias por hábito
- `admin_usuarios_resumo` — Contagem de dados por usuário (para painel admin)

### Migrations SQL (rodar na ordem)
- `supabase/001_criar_tabelas.sql` a `supabase/016_perfis_usuario.sql` — Base original
- `supabase/017_fix_rls_financas.sql` — Corrige RLS inseguro nas tabelas financeiras
- `supabase/018_habitos_log.sql` — Tabela de log diário de hábitos + coluna eh_habito
- `supabase/019_convites_admin.sql` — Sistema de convites + campos admin em perfis_usuario

### Dashboard Views (10)
- **Todas** — Lista de tarefas avulsas (hábitos ficam ocultos, default 30 dias)
- **Hoje** — Tarefas do dia + hábitos com checkbox "feito hoje" + eventos
- **Semana** — Calendário visual (com dedup contra Google Calendar)
- **Blocos** — Blocos de tempo por período (manhã/tarde/noite)
- **KPIs** — Gráficos de produtividade
- **Matriz** — Matriz de Eisenhower (urgente x importante)
- **Revisão** — Revisão semanal + heatmap 365 + rastreador de hábitos + gamificação
- **Metas** — Planejamento estratégico 2026 (só owner) + coaching IA
- **Finanças** — Saldo, gastos, orçamento, receitas pendentes, metas financeiras
- **Admin** — Painel admin (só owner): convites, usuários, ações

## Chaves API (.env) — 14 variáveis
- `TELEGRAM_BOT_TOKEN` — @BotFather (obrigatório)
- `SUPABASE_URL` — supabase.com > Settings > API (obrigatório)
- `SUPABASE_ANON_KEY` — supabase.com > Settings > API (obrigatório, usado pelo dashboard)
- `SUPABASE_SERVICE_KEY` — supabase.com > Settings > API > service_role (obrigatório para o bot com RLS)
- `BOT_USER_ID` — UUID do dono no Supabase Auth (obrigatório para o bot vincular dados ao usuário)
- `GEMINI_API_KEY` — aistudio.google.com (IA principal, gratuita)
- `ANTHROPIC_API_KEY` — console.anthropic.com (fallback, opcional)
- `GROQ_API_KEY` — console.groq.com (opcional, para áudio)
- `GOOGLE_CLIENT_ID` — console.cloud.google.com (Google Calendar OAuth)
- `GOOGLE_CLIENT_SECRET` — console.cloud.google.com (Google Calendar OAuth)
- `MICROSOFT_CLIENT_ID` — portal.azure.com (Outlook/Teams OAuth)
- `MICROSOFT_CLIENT_SECRET` — portal.azure.com (Outlook/Teams OAuth)
- `BOT_PUBLIC_URL` — URL pública do bot no Koyeb (para callbacks OAuth)
- `OAUTH_SECRET_KEY` — Chave secreta para assinar state OAuth (HMAC)

## Regras
1. Nunca commitar .env ou chaves de API
2. Documentar cada etapa para fins didaticos
3. Commits em portugues, descritivos
4. Testar localmente antes de subir
5. Ser proativo: analisar junto, antecipar problemas, pensar como product owner
6. Relatorio semanal automatico na sexta as 17h (nao domingo)
