# Arquitetura do Organizador de Tarefas

> Documentacao didatica - cada decisao explicada

## Visao Geral

```
[Wendel manda audio/texto]
        |
        v
[Telegram Bot] --- transcreve audio (Whisper API)
        |
        v
[Claude API] --- classifica, prioriza, sugere
        |
        v
[Supabase] --- armazena tudo (PostgreSQL)
        |
        v
[Dashboard Web] --- visualiza no navegador (GitHub Pages)
```

## Por que cada tecnologia?

### Telegram Bot (A Recepcao)
- **Por que Telegram e nao WhatsApp?**
  - WhatsApp: API oficial e paga (Meta Business), alternativas nao-oficiais = risco de bloqueio
  - Telegram: API de bots e gratuita, oficial, sem risco, suporta audio nativo
- **Linguagem**: Python (simples, muitas bibliotecas prontas)
- **Biblioteca**: `python-telegram-bot` (a mais usada, bem documentada)
- **Transcricao**: OpenAI Whisper API (converte audio em texto)

### Supabase (A Secretaria)
- **O que e?** Um "Firebase open source" - banco de dados + autenticacao + API pronta
- **Por que?**
  - Plano gratis generoso (500MB, 50k requests/mes)
  - PostgreSQL (banco robusto, o Wendel ja conhece banco de dados)
  - API REST automatica (nao precisa criar backend)
  - Realtime (dashboard atualiza sozinho)
- **Tabelas principais**:
  - `tarefas` - todas as tarefas
  - `categorias` - Trabalho, Consultoria, Grupo Ser, Pessoal
  - `historico` - log de mudancas para revisao

### Claude API (O Coordenador)
- **Funcao**: Recebe o texto da tarefa e retorna:
  - Categoria sugerida
  - Prioridade (alta/media/baixa)
  - Prazo sugerido
  - Sugestao de agrupamento com tarefas similares
- **Modelo**: claude-haiku-4-5 (rapido e barato para classificacao)

### Dashboard Web (O Mural)
- **Stack**: HTML + CSS + JavaScript puro (sem frameworks)
  - Por que sem React/Vue? Simplicidade. Para um dashboard pessoal, vanilla JS e suficiente
  - Menos coisas para aprender de uma vez
  - Deploy instantaneo no GitHub Pages
- **Funcionalidades**:
  - Visao por categoria (abas ou filtros)
  - Visao por prioridade
  - Visao semanal (calendario simples)
  - Marcar como concluida
  - Busca no historico

### GitHub Pages (O Endereco)
- **O que e?** Hospedagem gratuita de sites estaticos direto do GitHub
- **Custo**: Zero
- **URL**: https://wendelcastro.github.io/organizador-tarefas
- **Limitacao**: Apenas arquivos estaticos (HTML/CSS/JS) - perfeito para nosso caso
  porque o Supabase faz o papel do backend

## Fluxo detalhado

### 1. Captura (Telegram)
```
Wendel: [audio] "Preciso preparar a aula de IA para quarta-feira"
  Bot: Transcreve -> "Preciso preparar a aula de IA para quarta-feira"
  Claude API: {categoria: "Trabalho", prioridade: "alta", prazo: "2026-03-18"}
  Supabase: INSERT na tabela tarefas
  Bot responde: "Tarefa adicionada! Trabalho | Alta | Quarta 18/03"
```

### 2. Visualizacao (Dashboard)
```
Wendel abre o dashboard no navegador
  -> Dashboard busca tarefas do Supabase via API
  -> Mostra organizadas por categoria e prioridade
  -> Realtime: se adicionar via Telegram, aparece instantaneamente
```

### 3. Revisao Semanal (Claude Code)
```
Wendel no domingo: "me mostra o resumo da semana"
  Claude Code: busca tarefas da semana no Supabase
  -> Lista concluidas, pendentes, atrasadas
  -> Sugere priorizacao para a proxima semana
```

## Modelo de dados (Supabase)

### Tabela: tarefas
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | Identificador unico |
| titulo | text | Descricao da tarefa |
| categoria | text | Trabalho, Consultoria, Grupo Ser, Pessoal |
| prioridade | text | alta, media, baixa |
| status | text | pendente, em_andamento, concluida |
| prazo | date | Data limite (pode ser null) |
| notas | text | Observacoes adicionais |
| created_at | timestamp | Quando foi criada |
| updated_at | timestamp | Ultima atualizacao |
| origem | text | telegram, dashboard, claude_code |

## Custo total estimado

| Servico | Custo |
|---------|-------|
| Telegram Bot API | Gratis |
| Supabase (plano free) | Gratis |
| GitHub Pages | Gratis |
| Claude API (Haiku) | ~$0.01 por tarefa classificada |
| Whisper API | ~$0.006 por minuto de audio |
| **Total mensal estimado** | **< R$5/mes** (uso pessoal) |
