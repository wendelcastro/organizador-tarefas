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

### Passo a Passo

#### 1. Criar conta
- Acesse [koyeb.com](https://www.koyeb.com)
- Crie conta com GitHub (mais facil)
- Nao precisa de cartao de credito

#### 2. Preparar o projeto
O projeto ja inclui um `Dockerfile` na raiz. Verifique que ele existe:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt
COPY bot/ ./bot/
CMD ["python", "bot/main.py"]
```

#### 3. Criar o servico
1. No painel do Koyeb, clique **Create Service**
2. Selecione **GitHub** como source
3. Conecte seu GitHub e selecione o repositorio `organizador-tarefas`
4. Branch: `main`
5. Builder: **Dockerfile**
6. Instance type: **Free**
7. Region: Frankfurt ou Washington DC

#### 4. Configurar variaveis de ambiente
Na secao "Environment variables", adicione cada uma:

| Variavel | Valor |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Seu token do BotFather |
| `SUPABASE_URL` | URL do seu projeto Supabase |
| `SUPABASE_ANON_KEY` | Anon key do Supabase |
| `ANTHROPIC_API_KEY` | Chave da Claude API |
| `GROQ_API_KEY` | Chave do Groq (opcional) |

**IMPORTANTE**: As variaveis ficam criptografadas no Koyeb. Ninguem ve.

#### 5. Deploy
- Clique **Deploy**
- Aguarde 2-3 minutos para build e startup
- Verifique nos logs se aparece "Bot v2 rodando!"

#### 6. Pronto!
O bot agora:
- Roda 24/7
- Reinicia automaticamente se cair
- Atualiza sozinho quando voce faz `git push`
- Envia resumo matinal as 7:30
- Envia relatorio toda sexta as 17h
- Envia lembretes 15min antes de reunioes

### Troubleshooting Koyeb

| Problema | Solucao |
|----------|---------|
| Build falhou | Verifique se `Dockerfile` e `bot/requirements.txt` estao no repo |
| Bot nao responde | Confira as variaveis de ambiente no painel |
| Erro de conexao | Verifique SUPABASE_URL (deve comecar com https://) |
| Audio nao funciona | GROQ_API_KEY pode estar vazia. Confira. |
| Bot duplicado | Mate o bot local antes de deployar na nuvem |

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
