# Segurança, Boas Práticas e Fluxo de Trabalho com Claude Code

> Guia completo para quem está começando a construir ferramentas com IA.
> Escrito para o Professor Wendel Castro — mas útil para qualquer dev.

---

## 1. Segurança das Chaves API

### Onde estão suas chaves?

Todas as chaves ficam no arquivo `.env` na raiz do projeto:

```
📁 Organizador-tarefas/
├── .env              ← 🔐 SUAS CHAVES (só existe na SUA máquina)
├── .env.example      ← 📋 Template VAZIO (vai pro GitHub)
├── .gitignore        ← 🛡️ Lista de arquivos que o Git IGNORA
├── bot/
├── web/
└── ...
```

### O `.env` vai para o GitHub?

**NÃO.** E aqui está o porquê:

1. O arquivo `.gitignore` contém a linha `.env`
2. O Git lê esse arquivo e **ignora** tudo que está listado nele
3. Quando você faz `git push`, o `.env` **não é enviado**
4. No GitHub, ele **não existe** — quem clonar o projeto não vê suas chaves

**Analogia**: O `.gitignore` é como um segurança na porta do aeroporto.
Ele olha a lista de itens proibidos e não deixa passar. O `.env` está na lista.

### Como verificar que está seguro?

```bash
# Este comando mostra os arquivos rastreados pelo Git
git ls-files .env

# Se não retornar nada = NÃO está no Git = SEGURO ✅
# Se retornar ".env" = ESTÁ no Git = PERIGO ❌
```

No seu projeto: **retorna vazio** = suas chaves estão seguras.

### E o `.env.example`?

Esse arquivo **vai** pro GitHub, mas ele só tem o template:

```
ANTHROPIC_API_KEY=sua_chave_aqui
```

Serve para quem clonar o projeto saber quais variáveis precisa configurar,
sem ver os valores reais.

### ⚠️ O que NUNCA fazer

| ❌ Errado | ✅ Certo |
|-----------|----------|
| Colar a chave direto no código (`api_key = "sk-ant-..."`) | Usar `os.getenv("ANTHROPIC_API_KEY")` |
| Fazer commit do `.env` | Manter `.env` no `.gitignore` |
| Compartilhar chaves por mensagem/email | Usar gerenciador de segredos |
| Usar a mesma chave em dev e produção | Criar chaves separadas |

### Se vazar uma chave, o que fazer?

1. **Revogue imediatamente** no painel do serviço (Anthropic, Supabase, etc.)
2. **Gere uma nova chave**
3. **Atualize o `.env`** com a nova chave
4. Se estava no Git, use `git filter-branch` ou BFG Repo-Cleaner para limpar o histórico

---

## 2. Fluxo de Trabalho: Local vs GitHub

### "Já que o projeto está no GitHub, tem lógica fazer atualizações localmente?"

**SIM, e é exatamente assim que todo mundo faz.** O GitHub não é onde você programa — é onde você **guarda** e **compartilha** o código.

### O fluxo correto (que todo dev usa):

```
┌─────────────────┐     git push     ┌─────────────┐
│  SUA MÁQUINA    │ ───────────────► │   GITHUB     │
│  (onde você     │                  │  (backup +   │
│   programa)     │ ◄─────────────── │   vitrine)   │
│                 │     git pull     │              │
└─────────────────┘                  └──────┬───────┘
                                            │
                                    GitHub Pages
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  DASHBOARD   │
                                    │  (público)   │
                                    └──────────────┘
```

**Analogia**: O GitHub é o Google Drive do código.
Você edita o documento no seu computador e salva no Drive.
Não edita direto no Drive (até pode, mas ninguém faz).

### Na prática, seu fluxo é:

1. **Abre o Claude Code** na pasta do projeto
2. **Faz as mudanças** (com ajuda do Claude)
3. **Testa localmente** (roda o bot, abre o dashboard)
4. **Commit + Push** (salva no GitHub)
5. **Dashboard atualiza** automaticamente (GitHub Pages)

### Se quiser trabalhar de outro computador:

```bash
# Primeira vez: clonar o projeto
git clone https://github.com/wendelcastro/organizador-tarefas.git
cd organizador-tarefas

# Criar o .env (as chaves não vêm do GitHub!)
cp .env.example .env
# Editar .env e colocar suas chaves

# Instalar dependências
pip install -r bot/requirements.txt

# Pronto! Pode trabalhar normalmente
```

### Se já tem o projeto e quer atualizar:

```bash
# Puxar as mudanças mais recentes do GitHub
git pull
```

---

## 3. Como as Pessoas Usam Claude Code na Prática

### O que é o Claude Code?

É uma **CLI (linha de comando)** que roda no seu terminal.
O Claude tem acesso ao seu código, pode ler, editar, criar arquivos e rodar comandos.

**Analogia**: É como ter um programador sênior sentado do seu lado,
vendo seu código e fazendo mudanças junto com você.

### Fluxo real de trabalho com Claude Code:

```
1. Você descreve o que quer (em português!)
   "Cria um bot de Telegram que salva tarefas no Supabase"

2. Claude lê seu projeto, entende a estrutura

3. Claude escreve o código, cria arquivos, edita existentes

4. Você testa e dá feedback
   "O delete não tá funcionando"

5. Claude investiga, encontra o bug e corrige

6. Repete até ficar perfeito
```

### Boas práticas com Claude Code:

| Prática | Por quê |
|---------|---------|
| **Descreva o problema, não a solução** | "O delete não funciona" > "Muda a linha 45" |
| **Dê contexto** | "Sou professor, preciso organizar tarefas" |
| **Teste e reporte** | "Testei e apareceu esse erro: ..." |
| **Peça explicação** | "Me explica o que esse código faz" |
| **Use CLAUDE.md** | Arquivo de instruções que o Claude lê automaticamente |
| **Use memória** | Claude lembra de conversas anteriores |
| **Commit frequente** | Salve o progresso a cada feature funcional |

### O que o Claude Code NÃO deve fazer:

- ❌ Subir chaves para o GitHub
- ❌ Fazer push sem você pedir
- ❌ Deletar arquivos sem confirmação
- ❌ Guardar senhas no código

---

## 4. Chaves API — Guia Completo

### O que é uma API Key?

É uma **senha** que identifica você ao usar um serviço.
Quando seu bot chama a Claude API, a chave diz "sou o Wendel, pode me atender".

### Suas chaves atuais:

| Serviço | Variável | Para quê | Onde gerar |
|---------|----------|----------|------------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | IA que classifica tarefas | console.anthropic.com |
| Telegram | `TELEGRAM_BOT_TOKEN` | Conectar ao bot do Telegram | @BotFather no Telegram |
| Supabase | `SUPABASE_URL` + `SUPABASE_ANON_KEY` | Banco de dados | supabase.com > Settings > API |
| Groq | `GROQ_API_KEY` | Transcrição de áudio (Whisper) | console.groq.com |

### Custos:

| Serviço | Preço |
|---------|-------|
| **Claude API (Sonnet)** | ~$3/1M tokens input, ~$15/1M output. Uma tarefa gasta ~500-1000 tokens ≈ $0.001-0.003. Uso pessoal: ~$1-5/mês |
| **Telegram Bot** | Gratuito |
| **Supabase** | Gratuito (plano free: 500MB, 50K requests/mês) |
| **Groq (Whisper)** | Gratuito |
| **GitHub Pages** | Gratuito |

### Hierarquia de segurança das chaves:

```
🔴 MAIS SENSÍVEL (gasta dinheiro se vazar)
   → ANTHROPIC_API_KEY
   → Qualquer chave de LLM paga (OpenAI, Google, etc.)

🟡 SENSÍVEL (acesso a dados)
   → SUPABASE_ANON_KEY (dados do seu banco)
   → TELEGRAM_BOT_TOKEN (controle do seu bot)

🟢 MENOS SENSÍVEL
   → GROQ_API_KEY (serviço gratuito)
   → Chaves de serviços free-tier
```

---

## 5. Estrutura Recomendada de Projeto

```
📁 meu-projeto/
├── .env                  ← 🔐 Chaves (NUNCA no Git)
├── .env.example          ← 📋 Template vazio (vai pro Git)
├── .gitignore            ← 🛡️ Lista de ignorados
├── CLAUDE.md             ← 🧠 Instruções para o Claude Code
├── README.md             ← 📖 Documentação do projeto
│
├── bot/                  ← 🤖 Código do bot
│   ├── main.py
│   ├── ai_brain.py
│   └── requirements.txt
│
├── web/                  ← 🌐 Dashboard (GitHub Pages)
│   └── index.html
│
├── supabase/             ← 🗄️ Scripts do banco
│   ├── 001_criar_tabelas.sql
│   └── 002_fix_delete_trigger.sql
│
└── docs/                 ← 📚 Documentação
    ├── 01-git-github-guia.md
    ├── 02-arquitetura-do-projeto.md
    ├── 03-supabase-guia.md
    └── 04-seguranca-boas-praticas.md  ← ESTE ARQUIVO
```

---

## 6. Checklist de Segurança

Antes de fazer `git push`, confira:

- [ ] `.env` está no `.gitignore`?
- [ ] `git ls-files .env` retorna vazio?
- [ ] Nenhuma chave está hardcoded no código?
- [ ] O `.env.example` tem apenas placeholders?
- [ ] Chaves de produção são diferentes das de desenvolvimento?

---

## 7. Próximos Passos de Segurança (quando crescer)

Quando o projeto evoluir, considere:

1. **Supabase RLS com auth**: Trocar `USING (true)` por `auth.uid() = user_id`
2. **Variáveis de ambiente no servidor**: Usar Secrets do Railway/Render/Vercel
3. **Rate limiting**: Limitar chamadas à Claude API por hora
4. **Monitoramento de custos**: Configurar alertas no console.anthropic.com
5. **Backup do banco**: Ativar backups automáticos no Supabase

---

*Guia criado com Claude Code — documentando cada passo para aprender e ensinar.*
