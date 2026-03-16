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

## Nossas Tabelas

### tarefas (a principal)
```
id            → Identificador unico (UUID)
titulo        → "Preparar aula de IA"
categoria     → "Trabalho"
prioridade    → "alta" | "media" | "baixa"
status        → "pendente" | "em_andamento" | "concluida" | "cancelada"
prazo         → 2026-03-18
horario       → 14:00
meeting_link  → "https://meet.google.com/..."
meeting_platform → "zoom" | "meet" | "teams"
google_event_id → ID do evento no Google Calendar
origem        → "telegram" | "dashboard" | "claude_code"
created_at    → quando foi criada
updated_at    → ultima modificacao (automatico!)
completed_at  → quando foi concluida (automatico!)
```

### historico (o diario de bordo)
Registra AUTOMATICAMENTE toda mudanca nas tarefas:
- Tarefa criada
- Status alterado (de "pendente" para "concluida")
- Prioridade alterada
- Tarefa excluida

Isso e feito por **Triggers** — funcoes que disparam sozinhas.

### categorias (as pastas)
As 4 categorias com suas cores. Pode adicionar mais depois.

### configuracoes (preferencias)
Guarda configs como chat_id do Telegram, calendario do Google, fuso horario.

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

## Proximos passos

Depois de criar as tabelas:
1. Conectar o dashboard ao Supabase (trocar dados mock por dados reais)
2. Configurar Realtime para atualizacao automatica
3. Conectar o Telegram Bot para inserir tarefas
