# Guia Git + GitHub + Claude Code - Para Professores

> Por Wendel Castro - Aprendendo na pratica com Claude Code

## O que e Git? (Analogia: Caderno de Controle)

Imagine que voce esta escrevendo um livro. O Git e como ter um caderno magico que:
- Salva CADA versao do seu livro automaticamente
- Permite voltar para qualquer versao anterior
- Permite que varias pessoas escrevam ao mesmo tempo sem bagunca

### Termos essenciais (com analogias)

| Termo | Analogia | O que faz |
|-------|----------|-----------|
| `git init` | Comprar o caderno | Cria o controle de versao na pasta |
| `git add` | Marcar paginas para revisar | Seleciona arquivos para o proximo "save" |
| `git commit` | Carimbar e assinar | Salva oficialmente as mudancas com uma descricao |
| `git status` | Olhar o caderno | Ve o que mudou, o que esta marcado, o que falta |
| `git log` | Folhear o historico | Ve todos os "saves" anteriores |
| `git push` | Enviar para a biblioteca | Manda suas mudancas para o GitHub (nuvem) |
| `git pull` | Buscar na biblioteca | Pega mudancas que estao no GitHub |
| `git clone` | Fotocopiar o livro | Copia um projeto do GitHub para sua maquina |
| `git branch` | Abrir um rascunho | Cria uma versao paralela para testar algo |
| `git merge` | Juntar os rascunhos | Une o rascunho de volta ao livro principal |
| `.gitignore` | Lista de "nao copiar" | Arquivos que o Git deve ignorar (senhas, etc) |

## O que e GitHub? (Analogia: Biblioteca Central)

- Git = ferramenta local no seu computador
- GitHub = servico na nuvem onde voce guarda seus projetos

Pense assim:
- **Git** e o Word (trabalha local)
- **GitHub** e o Google Drive (sincroniza na nuvem)

### GitHub Pages (Analogia: Mural publico)

O GitHub Pages transforma seu repositorio em um site acessivel pela internet.
E como pegar seu trabalho da biblioteca e colocar num mural para todos verem.

- Gratuito para projetos publicos
- URL fica: `https://seuusuario.github.io/nome-do-projeto`
- Perfeito para dashboards, portfolios, documentacao

## Fluxo basico no dia a dia

```
1. Voce edita arquivos (escreve o livro)
2. git add arquivo.txt     (marca as paginas)
3. git commit -m "descricao" (carimba e salva)
4. git push                 (envia pra biblioteca)
```

## Comandos no Claude Code

No Claude Code, voce nao precisa digitar esses comandos manualmente!
O Claude faz pra voce. Basta pedir:

- "faz um commit com as mudancas" -> ele roda git add + git commit
- "sobe pro GitHub" -> ele roda git push
- "cria uma branch para testar X" -> ele roda git branch + git checkout
- "mostra o que mudou" -> ele roda git status + git diff

### Comandos uteis do Claude Code

| Voce diz | O que acontece |
|----------|---------------|
| "commit" ou /commit | Claude analisa mudancas e faz o commit |
| "cria um PR" | Claude cria Pull Request no GitHub |
| "mostra o status do git" | Claude roda git status |

## Como conectar ao GitHub (passo a passo)

### Passo 1: Criar repositorio no GitHub
1. Acesse github.com e faca login
2. Clique em "New repository" (botao verde)
3. Nome: `organizador-tarefas`
4. Deixe publico (para GitHub Pages funcionar gratis)
5. NAO marque "Initialize with README" (ja temos arquivos)
6. Clique "Create repository"

### Passo 2: Conectar local ao GitHub
O GitHub vai mostrar comandos. No Claude Code, peca:
"conecta esse projeto ao meu repositorio do GitHub"

Ele vai rodar algo como:
```bash
git remote add origin https://github.com/SEU_USUARIO/organizador-tarefas.git
git branch -M main
git push -u origin main
```

### Passo 3: Ativar GitHub Pages (para o dashboard)
1. No GitHub, va em Settings > Pages
2. Source: "Deploy from a branch"
3. Branch: main, pasta: /web (ou /docs)
4. Salve e aguarde ~2 minutos

Pronto! Seu dashboard estara em:
`https://seuusuario.github.io/organizador-tarefas`

## Sobre o Antigravity (Project IDX / Google)

O Project IDX (antigo Antigravity) e um IDE online do Google.
Voce pode usa-lo para visualizar o projeto em tempo real no navegador.
Porem, para este projeto, recomendo usar o **GitHub + Claude Code** localmente
e abrir o dashboard via GitHub Pages - e mais simples e direto.

Se quiser usar o IDX para preview ao vivo enquanto desenvolve, ele aceita
importar projetos do GitHub diretamente.

## Estrutura atual do projeto no GitHub

```
organizador-tarefas/
├── .env.example          <- Template de variáveis (12 variáveis)
├── .gitignore            <- Ignora .env, __pycache__, etc.
├── CLAUDE.md             <- Instruções para o Claude Code
├── README.md             <- Documentação completa do projeto
├── Dockerfile            <- Build para Koyeb
├── Procfile              <- Declaração de worker para PaaS
├── bot/                  <- Bot Telegram + IA + Calendar (3 arquivos Python)
├── web/                  <- Dashboard PWA (index.html + manifest + sw.js)
├── supabase/             <- 10 migrations SQL (001 a 010)
└── docs/                 <- 7 guias didáticos
```

## Próximos passos

- [ ] Criar conta no GitHub (se ainda não tem)
- [ ] Criar o repositório `organizador-tarefas`
- [ ] Fazer o primeiro commit e push
- [ ] Ativar GitHub Pages
