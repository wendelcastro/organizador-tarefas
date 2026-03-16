# Organizador de Tarefas - Config do Projeto

## Sobre
Sistema pessoal de organizacao de tarefas com captura por voz/texto via Telegram,
priorizacao por IA (Claude API), armazenamento no Supabase e dashboard web.

## Stack
- **Bot**: Python + python-telegram-bot + Whisper (transcricao de audio)
- **Backend**: Supabase (PostgreSQL + Auth + Realtime)
- **Frontend**: HTML/CSS/JS (vanilla) hospedado no GitHub Pages
- **IA**: Claude API (classificacao e priorizacao)
- **Deploy**: GitHub Pages (frontend) + Supabase Edge Functions ou Railway (bot)

## Categorias de Tarefas
- Trabalho (Ser Educacional)
- Consultoria
- Grupo Ser
- Pessoal

## Estrutura de Pastas
```
/bot          - Telegram Bot (Python)
/web          - Dashboard Web (HTML/CSS/JS)
/docs         - Documentacao didatica do projeto
/supabase     - Migrations e configs do Supabase
```

## Supabase
- URL: (configurar em .env)
- Anon Key: (configurar em .env)

## Telegram Bot
- Token: (configurar em .env via @BotFather)

## Regras
1. Nunca commitar .env ou chaves de API
2. Documentar cada etapa para fins didaticos
3. Commits em portugues, descritivos
4. Testar localmente antes de subir
