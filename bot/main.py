"""
Organizador de Tarefas — Telegram Bot
=====================================
Recebe texto ou audio pelo Telegram e cria tarefas no Supabase.
O dashboard web atualiza automaticamente via Realtime.

Como rodar:
  python bot/main.py

Comandos do bot:
  /start    — Mensagem de boas-vindas
  /tarefas  — Lista tarefas pendentes
  /resumo   — Resumo rapido (pendentes, atrasadas, reunioes)
  /concluir — Marca a ultima tarefa como concluida
  (texto)   — Cria nova tarefa
  (audio)   — Transcreve e cria nova tarefa
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

if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    print("ERRO: Preencha TELEGRAM_BOT_TOKEN, SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    sys.exit(1)

if not GROQ_API_KEY:
    print("AVISO: GROQ_API_KEY nao configurada. Transcricao de audio desabilitada.")

# Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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
                 horario=None, meeting_link=None, notas=""):
    """Cria uma tarefa no Supabase."""
    tarefa = {
        "titulo": titulo,
        "categoria": categoria,
        "prioridade": prioridade,
        "status": "pendente",
        "prazo": prazo,
        "horario": horario,
        "meeting_link": meeting_link or "",
        "notas": notas,
        "origem": "telegram",
    }

    # Detectar plataforma de reuniao
    if meeting_link:
        if "zoom" in meeting_link:
            tarefa["meeting_platform"] = "zoom"
        elif "meet.google" in meeting_link:
            tarefa["meeting_platform"] = "meet"
        elif "teams" in meeting_link:
            tarefa["meeting_platform"] = "teams"
        else:
            tarefa["meeting_platform"] = "outro"

    result = supabase_request("POST", "tarefas", tarefa)
    return result[0] if result else None


def listar_tarefas_pendentes(limite=10):
    """Lista tarefas pendentes ordenadas por prazo."""
    params = {
        "status": "neq.concluida",
        "order": "prazo.asc.nullslast,prioridade.asc",
        "limit": str(limite),
        "select": "id,titulo,categoria,prioridade,prazo,horario,meeting_link",
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


# ========== CLASSIFICACAO INTELIGENTE ==========

def classificar_tarefa(texto):
    """
    Classifica a tarefa com base em palavras-chave.
    Futuramente, isso sera feito pela Claude API para ser mais inteligente.
    """
    texto_lower = texto.lower()

    # Detectar categoria
    categoria = "Pessoal"
    if any(w in texto_lower for w in ["aula", "prova", "aluno", "tcc", "corrigir", "plano de ensino", "disciplina", "nota"]):
        categoria = "Trabalho"
    elif any(w in texto_lower for w in ["consultoria", "cliente", "projeto", "entrega", "relatorio", "pipeline", "dados"]):
        categoria = "Consultoria"
    elif any(w in texto_lower for w in ["ser educacional", "grupo ser", "coordenacao", "pedagogico", "curso novo", "institucional"]):
        categoria = "Grupo Ser"

    # Detectar prioridade
    prioridade = "media"
    if any(w in texto_lower for w in ["urgente", "urgencia", "hoje", "agora", "critico", "importante", "prazo curto"]):
        prioridade = "alta"
    elif any(w in texto_lower for w in ["quando puder", "sem pressa", "baixa prioridade", "qualquer hora"]):
        prioridade = "baixa"

    # Detectar prazo
    prazo = None
    hoje = datetime.now()

    if "hoje" in texto_lower:
        prazo = hoje.strftime("%Y-%m-%d")
    elif "amanha" in texto_lower or "amanhã" in texto_lower:
        prazo = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "segunda" in texto_lower:
        prazo = _proximo_dia_semana(0)
    elif "terca" in texto_lower or "terça" in texto_lower:
        prazo = _proximo_dia_semana(1)
    elif "quarta" in texto_lower:
        prazo = _proximo_dia_semana(2)
    elif "quinta" in texto_lower:
        prazo = _proximo_dia_semana(3)
    elif "sexta" in texto_lower:
        prazo = _proximo_dia_semana(4)
    elif "sabado" in texto_lower or "sábado" in texto_lower:
        prazo = _proximo_dia_semana(5)
    elif "domingo" in texto_lower:
        prazo = _proximo_dia_semana(6)

    # Detectar horario (formato HH:MM ou "as X horas")
    horario = None
    time_match = re.search(r'(\d{1,2})[h:](\d{2})', texto_lower)
    if time_match:
        h, m = int(time_match.group(1)), int(time_match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            horario = f"{h:02d}:{m:02d}"

    hora_match = re.search(r'[àa]s?\s*(\d{1,2})\s*(?:hora|hr|h(?!\d))', texto_lower)
    if hora_match and not horario:
        h = int(hora_match.group(1))
        if 0 <= h <= 23:
            horario = f"{h:02d}:00"

    # Detectar link de reuniao
    meeting_link = None
    url_match = re.search(r'(https?://\S+)', texto)
    if url_match:
        url = url_match.group(1)
        if any(p in url for p in ["zoom", "meet.google", "teams"]):
            meeting_link = url

    return {
        "categoria": categoria,
        "prioridade": prioridade,
        "prazo": prazo,
        "horario": horario,
        "meeting_link": meeting_link,
    }


def _proximo_dia_semana(dia_alvo):
    """Retorna a data do proximo dia da semana (0=segunda, 6=domingo)."""
    hoje = datetime.now()
    dias_frente = (dia_alvo - hoje.weekday()) % 7
    if dias_frente == 0:
        dias_frente = 7  # proximo, nao hoje
    return (hoje + timedelta(days=dias_frente)).strftime("%Y-%m-%d")


# ========== FORMATACAO ==========

EMOJI_CATEGORIA = {
    "Trabalho": "📚",
    "Consultoria": "💼",
    "Grupo Ser": "🏛",
    "Pessoal": "🏠",
}

EMOJI_PRIORIDADE = {
    "alta": "🔴",
    "media": "🟡",
    "baixa": "⚪",
}

def formatar_tarefa_card(tarefa):
    """Formata uma tarefa para exibicao no Telegram."""
    cat_emoji = EMOJI_CATEGORIA.get(tarefa.get("categoria", ""), "📋")
    pri_emoji = EMOJI_PRIORIDADE.get(tarefa.get("prioridade", ""), "⚪")

    linhas = [f"{pri_emoji} *{tarefa['titulo']}*"]
    linhas.append(f"   {cat_emoji} {tarefa.get('categoria', '')}")

    if tarefa.get("prazo"):
        d = datetime.strptime(tarefa["prazo"], "%Y-%m-%d")
        prazo_fmt = d.strftime("%d/%m (%a)")
        linhas.append(f"   📅 {prazo_fmt}")

    if tarefa.get("horario"):
        h = tarefa["horario"]
        if isinstance(h, str) and len(h) >= 5:
            linhas.append(f"   🕐 {h[:5]}")

    if tarefa.get("meeting_link"):
        linhas.append(f"   🔗 [Entrar na reuniao]({tarefa['meeting_link']})")

    return "\n".join(linhas)


# ========== TRANSCRICAO DE AUDIO (GROQ/WHISPER) ==========

def transcrever_audio(caminho_audio):
    """
    Transcreve audio usando Groq API (Whisper).
    Groq roda Whisper gratuitamente e com latencia muito baixa.
    Usa httpx em vez de urllib (Cloudflare bloqueia urllib).

    Fluxo:
    1. Converte OGG (formato do Telegram) para WAV via ffmpeg
    2. Envia WAV para Groq API via httpx
    3. Retorna texto transcrito
    """
    import httpx

    if not GROQ_API_KEY:
        return None

    # Converter OGG para WAV usando ffmpeg
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
        logger.error("Arquivo WAV nao foi criado")
        return None

    # Enviar para Groq API via httpx
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
        logger.info(f"Transcricao: {texto[:80]}...")
        return texto if texto and texto not in [".", ""] else None

    except Exception as e:
        logger.error(f"Erro na transcricao Groq: {e}")
        return None
    finally:
        # Limpar arquivos temporarios
        for f in [caminho_audio, wav_path]:
            try:
                os.remove(f)
            except OSError:
                pass


# ========== HANDLERS DO BOT ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem de boas-vindas."""
    chat_id = update.effective_chat.id
    logger.info(f"Chat ID: {chat_id}")

    await update.message.reply_text(
        "👋 *Organizador de Tarefas*\n\n"
        "Mande uma mensagem de texto ou audio e eu crio a tarefa pra voce!\n\n"
        "*Comandos:*\n"
        "/tarefas — Ver pendentes\n"
        "/resumo — Resumo rapido\n"
        "/concluir — Concluir ultima tarefa\n\n"
        "*Dicas:*\n"
        '• Diga "amanha" ou "sexta" para definir prazo\n'
        '• Diga "urgente" para prioridade alta\n'
        '• Cole link do Zoom/Meet/Teams para reunioes\n'
        '• Diga "aula" ou "prova" → categoria Trabalho\n\n'
        f"📊 Dashboard: [Abrir](https://wendelcastro.github.io/organizador-tarefas/web/)\n\n"
        f"_Seu chat ID: {chat_id}_",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista tarefas pendentes."""
    tarefas = listar_tarefas_pendentes(10)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente! Voce esta em dia.")
        return

    texto = f"📋 *Tarefas pendentes ({len(tarefas)}):*\n\n"
    for t in tarefas:
        texto += formatar_tarefa_card(t) + "\n\n"

    texto += f"[📊 Ver no dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)"

    await update.message.reply_text(texto, parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra resumo semanal."""
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
    tarefa = concluir_ultima_tarefa()
    if tarefa:
        await update.message.reply_text(f'✅ Concluida: *{tarefa["titulo"]}*', parse_mode="Markdown")
    else:
        await update.message.reply_text("Nenhuma tarefa pendente para concluir.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe texto e cria tarefa."""
    texto = update.message.text.strip()
    if not texto:
        return

    # Classificar
    classificacao = classificar_tarefa(texto)

    # Criar no Supabase
    tarefa = criar_tarefa(
        titulo=texto,
        categoria=classificacao["categoria"],
        prioridade=classificacao["prioridade"],
        prazo=classificacao["prazo"],
        horario=classificacao["horario"],
        meeting_link=classificacao["meeting_link"],
    )

    if tarefa:
        resposta = "✅ *Tarefa criada!*\n\n" + formatar_tarefa_card(tarefa)
        await update.message.reply_text(resposta, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text("❌ Erro ao criar tarefa. Tente novamente.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recebe audio, transcreve via Groq/Whisper e cria tarefa.

    Fluxo:
    1. Telegram envia audio em formato OGG
    2. Bot baixa o arquivo
    3. FFmpeg converte para WAV
    4. Groq API transcreve (Whisper)
    5. Texto e classificado e tarefa criada no Supabase
    6. Dashboard atualiza via Realtime
    """
    if not GROQ_API_KEY:
        await update.message.reply_text(
            "🎤 Audio recebido, mas transcricao nao esta configurada.\n"
            "Configure GROQ_API_KEY no .env",
        )
        return

    # Feedback instantaneo
    msg = await update.message.reply_text("🎤 Transcrevendo audio...")

    try:
        # Baixar audio do Telegram
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)

        # Salvar em arquivo temporario
        tmp_dir = tempfile.mkdtemp()
        ogg_path = os.path.join(tmp_dir, "audio.ogg")
        await file.download_to_drive(ogg_path)

        # Transcrever
        texto = transcrever_audio(ogg_path)

        if not texto:
            await msg.edit_text("❌ Nao consegui transcrever o audio. Tente novamente ou mande por texto.")
            return

        # Mostrar o que entendeu
        await msg.edit_text(f"🎤 Entendi: _{texto}_\n\nCriando tarefa...", parse_mode="Markdown")

        # Classificar e criar
        classificacao = classificar_tarefa(texto)
        tarefa = criar_tarefa(
            titulo=texto,
            categoria=classificacao["categoria"],
            prioridade=classificacao["prioridade"],
            prazo=classificacao["prazo"],
            horario=classificacao["horario"],
            meeting_link=classificacao["meeting_link"],
        )

        if tarefa:
            resposta = "✅ *Tarefa criada por audio!*\n\n" + formatar_tarefa_card(tarefa)
            await msg.edit_text(resposta, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await msg.edit_text("❌ Erro ao criar tarefa. Tente novamente.")

    except Exception as e:
        logger.error(f"Erro no handler de voz: {e}")
        await msg.edit_text("❌ Erro ao processar audio. Tente novamente.")


async def setup_commands(app):
    """Configura os comandos visiveis no menu do Telegram."""
    commands = [
        BotCommand("start", "Iniciar o bot"),
        BotCommand("tarefas", "Ver tarefas pendentes"),
        BotCommand("resumo", "Resumo rapido"),
        BotCommand("concluir", "Concluir ultima tarefa"),
    ]
    await app.bot.set_my_commands(commands)


# ========== MAIN ==========

def main():
    logger.info("Iniciando Organizador de Tarefas Bot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(setup_commands).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("tarefas", cmd_tarefas))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("concluir", cmd_concluir))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot rodando! Mande /start no Telegram.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
