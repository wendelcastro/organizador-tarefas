# Guia Supabase — Para Professores

> Documentacao didatica do Organizador de Tarefas

## O que e Supabase? (Analogia: A Secretaria da Escola)

Imagine uma secretaria de escola que:
- Guarda todos os documentos organizados em pastas (tabelas)
- Tem um balcao de atendimento que responde perguntas (API REST)
- Atualiza o mural automaticamente quando algo muda (Realtime)
- Tem um seguranca na porta que controla quem entra (RLS)

Isso e o Supabase. Na pratica, e um banco de dados PostgreSQL com superpoderes.

### Por que Supabase e nao Firebase?

| Supabase | Firebase |
|----------|----------|
| PostgreSQL (SQL padrao) | Firestore (NoSQL proprietario) |
| Open source | Proprietario do Google |
| Voce ja sabe SQL | Precisa aprender query syntax |
| Gratis ate 500MB | Gratis ate 1GB |
| Pode migrar facil | Lock-in do Google |

## Termos do Supabase (com analogias)

| Termo | Analogia | O que faz |
|-------|----------|-----------|
| **Tabela** | Pasta no arquivo | Guarda um tipo de dado (ex: tarefas) |
| **Row** (linha) | Ficha dentro da pasta | Um registro (ex: uma tarefa especifica) |
| **Column** (coluna) | Campo da ficha | Uma informacao (ex: titulo, prioridade) |
| **Migration** | Reforma na secretaria | Script que altera a estrutura do banco |
| **RLS** | Seguranca na porta | Regras de quem pode ver/editar o que |
| **Policy** | Cracha do funcionario | Permissao especifica (ler, escrever, etc) |
| **Trigger** | Alarme automatico | Acao que dispara quando algo muda |
| **View** | Relatorio pronto | Consulta salva que voce pode reusar |
| **Index** | Aba no fichario | Acelera buscas em colunas especificas |
| **API Key (anon)** | Chave da porta da frente | Acesso publico, limitado pelas policies |
| **API Key (service)** | Chave mestra | Acesso total, NUNCA expor no frontend |

## Nossas Tabelas (13 tabelas + 2 views)

### tarefas (a principal)
```
id                   → Identificador único (UUID)
titulo               → "Preparar aula de IA"
notas                → Observações adicionais
categoria            → "Trabalho" | "Consultoria" | "Grupo Ser" | "Pessoal"
prioridade           → "alta" | "media" | "baixa"
status               → "pendente" | "em_andamento" | "concluida" | "cancelada"
prazo                → 2026-03-18
horario              → 14:00
meeting_link         → "https://meet.google.com/..."
meeting_platform     → "zoom" | "meet" | "teams" | "outro"
google_event_id      → ID do evento no Google Calendar
origem               → "telegram" | "dashboard" | "claude_code"
tempo_estimado_min   → 120 (minutos estimados)
tempo_gasto_min      → 50 (tempo real gasto via Pomodoro)
recorrencia          → "diaria" | "semanal" | "quinzenal" | "mensal"
recorrencia_dia      → Dia da recorrência
delegado_para        → "João" (nome do delegado)
tarefa_pai_id        → UUID do modelo de recorrência
quadrante_eisenhower → "q1" | "q2" | "q3" | "q4"
created_at           → quando foi criada
updated_at           → última modificação (automático!)
completed_at         → quando foi concluída (automático!)
```

### subtarefas (checklist)
Vinculadas a uma tarefa pai. Usadas pelo `/decompor` e exibidas como checklist no dashboard.
```
id, tarefa_id (FK), titulo, concluida, ordem, created_at
```

### eventos_calendario (calendários sincronizados)
Eventos do Google Calendar e Microsoft Outlook/Teams sincronizados a cada 15 min.
```
id, external_id, provider (google|microsoft), titulo, descricao, local_evento,
data_inicio, data_fim, dia, horario_inicio, horario_fim, all_day,
meeting_link, meeting_platform, recorrente, synced_at, created_at
```

### anexos (arquivos e textos)
Textos, transcrições, links e arquivos vinculados a tarefas ou eventos. Pesquisáveis via busca full-text.
```
id, tarefa_id (FK), evento_id (FK), tipo (texto|transcricao|link|arquivo),
titulo, conteudo, url, metadata (JSONB), created_at
```

### energia_diaria (mapeamento de energia)
Nível de energia por período do dia, usado pelo `/planejar` para alocação inteligente.
```
id, data, periodo (manha|tarde|noite), nivel (1-5), notas, created_at
UNIQUE(data, periodo) — permite upsert automático
```

### gamificacao (XP e níveis)
```
id, xp_total, nivel (1-10), streak_atual, melhor_streak, updated_at
```

### xp_log (log de XP)
```
id, tarefa_id, xp_ganho, motivo, created_at
```

### historico_semanal (snapshots semanais)
```
id, week_start, metrics (JSONB), annotation (texto pesquisável), created_at
```

### reflexoes (reflexões diárias)
```
id, data, pergunta, resposta, created_at
```

### contexto_ia (memória da IA)
```
id, chave, valor, tipo (pessoa|padrao|preferencia|geral), confianca (0-1), vezes_usado, created_at, updated_at
```

### historico (o diário de bordo)
Registra AUTOMATICAMENTE toda mudança nas tarefas:
- Tarefa criada
- Status alterado (de "pendente" para "concluída")
- Prioridade alterada
- Tarefa excluída

Isso é feito por **Triggers** — funções que disparam sozinhas.

### categorias (as pastas)
As 4 categorias com suas cores. Pode adicionar mais depois.

### configuracoes (preferências)
Guarda configs como chat_id do Telegram, tokens OAuth do Google/Microsoft, fuso horário.

### Views
- `resumo_semanal` — Números agregados da semana
- `carga_por_dia` — Ocupação por dia (total tarefas, minutos estimados, reuniões, alta prioridade)

## O que e RLS? (Row Level Security)

Analogia: E como um seguranca na porta de cada pasta.

Sem RLS: qualquer um com a chave (API key) ve TUDO.
Com RLS: mesmo com a chave, so ve o que a policy permite.

No nosso caso (uso pessoal), as policies permitem tudo.
Se um dia voce quiser que outros professores usem o sistema,
basta trocar as policies para filtrar por usuario.

## O que sao Triggers?

Analogia: Alarmes automaticos.

Quando voce muda o status de uma tarefa para "concluida":
1. O trigger `atualizar_updated_at` atualiza a data de modificacao
2. O trigger `registrar_historico` anota no diario de bordo
3. Tudo automatico, sem voce precisar fazer nada

## Como a API funciona

O Supabase gera uma API REST automaticamente para cada tabela.
O dashboard web vai usar essa API assim:

```javascript
// Buscar todas as tarefas
const { data } = await supabase.from('tarefas').select('*')

// Criar nova tarefa
const { data } = await supabase.from('tarefas').insert({ titulo: '...' })

// Atualizar status
const { data } = await supabase.from('tarefas').update({ status: 'concluida' }).eq('id', '...')

// Excluir
const { data } = await supabase.from('tarefas').delete().eq('id', '...')
```

E como conversar com a secretaria:
- "Me da todas as fichas" → SELECT
- "Guarda essa ficha nova" → INSERT
- "Atualiza o status dessa ficha" → UPDATE
- "Joga essa ficha fora" → DELETE

## Realtime: O Mural que Atualiza Sozinho

O Supabase tem um recurso chamado Realtime.
Quando o bot do Telegram cria uma tarefa, o dashboard
atualiza INSTANTANEAMENTE sem precisar recarregar a pagina.

Analogia: E como um quadro de avisos digital que pisca
toda vez que alguem coloca um aviso novo.

## Seguranca: O que NUNCA fazer

1. NUNCA colocar a `service_role` key no frontend (HTML/JS)
2. NUNCA desabilitar RLS em producao
3. NUNCA commitar o `.env` com as chaves
4. A `anon` key PODE ir no frontend — ela e limitada pelas policies

## Migrations (Scripts SQL)

O banco evolui por migrations — scripts SQL executados na ordem. Cada um adiciona funcionalidades novas sem quebrar as anteriores.

| Migration | O que faz |
|-----------|-----------|
| `001_criar_tabelas.sql` | Tabelas base: tarefas, categorias, histórico, configurações |
| `002_fix_delete_trigger.sql` | Corrige FK do histórico para permitir registro de exclusões |
| `003_melhorias_inteligentes.sql` | Campos v2: tempo estimado, recorrência, delegação, contexto IA |
| `004_gamificacao_historico_habitos.sql` | Gamificação (XP, níveis, streaks), histórico semanal, hábitos |
| `005_pomodoro_reflexoes.sql` | Pomodoro tracking (tempo_gasto_min), reflexões diárias |
| `006_energy_mapping.sql` | Tabela energia_diária (manhã/tarde/noite, 1-5) |
| `007_eisenhower_quadrant.sql` | Coluna quadrante_eisenhower na tabela tarefas |
| `008_subtarefas.sql` | Tabela subtarefas (checklist vinculada a tarefas) |
| `009_eventos_calendario.sql` | Tabela eventos_calendario (sync Google/Microsoft) |
| `010_anexos_busca.sql` | Tabela anexos + índices full-text search (português GIN) |

**Analogia**: Migrations são como reformas na secretaria. Cada uma adiciona uma gaveta, um fichário ou um sistema novo — sem jogar fora o que já existia.

## Próximos passos

Depois de criar as tabelas:
1. Conectar o dashboard ao Supabase (trocar dados mock por dados reais)
2. Configurar Realtime para atualização automática
3. Conectar o Telegram Bot para inserir tarefas
