# Guia Passo a Passo: Integrar Google Calendar + Microsoft Teams

Esse guia vai te levar do zero ate ter seus calendarios sincronizados.
Tempo estimado: ~20 minutos (10 Google + 10 Microsoft)

---

## PARTE 1: Google Calendar

### Passo 1 — Acessar o Google Cloud Console

1. Abra: https://console.cloud.google.com
2. Faca login com sua conta Google (a mesma do Google Calendar que quer sincronizar)
3. Se for sua primeira vez, aceite os termos de servico

### Passo 2 — Criar um Projeto

1. No topo da pagina, clique em **"Select a project"** (ou o nome do projeto atual)
2. Clique em **"NEW PROJECT"** (canto superior direito do popup)
3. Nome: `Organizador Tarefas`
4. Clique **"CREATE"**
5. Aguarde criar e selecione o projeto (clique nele na lista)

### Passo 3 — Ativar a Google Calendar API

1. No menu lateral esquerdo, va em **"APIs & Services"** > **"Library"**
2. Na barra de busca, pesquise: `Google Calendar API`
3. Clique no resultado **"Google Calendar API"**
4. Clique no botao azul **"ENABLE"**
5. Aguarde ativar

### Passo 4 — Configurar a Tela de Consentimento OAuth

1. No menu lateral, va em **"APIs & Services"** > **"OAuth consent screen"**
2. Selecione **"External"** e clique **"CREATE"**
3. Preencha:
   - App name: `Organizador de Tarefas`
   - User support email: seu email
   - Developer contact: seu email
4. Clique **"SAVE AND CONTINUE"**
5. Na tela de Scopes, clique **"ADD OR REMOVE SCOPES"**
   - Busque `calendar.readonly`
   - Marque **"Google Calendar API .../auth/calendar.readonly"**
   - Clique **"UPDATE"**
6. Clique **"SAVE AND CONTINUE"**
7. Na tela Test Users, clique **"ADD USERS"**
   - Digite seu email Gmail
   - Clique **"ADD"**
8. Clique **"SAVE AND CONTINUE"**
9. Revise e clique **"BACK TO DASHBOARD"**

### Passo 5 — Criar as Credenciais OAuth

1. No menu lateral, va em **"APIs & Services"** > **"Credentials"**
2. Clique **"+ CREATE CREDENTIALS"** > **"OAuth client ID"**
3. Application type: **"Web application"**
4. Name: `Organizador Bot`
5. Em **"Authorized redirect URIs"**, clique **"+ ADD URI"** e cole:
   ```
   https://delicate-latashia-wendelcastro-30fcdc8a.koyeb.app/auth/google/callback
   ```
6. Clique **"CREATE"**
7. VAI APARECER UM POPUP com:
   - **Client ID**: algo como `123456789-abc.apps.googleusercontent.com`
   - **Client Secret**: algo como `GOCSPX-xxxxxxxx`

   **COPIE OS DOIS E GUARDE!** (Voce pode baixar o JSON tambem)

### Resultado do Passo 1:
Voce agora tem:
- `GOOGLE_CLIENT_ID` = o Client ID copiado
- `GOOGLE_CLIENT_SECRET` = o Client Secret copiado

---

## PARTE 2: Microsoft Teams / Outlook

### Passo 1 — Acessar o Azure Portal

1. Abra: https://portal.azure.com
2. Faca login com sua conta Microsoft (a do Grupo Ser / Teams)
3. Se pedir para configurar algo, pode pular

### Passo 2 — Registrar o App

1. Na barra de busca do topo, pesquise: **"App registrations"**
2. Clique em **"App registrations"**
3. Clique **"+ New registration"**
4. Preencha:
   - Name: `Organizador de Tarefas`
   - Supported account types: **"Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts"**
     (Essa opcao e a terceira, garante que funciona com conta do Grupo Ser E conta pessoal)
   - Redirect URI:
     - Plataforma: **"Web"**
     - URI: `https://delicate-latashia-wendelcastro-30fcdc8a.koyeb.app/auth/microsoft/callback`
5. Clique **"Register"**

### Passo 3 — Copiar o Client ID

1. Na pagina do app registrado, voce vera:
   - **Application (client) ID**: algo como `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

   **COPIE!** Esse e o `MICROSOFT_CLIENT_ID`

### Passo 4 — Criar o Client Secret

1. No menu lateral esquerdo, clique em **"Certificates & secrets"**
2. Clique **"+ New client secret"**
3. Description: `Organizador Bot`
4. Expires: **"24 months"** (maximo)
5. Clique **"Add"**
6. VAI APARECER O SECRET VALUE na coluna "Value"

   **COPIE IMEDIATAMENTE!** Ele so aparece uma vez. Se perdeu, delete e crie outro.

   Esse e o `MICROSOFT_CLIENT_SECRET`

### Passo 5 — Adicionar Permissoes

1. No menu lateral esquerdo, clique em **"API permissions"**
2. Clique **"+ Add a permission"**
3. Escolha **"Microsoft Graph"**
4. Escolha **"Delegated permissions"**
5. Busque e marque:
   - `Calendars.Read`
   - `offline_access`
   - `User.Read` (provavelmente ja esta la)
6. Clique **"Add permissions"**
7. Se aparecer um botao **"Grant admin consent"**, clique nele (opcional, depende das permissoes da sua organizacao)

### Resultado do Passo 2:
Voce agora tem:
- `MICROSOFT_CLIENT_ID` = o Application (client) ID
- `MICROSOFT_CLIENT_SECRET` = o Secret Value copiado

---

## PARTE 3: Configurar no Koyeb

### Passo 1 — Adicionar variaveis de ambiente

1. Abra: https://app.koyeb.com
2. Va no seu servico **organizador-tarefas**
3. Clique em **"Settings"** (ou **"Edit"**)
4. Va na secao **"Environment variables"**
5. Adicione estas 6 variaveis:

| Variavel | Valor |
|----------|-------|
| `GOOGLE_CLIENT_ID` | O Client ID do Google (passo 1.5) |
| `GOOGLE_CLIENT_SECRET` | O Client Secret do Google (passo 1.5) |
| `MICROSOFT_CLIENT_ID` | O Application ID do Azure (passo 2.3) |
| `MICROSOFT_CLIENT_SECRET` | O Secret Value do Azure (passo 2.4) |
| `BOT_PUBLIC_URL` | `https://delicate-latashia-wendelcastro-30fcdc8a.koyeb.app` |
| `OAUTH_SECRET_KEY` | Qualquer texto aleatorio, ex: `minha-chave-secreta-2026` |

6. Clique **"Save"** / **"Redeploy"**

### Passo 2 — Rodar a migration no Supabase

1. Abra: https://supabase.com > seu projeto > **SQL Editor**
2. Cole o conteúdo destes arquivos (um por vez, execute cada um):
   - `supabase/005_pomodoro_reflexoes.sql` — Pomodoro e reflexões
   - `supabase/006_energy_mapping.sql` — Mapeamento de energia
   - `supabase/007_eisenhower_quadrant.sql` — Matriz de Eisenhower
   - `supabase/008_subtarefas.sql` — Subtarefas/checklist
   - `supabase/009_eventos_calendario.sql` — Eventos de calendário
   - `supabase/010_anexos_busca.sql` — Anexos e busca full-text
3. Clique **"Run"** para cada um

---

## PARTE 4: Conectar os Calendarios

Depois que o Koyeb fizer redeploy (2-3 minutos):

### Google Calendar:
1. No Telegram, mande: `/conectar_google`
2. O bot vai mandar um link — clique nele
3. Escolha sua conta Google
4. Clique **"Continuar"** (pode aparecer "app nao verificado", clique em "Avancado" > "Ir para Organizador de Tarefas")
5. Permita acesso ao calendario
6. Vai redirecionar para uma pagina dizendo "Conectado com sucesso!"
7. Volte ao Telegram

### Microsoft Teams/Outlook:
1. No Telegram, mande: `/conectar_microsoft`
2. Clique no link
3. Faca login com sua conta do Grupo Ser
4. Permita acesso ao calendario
5. Pagina de sucesso > volte ao Telegram

### Testar:
1. Mande `/sync` para forcar a sincronizacao
2. Mande `/agenda` para ver os eventos do dia
3. Abra o dashboard — os eventos ja devem aparecer!

---

## Troubleshooting

### "App nao verificado" (Google)
Normal! Como o app esta em modo teste, so voce (adicionado como Test User) consegue usar. Para uso pessoal isso e suficiente.

### "AADSTS..." erro no Microsoft
Provavelmente a conta do Grupo Ser tem restricoes. Tente:
1. Peca ao TI para aprovar o app, OU
2. Use sua conta pessoal Microsoft primeiro para testar

### Eventos nao aparecem no dashboard
1. Verifique se o bot esta healthy no Koyeb
2. Mande `/sync` e veja se retorna contagem de eventos
3. Mande `/agenda` para confirmar que o bot esta lendo os eventos
4. No dashboard, espere 5 minutos (auto-refresh) ou recarregue a pagina

### Redirect URI mismatch
O erro mais comum! Verifique que as URIs sao EXATAMENTE:
- Google: `https://delicate-latashia-wendelcastro-30fcdc8a.koyeb.app/auth/google/callback`
- Microsoft: `https://delicate-latashia-wendelcastro-30fcdc8a.koyeb.app/auth/microsoft/callback`

Sem barra no final, sem http (tem que ser https), sem espaco.
