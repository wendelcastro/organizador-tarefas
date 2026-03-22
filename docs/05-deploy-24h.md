# Deploy 24/7 Gratuito — Guia Completo

> Como manter o bot do Telegram rodando permanentemente sem pagar nada.

---

## O Problema

Quando voce roda `python bot/main.py` no seu computador, o bot funciona.
Mas quando fecha o terminal ou desliga o PC, ele para.

Para um assistente pessoal que envia lembretes e resumos automaticos, precisa rodar 24/7.

---

## Opcao A: Koyeb (Mais Simples)

**O que e?** Plataforma de deploy que roda seu codigo na nuvem.
**Custo?** Gratis — 1 instancia, 512MB RAM, 0.1 vCPU.
**Precisa de Linux?** Nao. Tudo pelo navegador.

### Detalhe tecnico: Health Check

O plano gratuito do Koyeb so oferece **Web Service** (nao Worker). Isso significa que o Koyeb
faz health checks periodicos numa porta HTTP — se nao responder, ele acha que o servico caiu.

**Solucao implementada**: O bot inclui um mini servidor HTTP integrado (5 linhas de codigo)
que roda em paralelo na porta 8000 e responde "OK" para os health checks. Assim o Koyeb fica
satisfeito e o bot continua rodando normalmente.

O codigo relevante no `bot/main.py`:
```python
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Organizador de Tarefas v2 rodando")

def start_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
```

Esse servidor:
- Usa apenas a **biblioteca padrao** do Python (`http.server`, `threading`) — zero dependencias extras
- Roda numa **thread separada** (daemon) — nao interfere no bot
- Le a porta da variavel `PORT` (que o Koyeb define automaticamente)
- Logs silenciados para nao poluir a saida

### Passo a Passo

#### 0. Pre-requisitos (antes de deployar)

**IMPORTANTE**: Antes de subir o bot no Koyeb:

1. **Pare o bot local** — se voce tem `python bot/main.py` rodando no PC, pare com `Ctrl+C`.
   Dois bots NAO podem usar o mesmo token ao mesmo tempo.

2. **Rode as migrations SQL** — no Supabase > SQL Editor, execute na ordem:
   - `supabase/001_criar_tabelas.sql` — Tabelas base
   - `supabase/002_fix_delete_trigger.sql` — Fix FK
   - `supabase/003_melhorias_inteligentes.sql` — Campos v2
   - `supabase/004_gamificacao_historico_habitos.sql` — Gamificação
   - `supabase/005_pomodoro_reflexoes.sql` — Pomodoro e reflexões
   - `supabase/006_energy_mapping.sql` — Energia
   - `supabase/007_eisenhower_quadrant.sql` — Matriz Eisenhower
   - `supabase/008_subtarefas.sql` — Subtarefas
   - `supabase/009_eventos_calendario.sql` — Eventos calendário
   - `supabase/010_anexos_busca.sql` — Anexos e busca full-text

3. **Commit e push** — o Koyeb puxa o codigo do GitHub, entao tudo precisa estar no repo:
   ```bash
   git add -A
   git commit -m "preparar para deploy no Koyeb"
   git push
   ```

#### 1. Criar conta
- Acesse [koyeb.com](https://www.koyeb.com)
- Crie conta com GitHub (mais facil)
- Nao precisa de cartao de credito

#### 2. Preparar o projeto
O projeto ja inclui um `Dockerfile` na raiz com tudo pronto:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt
COPY bot/ ./bot/
EXPOSE 8000
CMD ["python", "bot/main.py"]
```

O `EXPOSE 8000` declara a porta do health check para o Koyeb.

#### 3. Criar o servico
1. No painel do Koyeb, clique **Create Service**
2. Selecione **GitHub** como source
3. Autorize o Koyeb a acessar seu GitHub (se ainda nao fez)
4. Selecione o repositorio `organizador-tarefas`
5. Branch: `main`
6. Builder: **Dockerfile** (ele detecta automaticamente)
7. Instance type: **Free**
8. Region: **Washington DC** ou **Frankfurt**

#### 4. Configurar variaveis de ambiente
Na secao "Environment variables", adicione cada uma:

| Variável | Onde pegar | Exemplo |
|----------|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | @BotFather no Telegram | `1234567890:ABCdef...` |
| `SUPABASE_URL` | Supabase > Settings > API > Project URL | `https://abc123.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase > Settings > API > anon public | `eyJhbGci...` |
| `GEMINI_API_KEY` | aistudio.google.com > Get API Key | `AIza...` |
| `ANTHROPIC_API_KEY` | console.anthropic.com > API Keys (opcional) | `sk-ant-api03-...` |
| `GROQ_API_KEY` | console.groq.com > API Keys (opcional) | `gsk_...` |
| `GOOGLE_CLIENT_ID` | console.cloud.google.com (opcional) | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | console.cloud.google.com (opcional) | `GOCSPX-...` |
| `MICROSOFT_CLIENT_ID` | portal.azure.com (opcional) | `a1b2c3d4-...` |
| `MICROSOFT_CLIENT_SECRET` | portal.azure.com (opcional) | `secret...` |
| `BOT_PUBLIC_URL` | URL do deploy no Koyeb (se usar calendário) | `https://seu-app.koyeb.app` |
| `OAUTH_SECRET_KEY` | Você define (se usar calendário) | `chave-secreta-aleatoria` |

**IMPORTANTE**: As variaveis ficam criptografadas no Koyeb. Ninguem ve.

A variavel `PORT` e definida automaticamente pelo Koyeb (geralmente 8000).

#### 5. Configurar porta
- Na configuracao do servico, garanta que a porta HTTP esta como **8000**
- Essa e a porta do health check — o bot responde "OK" nela

#### 6. Deploy
- Clique **Deploy**
- Aguarde 2-3 minutos para build e startup
- Nos **Logs**, procure essas mensagens (nesta ordem):
  ```
  Health check server rodando na porta 8000
  Gemini API conectada — modo inteligente v2 ativado!
  Iniciando Organizador de Tarefas v2...
  Modo: INTELIGENTE v2 (Gemini 2.5 Flash)
  Bot v2 rodando! Mande /start no Telegram.
  Jobs programados: resumo 7:30, relatorio sex 17:00, recorrentes 6:00
  ```

#### 7. Testar
- Abra o Telegram e envie `/start` para o bot
- Se responder, esta tudo funcionando na nuvem!

#### 8. Pronto!
O bot agora:
- Roda 24/7 na nuvem (você pode desligar o PC)
- Reinicia automaticamente se cair
- Atualiza sozinho quando você faz `git push` no GitHub
- Health check responde "OK" para o Koyeb na porta 8000
- Envia resumo matinal às 7:30
- Check-in do meio-dia às 13:00
- Envia relatório toda sexta às 17h
- Envia lembretes 15min antes de reuniões e eventos do calendário
- Cria tarefas recorrentes às 6:00
- Sincroniza calendários a cada 15 minutos
- Keep-alive a cada 4 minutos (evita sleep no free tier)

### Atualizacao automatica

Quando voce faz `git push` no GitHub, o Koyeb automaticamente:
1. Detecta a mudanca
2. Faz novo build do Docker
3. Substitui o container antigo pelo novo
4. Zero downtime (o bot continua rodando durante o deploy)

### Troubleshooting Koyeb

| Problema | Solucao |
|----------|---------|
| Build falhou | Verifique se `Dockerfile` e `bot/requirements.txt` estao no repo |
| Bot nao responde | Confira as variaveis de ambiente no painel |
| Health check falhando | Verifique se a porta no Koyeb esta como 8000 |
| Erro de conexao | Verifique SUPABASE_URL (deve comecar com `https://`) |
| Audio nao funciona | GROQ_API_KEY pode estar vazia. Confira. |
| Bot duplicado | Mate o bot local antes de deployar na nuvem |
| "Unhealthy" mas bot funciona | Pode ser timeout de rede. Espere 1-2 minutos. |

---

## Opcao B: Oracle Cloud Always Free (Mais Robusto)

**O que e?** Servidor virtual (VM) gratuito para sempre da Oracle.
**Custo?** Gratis — ate 4 CPUs ARM, 24GB RAM (muito mais que o necessario).
**Precisa de Linux?** Sim, acesso via SSH (terminal).

### Passo a Passo

#### 1. Criar conta Oracle Cloud
- Acesse [cloud.oracle.com/free](https://cloud.oracle.com/free)
- Crie conta (pode pedir cartao para verificacao, mas NAO cobra)
- Selecione sua Home Region (mais proximo de voce)

#### 2. Criar a VM
1. No painel, va em **Compute > Instances > Create Instance**
2. Name: `bot-organizador`
3. Image: **Ubuntu 22.04** (Canonical)
4. Shape: **VM.Standard.A1.Flex** (Ampere ARM — Always Free eligible)
5. OCPU: 1, Memory: 6 GB
6. Networking: aceite os padroes (VCN automatica)
7. SSH Key: **Generate a key pair** e baixe a chave privada (.key)
8. Clique **Create**
9. Aguarde ~2 minutos ate o status ficar "Running"
10. Copie o **Public IP Address**

#### 3. Conectar via SSH

```bash
# Windows (Git Bash ou PowerShell)
ssh -i caminho/para/sua-chave.key ubuntu@SEU_IP

# Se der erro de permissao na chave:
chmod 400 caminho/para/sua-chave.key
```

#### 4. Instalar dependencias no servidor

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

#### 5. Clonar e configurar o projeto

```bash
git clone https://github.com/wendelcastro/organizador-tarefas.git
cd organizador-tarefas

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r bot/requirements.txt
```

#### 6. Criar o .env

```bash
cp .env.example .env
nano .env
```

Preencha com suas chaves. Para salvar no nano: `Ctrl+O`, `Enter`, `Ctrl+X`.

#### 7. Testar manualmente

```bash
python bot/main.py
```

Se aparecer "Bot v2 rodando!", esta funcionando. Pare com `Ctrl+C`.

#### 8. Criar servico systemd (roda 24/7)

```bash
sudo tee /etc/systemd/system/organizador-bot.service << 'EOF'
[Unit]
Description=Organizador de Tarefas Bot v2
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

#### 9. Ativar e iniciar

```bash
sudo systemctl daemon-reload
sudo systemctl enable organizador-bot
sudo systemctl start organizador-bot
```

#### 10. Verificar

```bash
# Ver status
sudo systemctl status organizador-bot

# Ver logs em tempo real
sudo journalctl -u organizador-bot -f

# Parar
sudo systemctl stop organizador-bot

# Reiniciar
sudo systemctl restart organizador-bot
```

#### 11. Atualizar o codigo (quando fizer mudancas)

```bash
cd /home/ubuntu/organizador-tarefas
git pull
sudo systemctl restart organizador-bot
```

### Troubleshooting Oracle Cloud

| Problema | Solucao |
|----------|---------|
| Nao consigo criar VM A1 | A1 Flex pode estar esgotado na regiao. Tente outra regiao ou tente novamente mais tarde. |
| SSH recusado | Abra a porta 22 nas Security Lists da VCN (Networking > VCN > Security Lists > Add Ingress Rule) |
| Bot cai e nao volta | Verifique se o service tem `Restart=always`. Confira com `systemctl status`. |
| Sem espaco | A VM free tem 47GB. Use `df -h` para verificar. |

---

## Comparacao

| Aspecto | Koyeb | Oracle Cloud |
|---------|-------|-------------|
| Dificuldade | Facil (navegador) | Media (SSH + Linux) |
| RAM gratis | 512MB | Ate 24GB |
| CPU gratis | 0.1 vCPU | Ate 4 CPUs |
| Setup | 5 minutos | 30 minutos |
| Auto-deploy | Sim (git push) | Manual (git pull) |
| Auto-restart | Sim | Sim (systemd) |
| Cartao de credito | Nao | Verificacao (nao cobra) |
| Melhor para | Simplicidade | Projetos maiores |

**Recomendacao**: Comece pelo **Koyeb** (mais rapido). Se precisar de mais recursos, migre para **Oracle Cloud**.

---

*Guia criado para o Professor Wendel Castro — mas util para qualquer dev que queira deployar um bot Python.*
