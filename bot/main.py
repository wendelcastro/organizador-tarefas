"""
Organizador de Tarefas — Telegram Bot com IA
=============================================
Bot INTELIGENTE que usa Claude API como cerebro.
Nao e um CRUD — e um assistente que PENSA.

Fluxo principal:
1. Usuario manda texto/audio
2. Claude classifica e PERGUNTA antes de salvar
3. Usuario confirma ou ajusta
4. Tarefa salva no Supabase + dashboard atualiza

Comandos:
  /start     — Boas-vindas
  /tarefas   — Lista pendentes
  /planejar  — Planejamento inteligente do dia
  /feedback  — Feedback construtivo do dia
  /resumo    — Resumo rapido
  /concluir  — Marca ultima tarefa como concluida

Como rodar:
  pip install -r bot/requirements.txt
  python bot/main.py
"""

import os
import sys
import json
import re
import logging
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Carregar .env do diretorio raiz do projeto
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Configuracao
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    print("ERRO: Preencha TELEGRAM_BOT_TOKEN, SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    sys.exit(1)

if not GROQ_API_KEY:
    print("AVISO: GROQ_API_KEY nao configurada. Transcricao de audio desabilitada.")

# IA: importar cerebro
ai_brain = None
if ANTHROPIC_API_KEY:
    from ai_brain import AIBrain
    ai_brain = AIBrain(ANTHROPIC_API_KEY)
    print("Claude API conectada — modo inteligente ativado!")
else:
    print("AVISO: ANTHROPIC_API_KEY nao configurada. Bot rodara em modo basico (sem IA).")

# Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ========== ESTADOS DE CONVERSA ==========
# Cada usuario tem um estado que controla o fluxo

STATE_IDLE = "idle"                # Esperando nova entrada
STATE_CONFIRMING = "confirming"    # Esperando confirmacao de tarefa
STATE_CHATTING = "chatting"        # Conversa livre (pos-feedback)


def get_state(context):
    """Retorna o estado atual da conversa."""
    return context.user_data.get("state", STATE_IDLE)


def set_state(context, state, **kwargs):
    """Define o estado da conversa com dados extras."""
    context.user_data["state"] = state
    for k, v in kwargs.items():
        context.user_data[k] = v


def clear_state(context):
    """Volta ao estado idle."""
    context.user_data["state"] = STATE_IDLE
    context.user_data.pop("pending_task", None)
    context.user_data.pop("chat_history", None)


# ========== SUPABASE HELPERS ==========

def supabase_request(method, endpoint, data=None, params=None):
    """Faz requisicao HTTP para a API REST do Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except URLError as e:
        logger.error(f"Supabase error: {e}")
        return None


def criar_tarefa(titulo, categoria="Pessoal", prioridade="media", prazo=None,
                 horario=None, meeting_link=None, meeting_platform=None,
                 notas="", tempo_estimado=None):
    """Cria uma tarefa no Supabase."""
    tarefa = {
        "titulo": titulo,
        "categoria": categoria,
        "prioridade": prioridade,
        "status": "pendente",
        "prazo": prazo,
        "horario": horario,
        "meeting_link": meeting_link or "",
        "meeting_platform": meeting_platform,
        "notas": notas,
        "origem": "telegram",
    }

    # Detectar plataforma de reuniao se nao foi passada
    if meeting_link and not meeting_platform:
        if "zoom" in meeting_link:
            tarefa["meeting_platform"] = "zoom"
        elif "meet.google" in meeting_link:
            tarefa["meeting_platform"] = "meet"
        elif "teams" in meeting_link:
            tarefa["meeting_platform"] = "teams"

    result = supabase_request("POST", "tarefas", tarefa)
    return result[0] if result else None


def listar_tarefas_pendentes(limite=10):
    """Lista tarefas pendentes ordenadas por prazo."""
    params = {
        "status": "neq.concluida",
        "order": "prazo.asc.nullslast,prioridade.asc",
        "limit": str(limite),
        "select": "id,titulo,categoria,prioridade,prazo,horario,meeting_link,status",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_tarefas_do_dia(data=None):
    """Lista tarefas de um dia especifico."""
    if not data:
        data = datetime.now().strftime("%Y-%m-%d")
    params = {
        "prazo": f"eq.{data}",
        "status": "neq.concluida",
        "order": "horario.asc.nullslast",
        "select": "id,titulo,categoria,prioridade,prazo,horario,meeting_link,status",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_tarefas_atrasadas():
    """Lista tarefas atrasadas."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    params = {
        "prazo": f"lt.{hoje}",
        "status": "neq.concluida",
        "order": "prazo.asc",
        "select": "id,titulo,categoria,prioridade,prazo,horario",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_concluidas_hoje():
    """Lista tarefas concluidas hoje."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    params = {
        "status": "eq.concluida",
        "completed_at": f"gte.{hoje}T00:00:00",
        "order": "completed_at.desc",
        "select": "id,titulo,categoria,prioridade,completed_at",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def obter_resumo():
    """Busca o resumo semanal."""
    result = supabase_request("GET", "resumo_semanal")
    return result[0] if result else None


def concluir_ultima_tarefa():
    """Marca a tarefa pendente mais recente como concluida."""
    params = {
        "status": "eq.pendente",
        "order": "created_at.desc",
        "limit": "1",
        "select": "id,titulo",
    }
    tarefas = supabase_request("GET", "tarefas", params=params)
    if not tarefas:
        return None
    tarefa = tarefas[0]
    supabase_request("PATCH", f"tarefas?id=eq.{tarefa['id']}", {"status": "concluida"})
    return tarefa


# ========== CLASSIFICACAO BASICA (fallback sem IA) ==========

def classificar_tarefa_basico(texto):
    """Classificacao por keywords — fallback quando nao tem Claude."""
    texto_lower = texto.lower()

    categoria = "Pessoal"
    if any(w in texto_lower for w in ["aula", "prova", "aluno", "tcc", "corrigir", "nota", "disciplina"]):
        categoria = "Trabalho"
    elif any(w in texto_lower for w in ["consultoria", "cliente", "projeto", "pipeline", "dados"]):
        categoria = "Consultoria"
    elif any(w in texto_lower for w in ["ser educacional", "grupo ser", "coordenacao", "pedagogico"]):
        categoria = "Grupo Ser"

    prioridade = "media"
    if any(w in texto_lower for w in ["urgente", "hoje", "agora", "critico"]):
        prioridade = "alta"
    elif any(w in texto_lower for w in ["quando puder", "sem pressa", "baixa prioridade"]):
        prioridade = "baixa"

    prazo = None
    hoje = datetime.now()
    if "hoje" in texto_lower:
        prazo = hoje.strftime("%Y-%m-%d")
    elif "amanha" in texto_lower or "amanhã" in texto_lower:
        prazo = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")

    horario = None
    time_match = re.search(r'(\d{1,2})[h:](\d{2})', texto_lower)
    if time_match:
        h, m = int(time_match.group(1)), int(time_match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            horario = f"{h:02d}:{m:02d}"

    meeting_link = None
    url_match = re.search(r'(https?://\S+)', texto)
    if url_match:
        url = url_match.group(1)
        if any(p in url for p in ["zoom", "meet.google", "teams"]):
            meeting_link = url

    return {
        "titulo": texto,
        "categoria": categoria,
        "prioridade": prioridade,
        "prazo": prazo,
        "horario": horario,
        "meeting_link": meeting_link,
    }


# ========== FORMATACAO ==========

EMOJI_CATEGORIA = {
    "Trabalho": "📚", "Consultoria": "💼", "Grupo Ser": "🏛", "Pessoal": "🏠",
}
EMOJI_PRIORIDADE = {
    "alta": "🔴", "media": "🟡", "baixa": "⚪",
}


def formatar_tarefa_card(tarefa):
    """Formata uma tarefa para exibicao no Telegram."""
    cat_emoji = EMOJI_CATEGORIA.get(tarefa.get("categoria", ""), "📋")
    pri_emoji = EMOJI_PRIORIDADE.get(tarefa.get("prioridade", ""), "⚪")

    linhas = [f"{pri_emoji} *{tarefa['titulo']}*"]
    linhas.append(f"   {cat_emoji} {tarefa.get('categoria', '')}")

    if tarefa.get("prazo"):
        try:
            d = datetime.strptime(tarefa["prazo"], "%Y-%m-%d")
            linhas.append(f"   📅 {d.strftime('%d/%m (%a)')}")
        except ValueError:
            pass

    if tarefa.get("horario"):
        h = tarefa["horario"]
        if isinstance(h, str) and len(h) >= 5:
            linhas.append(f"   🕐 {h[:5]}")

    if tarefa.get("meeting_link"):
        linhas.append(f"   🔗 [Entrar na reuniao]({tarefa['meeting_link']})")

    if tarefa.get("tempo_estimado_min"):
        linhas.append(f"   ⏱ ~{tarefa['tempo_estimado_min']}min estimados")

    return "\n".join(linhas)


def formatar_confirmacao(classificacao):
    """Formata a mensagem de confirmacao com a tarefa classificada."""
    card = formatar_tarefa_card(classificacao)

    msg = f"🧠 *Entendi! Classifiquei assim:*\n\n{card}\n\n"

    if classificacao.get("alerta_sobrecarga") and classificacao.get("alerta_msg"):
        msg += f"⚠️ {classificacao['alerta_msg']}\n\n"

    if classificacao.get("mensagem"):
        msg += f"_{classificacao['mensagem']}_\n\n"

    msg += "✅ *Confirma?* Ou me diz o que ajustar."

    return msg


# ========== TRANSCRICAO DE AUDIO ==========

def transcrever_audio(caminho_audio):
    """Transcreve audio usando Groq API (Whisper) via httpx."""
    import httpx

    if not GROQ_API_KEY:
        return None

    wav_path = caminho_audio.replace(".ogg", ".wav").replace(".oga", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-i", caminho_audio, "-ar", "16000", "-ac", "1", "-y", wav_path],
            capture_output=True, timeout=30,
        )
    except Exception as e:
        logger.error(f"Erro ao converter audio: {e}")
        return None

    if not os.path.exists(wav_path):
        return None

    try:
        with open(wav_path, "rb") as f:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"model": "whisper-large-v3-turbo", "language": "pt"},
                timeout=30,
            )
        if resp.status_code != 200:
            logger.error(f"Groq API erro {resp.status_code}: {resp.text}")
            return None
        result = resp.json()
        texto = result.get("text", "").strip()
        return texto if texto and texto not in [".", ""] else None
    except Exception as e:
        logger.error(f"Erro na transcricao Groq: {e}")
        return None
    finally:
        for f in [caminho_audio, wav_path]:
            try:
                os.remove(f)
            except OSError:
                pass


# ========== PROCESSAR TAREFA (texto ja extraido) ==========

async def processar_nova_tarefa(update, context, texto):
    """
    Processa texto como nova tarefa.
    COM IA: classifica + pede confirmacao
    SEM IA: classifica por keywords + salva direto
    """
    if ai_brain:
        # === MODO INTELIGENTE ===
        tarefas_hoje = listar_tarefas_do_dia()

        # Claude classifica
        classificacao = ai_brain.classificar_tarefa(texto, tarefas_hoje)

        # Salva como pendente de confirmacao
        set_state(context, STATE_CONFIRMING, pending_task=classificacao)

        # Mostra e pede confirmacao
        msg = formatar_confirmacao(classificacao)
        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

    else:
        # === MODO BASICO (sem IA) ===
        classificacao = classificar_tarefa_basico(texto)
        tarefa = criar_tarefa(
            titulo=classificacao["titulo"],
            categoria=classificacao["categoria"],
            prioridade=classificacao["prioridade"],
            prazo=classificacao["prazo"],
            horario=classificacao["horario"],
            meeting_link=classificacao.get("meeting_link"),
        )
        if tarefa:
            resposta = "✅ *Tarefa criada!*\n\n" + formatar_tarefa_card(tarefa)
            await update.message.reply_text(resposta, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Erro ao criar tarefa.")


async def processar_confirmacao(update, context, texto):
    """Processa resposta de confirmacao/ajuste de tarefa."""
    pending = context.user_data.get("pending_task")
    if not pending:
        clear_state(context)
        return

    result = ai_brain.processar_confirmacao(texto, pending)

    if not result:
        # Nao entendeu — assume confirmacao
        result = {"acao": "salvar"}

    acao = result.get("acao")

    if acao == "cancelar":
        clear_state(context)
        await update.message.reply_text("🚫 Tarefa cancelada.")
        return

    if acao == "salvar":
        # Salvar a tarefa pendente
        tarefa_data = pending
    else:
        # Claude retornou tarefa atualizada
        tarefa_data = result

    # Criar no Supabase
    tarefa = criar_tarefa(
        titulo=tarefa_data.get("titulo", "Tarefa"),
        categoria=tarefa_data.get("categoria", "Pessoal"),
        prioridade=tarefa_data.get("prioridade", "media"),
        prazo=tarefa_data.get("prazo"),
        horario=tarefa_data.get("horario"),
        meeting_link=tarefa_data.get("meeting_link"),
        meeting_platform=tarefa_data.get("meeting_platform"),
        tempo_estimado=tarefa_data.get("tempo_estimado_min"),
    )

    clear_state(context)

    if tarefa:
        resposta = "✅ *Tarefa salva!*\n\n" + formatar_tarefa_card(tarefa)
        resposta += f"\n\n[📊 Ver no dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)"
        await update.message.reply_text(resposta, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text("❌ Erro ao salvar tarefa.")


# ========== HANDLERS DO BOT ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem de boas-vindas."""
    chat_id = update.effective_chat.id
    logger.info(f"Chat ID: {chat_id}")
    clear_state(context)

    modo = "🧠 *Modo inteligente* (Claude IA)" if ai_brain else "⚡ *Modo basico* (sem IA)"

    await update.message.reply_text(
        f"👋 *Organizador de Tarefas*\n\n"
        f"{modo}\n\n"
        "Mande uma mensagem de texto ou audio e eu organizo pra voce!\n\n"
        "*Comandos:*\n"
        "/tarefas — Ver pendentes\n"
        "/planejar — Planejamento inteligente do dia\n"
        "/feedback — Feedback construtivo do dia\n"
        "/resumo — Resumo rapido\n"
        "/concluir — Concluir ultima tarefa\n\n"
        "*Como funciona:*\n"
        "1. Voce manda a tarefa (texto ou audio)\n"
        "2. Eu classifico e pergunto se esta certo\n"
        "3. Voce confirma ou ajusta\n"
        "4. Tarefa salva — dashboard atualiza automaticamente\n\n"
        f"📊 [Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)\n"
        f"_Chat ID: {chat_id}_",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista tarefas pendentes."""
    clear_state(context)
    tarefas = listar_tarefas_pendentes(10)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente! Voce esta em dia.")
        return

    texto = f"📋 *Tarefas pendentes ({len(tarefas)}):*\n\n"
    for t in tarefas:
        texto += formatar_tarefa_card(t) + "\n\n"

    texto += f"[📊 Ver no dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)"
    await update.message.reply_text(texto, parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_planejar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Planejamento inteligente do dia."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text(
            "⚠️ Planejamento inteligente requer Claude API.\n"
            "Configure ANTHROPIC_API_KEY no .env e reinicie o bot."
        )
        return

    msg = await update.message.reply_text("🧠 Analisando seu dia...")

    # Buscar tarefas do dia + atrasadas
    hoje = datetime.now().strftime("%Y-%m-%d")
    tarefas_hoje = listar_tarefas_do_dia(hoje)
    atrasadas = listar_tarefas_atrasadas()
    todas = tarefas_hoje + atrasadas

    if not todas:
        await msg.edit_text(
            "📭 Nenhuma tarefa para hoje e nada atrasado!\n\n"
            "Que tal aproveitar para:\n"
            "• 🇬🇧 Ingles (30min)\n"
            "• 📖 Leitura\n"
            "• 🧠 Projeto pessoal"
        )
        return

    planejamento = ai_brain.planejar_dia(todas, hoje)

    # Entra em modo chat para discutir o planejamento
    set_state(context, STATE_CHATTING, chat_history=[
        {"role": "assistant", "content": planejamento}
    ])

    await msg.edit_text(planejamento, parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Feedback construtivo do dia."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text(
            "⚠️ Feedback inteligente requer Claude API.\n"
            "Configure ANTHROPIC_API_KEY no .env e reinicie o bot."
        )
        return

    msg = await update.message.reply_text("🧠 Analisando seu dia...")

    hoje = datetime.now().strftime("%Y-%m-%d")
    concluidas = listar_concluidas_hoje()
    pendentes = listar_tarefas_do_dia(hoje)

    feedback = ai_brain.feedback_dia(concluidas, pendentes, hoje)

    # Entra em modo chat para discutir o feedback
    set_state(context, STATE_CHATTING, chat_history=[
        {"role": "assistant", "content": feedback}
    ])

    await msg.edit_text(feedback, parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra resumo semanal."""
    clear_state(context)
    resumo = obter_resumo()

    if not resumo:
        await update.message.reply_text("❌ Erro ao buscar resumo.")
        return

    await update.message.reply_text(
        "📊 *Resumo:*\n\n"
        f"📋 Total: *{resumo['total']}*\n"
        f"⏳ Pendentes: *{resumo['pendentes']}*\n"
        f"✅ Concluidas esta semana: *{resumo['concluidas_semana']}*\n"
        f"🔴 Atrasadas: *{resumo['atrasadas']}*\n"
        f"🎥 Reunioes pendentes: *{resumo['reunioes_pendentes']}*\n"
        f"🔥 Alta prioridade: *{resumo['alta_prioridade']}*\n\n"
        f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conclui a ultima tarefa pendente."""
    clear_state(context)
    tarefa = concluir_ultima_tarefa()
    if tarefa:
        await update.message.reply_text(f'✅ Concluida: *{tarefa["titulo"]}*', parse_mode="Markdown")
    else:
        await update.message.reply_text("Nenhuma tarefa pendente para concluir.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal de texto — roteador de estados."""
    texto = update.message.text.strip()
    if not texto:
        return

    state = get_state(context)

    if state == STATE_CONFIRMING and ai_brain:
        # Esperando confirmacao de tarefa
        await processar_confirmacao(update, context, texto)

    elif state == STATE_CHATTING and ai_brain:
        # Conversa livre (pos-feedback ou pos-planejamento)
        history = context.user_data.get("chat_history", [])
        history.append({"role": "user", "content": texto})

        msg = await update.message.reply_text("🧠 Pensando...")
        resposta = ai_brain.conversar(texto, history)

        history.append({"role": "assistant", "content": resposta})
        context.user_data["chat_history"] = history

        await msg.edit_text(resposta, parse_mode="Markdown", disable_web_page_preview=True)

        # Se usuario manda algo que parece tarefa nova, sai do chat
        if any(w in texto.lower() for w in ["nova tarefa", "adicionar", "criar tarefa", "/sair"]):
            clear_state(context)

    else:
        # Estado idle — nova tarefa
        await processar_nova_tarefa(update, context, texto)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe audio, transcreve e processa como tarefa."""
    if not GROQ_API_KEY:
        await update.message.reply_text(
            "🎤 Audio recebido, mas transcricao nao esta configurada.\n"
            "Configure GROQ_API_KEY no .env"
        )
        return

    msg = await update.message.reply_text("🎤 Transcrevendo audio...")

    try:
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)

        tmp_dir = tempfile.mkdtemp()
        ogg_path = os.path.join(tmp_dir, "audio.ogg")
        await file.download_to_drive(ogg_path)

        texto = transcrever_audio(ogg_path)

        if not texto:
            await msg.edit_text("❌ Nao consegui transcrever. Tente novamente ou mande por texto.")
            return

        await msg.edit_text(f"🎤 Entendi: _{texto}_\n\nProcessando...", parse_mode="Markdown")

        # Processa como tarefa (com ou sem IA)
        # Usamos update.message.reply_text pois msg.edit_text
        # nao funciona bem com o fluxo de confirmacao
        await processar_nova_tarefa(update, context, texto)

    except Exception as e:
        logger.error(f"Erro no handler de voz: {e}")
        await msg.edit_text("❌ Erro ao processar audio.")


async def setup_commands(app):
    """Configura os comandos visiveis no menu do Telegram."""
    commands = [
        BotCommand("start", "Iniciar o bot"),
        BotCommand("tarefas", "Ver tarefas pendentes"),
        BotCommand("planejar", "Planejamento inteligente do dia"),
        BotCommand("feedback", "Feedback construtivo do dia"),
        BotCommand("resumo", "Resumo rapido"),
        BotCommand("concluir", "Concluir ultima tarefa"),
    ]
    await app.bot.set_my_commands(commands)


# ========== MAIN ==========

def main():
    logger.info("Iniciando Organizador de Tarefas Bot...")
    modo = "INTELIGENTE (Claude)" if ai_brain else "BASICO (sem IA)"
    logger.info(f"Modo: {modo}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(setup_commands).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("tarefas", cmd_tarefas))
    app.add_handler(CommandHandler("planejar", cmd_planejar))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("concluir", cmd_concluir))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot rodando! Mande /start no Telegram.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
