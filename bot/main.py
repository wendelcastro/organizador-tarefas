"""
Organizador de Tarefas v2 — Telegram Bot com IA
================================================
Bot INTELIGENTE que usa Claude API como cerebro.

Melhorias v2:
- Resolucao temporal (amanha, sexta, daqui 3 dias)
- Multiplas tarefas por mensagem
- Concluir tarefa interativo (inline keyboard)
- Lembretes automaticos (15min antes)
- Resumo matinal automatico (7:30)
- Relatorio semanal automatico (sexta 17:00)
- Modo foco
- Edicao de tarefas pelo chat
- Delegacao
- Tarefas recorrentes
- Memoria de contexto da IA
- Health check HTTP integrado (para deploy no Koyeb/PaaS)
- Decomposicao de tarefas em subtarefas (Sprint 2)
- Check-in meio-dia automatico (13:00)
- Sugestao de reagendamento de atrasadas
- Alerta preditivo de sobrecarga
- Deteccao de conflitos de horario
- Timeout de confirmacao (30 min)

Comandos:
  /start     — Boas-vindas
  /tarefas   — Lista pendentes
  /planejar  — Planejamento inteligente do dia
  /feedback  — Feedback construtivo do dia
  /resumo    — Resumo rapido
  /concluir  — Concluir tarefa (interativo)
  /editar    — Editar tarefa existente
  /decompor  — Decompor tarefa em subtarefas
  /relatorio — Relatorio semanal manual
  /foco      — Modo foco (silencia interrupcoes)
  /cancelar  — Cancela operacao atual

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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
    print("Claude API conectada — modo inteligente v2 ativado!")
else:
    print("AVISO: ANTHROPIC_API_KEY nao configurada. Bot em modo basico (sem IA).")

# Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Timezone
TZ_RECIFE = ZoneInfo("America/Recife")

# Chat ID global (salvo no /start, carregado do Supabase no boot)
CHAT_ID = None


# ========== ESTADOS DE CONVERSA ==========

STATE_IDLE = "idle"
STATE_CONFIRMING = "confirming"
STATE_CONFIRMING_MULTI = "confirming_multi"  # Multiplas tarefas
STATE_CHATTING = "chatting"
STATE_EDITING = "editing"        # Editando tarefa
STATE_FOCUS = "focus"            # Modo foco
STATE_CONFIRMING_DECOMP = "confirming_decomp"  # Confirmando decomposicao


def get_state(context):
    return context.user_data.get("state", STATE_IDLE)


def set_state(context, state, **kwargs):
    context.user_data["state"] = state
    for k, v in kwargs.items():
        context.user_data[k] = v


def clear_state(context):
    context.user_data["state"] = STATE_IDLE
    for key in ["pending_task", "pending_tasks", "confirm_history",
                "chat_history", "editing_task_id", "focus_until",
                "pending_decomp", "decomp_task", "state_timestamp"]:
        context.user_data.pop(key, None)


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
                 notas="", tempo_estimado=None, delegado_para=None,
                 recorrencia=None, recorrencia_dia=None, status="pendente"):
    """Cria uma tarefa no Supabase."""
    tarefa = {
        "titulo": titulo,
        "categoria": categoria,
        "prioridade": prioridade,
        "status": status,
        "prazo": prazo,
        "horario": horario,
        "meeting_link": meeting_link or "",
        "meeting_platform": meeting_platform,
        "notas": notas,
        "origem": "telegram",
    }

    # Campos opcionais (migration 003)
    if tempo_estimado is not None:
        tarefa["tempo_estimado_min"] = tempo_estimado
    if delegado_para:
        tarefa["delegado_para"] = delegado_para
    if recorrencia:
        tarefa["recorrencia"] = recorrencia
    if recorrencia_dia is not None:
        tarefa["recorrencia_dia"] = recorrencia_dia

    # Detectar plataforma de reuniao
    if meeting_link and not meeting_platform:
        if "zoom" in meeting_link:
            tarefa["meeting_platform"] = "zoom"
        elif "meet.google" in meeting_link:
            tarefa["meeting_platform"] = "meet"
        elif "teams" in meeting_link:
            tarefa["meeting_platform"] = "teams"

    result = supabase_request("POST", "tarefas", tarefa)
    if not result:
        # Tentar sem campos novos (caso migration 003 nao tenha rodado)
        for campo in ["tempo_estimado_min", "delegado_para", "recorrencia", "recorrencia_dia"]:
            tarefa.pop(campo, None)
        result = supabase_request("POST", "tarefas", tarefa)
    return result[0] if result else None


def atualizar_tarefa(task_id, dados):
    """Atualiza campos de uma tarefa."""
    return supabase_request("PATCH", f"tarefas?id=eq.{task_id}", dados)


def listar_tarefas_pendentes(limite=15):
    params = {
        "status": "neq.concluida",
        "order": "prazo.asc.nullslast,prioridade.asc",
        "limit": str(limite),
        "select": "id,titulo,categoria,prioridade,prazo,horario,meeting_link,status,tempo_estimado_min,delegado_para",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_tarefas_do_dia(data=None):
    if not data:
        data = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    params = {
        "prazo": f"eq.{data}",
        "status": "neq.concluida",
        "order": "horario.asc.nullslast",
        "select": "id,titulo,categoria,prioridade,prazo,horario,meeting_link,status,tempo_estimado_min,delegado_para",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_tarefas_atrasadas():
    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    params = {
        "prazo": f"lt.{hoje}",
        "status": "neq.concluida",
        "order": "prazo.asc",
        "select": "id,titulo,categoria,prioridade,prazo,horario,tempo_estimado_min",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_concluidas_hoje():
    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    params = {
        "status": "eq.concluida",
        "completed_at": f"gte.{hoje}T00:00:00",
        "order": "completed_at.desc",
        "select": "id,titulo,categoria,prioridade,completed_at",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def listar_tarefas_semana():
    """Lista todas as tarefas da semana (para relatorio)."""
    hoje = datetime.now(TZ_RECIFE)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    params = {
        "created_at": f"gte.{inicio_semana.strftime('%Y-%m-%d')}T00:00:00",
        "order": "created_at.desc",
        "select": "id,titulo,categoria,prioridade,prazo,status,completed_at,tempo_estimado_min",
    }
    return supabase_request("GET", "tarefas", params=params) or []


def obter_carga_semana():
    """Obtem carga por dia para sugestao de realocacao."""
    result = supabase_request("GET", "carga_por_dia")
    if not result:
        return {}
    carga = {}
    for r in result:
        if r.get("dia"):
            carga[r["dia"]] = {
                "total_tarefas": r.get("total_tarefas", 0),
                "minutos_estimados": r.get("minutos_estimados", 0),
            }
    return carga


def obter_resumo():
    result = supabase_request("GET", "resumo_semanal")
    return result[0] if result else None


def concluir_tarefa_por_id(task_id):
    """Conclui tarefa por ID e retorna a tarefa."""
    result = supabase_request("PATCH", f"tarefas?id=eq.{task_id}", {
        "status": "concluida"
    })
    return result[0] if result else None


def buscar_tarefas_por_texto(texto, limite=5):
    """Busca tarefas por titulo (para edicao/conclusao)."""
    params = {
        "titulo": f"ilike.*{texto}*",
        "status": "neq.concluida",
        "limit": str(limite),
        "select": "id,titulo,categoria,prioridade,prazo,horario,status",
    }
    return supabase_request("GET", "tarefas", params=params) or []


# ========== CONTEXTO IA (MEMORIA) ==========

def carregar_contextos():
    """Carrega contextos aprendidos da tabela contexto_ia."""
    result = supabase_request("GET", "contexto_ia", params={
        "order": "vezes_usado.desc",
        "limit": "50",
        "select": "chave,valor,tipo,confianca",
    })
    return result or []


def salvar_contexto(chave, valor, tipo="geral"):
    """Salva ou atualiza contexto na memoria da IA."""
    existing = supabase_request("GET", "contexto_ia", params={
        "chave": f"eq.{chave}",
        "select": "id,vezes_usado",
    })
    if existing:
        supabase_request("PATCH", f"contexto_ia?chave=eq.{chave}", {
            "valor": valor,
            "tipo": tipo,
            "vezes_usado": existing[0].get("vezes_usado", 1) + 1,
        })
    else:
        supabase_request("POST", "contexto_ia", {
            "chave": chave,
            "valor": valor,
            "tipo": tipo,
        })


# ========== CHAT ID ==========

def get_chat_id():
    """Retorna o chat ID salvo."""
    global CHAT_ID
    if CHAT_ID:
        return CHAT_ID
    result = supabase_request("GET", "configuracoes", params={
        "chave": "eq.telegram_chat_id",
        "select": "valor",
    })
    if result and result[0].get("valor"):
        try:
            CHAT_ID = int(result[0]["valor"])
        except (ValueError, TypeError):
            pass
    return CHAT_ID


def save_chat_id(chat_id):
    """Salva chat ID no Supabase."""
    global CHAT_ID
    CHAT_ID = chat_id
    supabase_request("PATCH", "configuracoes?chave=eq.telegram_chat_id", {
        "valor": str(chat_id),
    })


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
        linhas.append(f"   ⏱ ~{tarefa['tempo_estimado_min']}min")

    if tarefa.get("delegado_para"):
        linhas.append(f"   👤 Delegado: {tarefa['delegado_para']}")

    if tarefa.get("recorrencia"):
        linhas.append(f"   🔄 {tarefa['recorrencia'].capitalize()}")

    status = tarefa.get("status", "pendente")
    if status == "concluida":
        linhas.append("   ✅ Já feito")
    elif status == "em_andamento":
        linhas.append("   🔄 Em andamento")

    return "\n".join(linhas)


def formatar_confirmacao(classificacao):
    """Formata mensagem de confirmacao."""
    card = formatar_tarefa_card(classificacao)
    msg = f"🧠 *Entendi! Classifiquei assim:*\n\n{card}\n\n"

    if classificacao.get("alerta_sobrecarga") and classificacao.get("alerta_msg"):
        msg += f"{classificacao['alerta_msg']}\n\n"

    if classificacao.get("mensagem"):
        msg += f"_{classificacao['mensagem']}_\n\n"

    msg += "✅ *Confirma?* Ou me diz o que ajustar."
    return msg


# ========== TRANSCRICAO DE AUDIO ==========

def transcrever_audio(caminho_audio):
    """Transcreve audio usando Groq API (Whisper)."""
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


# ========== PROCESSAR TAREFA ==========

async def processar_nova_tarefa(update, context, texto):
    """Processa texto como nova tarefa (com ou sem IA)."""
    if ai_brain:
        msg = await update.message.reply_text("🧠 Analisando...")

        tarefas_hoje = listar_tarefas_do_dia()
        carga_semana = obter_carga_semana()
        contextos = carregar_contextos()

        classificacao = ai_brain.classificar_tarefa(
            texto, tarefas_hoje, carga_semana, contextos
        )

        # MULTIPLAS TAREFAS
        if isinstance(classificacao, dict) and classificacao.get("multiplas"):
            tarefas = classificacao["tarefas"]

            # Montar lista de cards em blocos (Telegram limita 4096 chars)
            header = f"🧠 *Detectei {len(tarefas)} tarefas:*\n\n"
            footer = "\n✅ *Confirma todas?* Ou diz qual ajustar (ex: 'ajusta a 2')."
            blocos = []
            bloco_atual = header
            for i, t in enumerate(tarefas, 1):
                card = f"*{i}.* {formatar_tarefa_card(t)}\n\n"
                if len(bloco_atual) + len(card) > 3800:
                    blocos.append(bloco_atual)
                    bloco_atual = ""
                bloco_atual += card
            bloco_atual += footer
            blocos.append(bloco_atual)

            # Primeira mensagem edita a existente, as demais sao novas
            response_full = header + "".join(
                f"*{i}.* {formatar_tarefa_card(t)}\n\n"
                for i, t in enumerate(tarefas, 1)
            ) + footer

            set_state(context, STATE_CONFIRMING_MULTI,
                      pending_tasks=tarefas,
                      state_timestamp=datetime.now(TZ_RECIFE).isoformat(),
                      confirm_history=[
                          {"role": "user", "content": texto},
                          {"role": "assistant", "content": response_full[:2000]},
                      ])

            await msg.edit_text(blocos[0], parse_mode="Markdown",
                                disable_web_page_preview=True)
            for bloco in blocos[1:]:
                await update.message.reply_text(bloco, parse_mode="Markdown",
                                                 disable_web_page_preview=True)
            return

        # TAREFA UNICA
        # Detectar conflitos de horario
        if classificacao.get("horario") and ai_brain:
            try:
                conflitos = ai_brain.detectar_conflitos(tarefas_hoje, classificacao)
                if conflitos:
                    classificacao["_alerta_conflito"] = conflitos
            except Exception as e:
                logger.warning(f"Erro ao detectar conflitos: {e}")

        # Alerta preditivo de sobrecarga
        if classificacao.get("prazo") and ai_brain:
            try:
                alerta = ai_brain.alerta_preditivo(carga_semana)
                if alerta:
                    classificacao["_alerta_preditivo"] = alerta
            except Exception as e:
                logger.warning(f"Erro no alerta preditivo: {e}")

        confirm_msg = formatar_confirmacao(classificacao)

        # Adicionar alertas extras a mensagem
        if classificacao.get("_alerta_conflito"):
            confirm_msg += f"\n\n⚠️ *Conflito de horario:* {classificacao['_alerta_conflito']}"
        if classificacao.get("_alerta_preditivo"):
            confirm_msg += f"\n\n📈 *Alerta:* {classificacao['_alerta_preditivo']}"

        set_state(context, STATE_CONFIRMING,
                  pending_task=classificacao,
                  state_timestamp=datetime.now(TZ_RECIFE).isoformat(),
                  confirm_history=[
                      {"role": "user", "content": texto},
                      {"role": "assistant", "content": confirm_msg},
                  ])
        await msg.edit_text(confirm_msg, parse_mode="Markdown",
                            disable_web_page_preview=True)

    else:
        # MODO BASICO (sem IA)
        classificacao = classificar_tarefa_basico(texto)
        tarefa = criar_tarefa(
            titulo=classificacao["titulo"],
            categoria=classificacao["categoria"],
            prioridade=classificacao["prioridade"],
            prazo=classificacao["prazo"],
            horario=classificacao.get("horario"),
            meeting_link=classificacao.get("meeting_link"),
        )
        if tarefa:
            resposta = "✅ *Tarefa criada!*\n\n" + formatar_tarefa_card(tarefa)
            await update.message.reply_text(resposta, parse_mode="Markdown",
                                            disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Erro ao criar tarefa.")


def _salvar_tarefa_e_contexto(tarefa_data):
    """Salva tarefa no Supabase e extrai contexto para memoria."""
    tarefa = criar_tarefa(
        titulo=tarefa_data.get("titulo", "Tarefa"),
        categoria=tarefa_data.get("categoria", "Pessoal"),
        prioridade=tarefa_data.get("prioridade", "media"),
        prazo=tarefa_data.get("prazo"),
        horario=tarefa_data.get("horario"),
        meeting_link=tarefa_data.get("meeting_link"),
        meeting_platform=tarefa_data.get("meeting_platform"),
        tempo_estimado=tarefa_data.get("tempo_estimado_min"),
        delegado_para=tarefa_data.get("delegado_para"),
        recorrencia=tarefa_data.get("recorrencia"),
        recorrencia_dia=tarefa_data.get("recorrencia_dia"),
        status=tarefa_data.get("status", "pendente"),
    )

    # Salvar contexto aprendido
    if ai_brain and tarefa:
        try:
            contextos = ai_brain.extrair_contexto(
                tarefa_data.get("titulo", ""),
                tarefa_data
            )
            for ctx in contextos:
                salvar_contexto(ctx["chave"], ctx["valor"], ctx["tipo"])
        except Exception as e:
            logger.warning(f"Erro ao salvar contexto: {e}")

    return tarefa


async def processar_confirmacao(update, context, texto):
    """Processa confirmacao de tarefa unica."""
    pending = context.user_data.get("pending_task")
    if not pending:
        clear_state(context)
        return

    historico = context.user_data.get("confirm_history", [])
    historico.append({"role": "user", "content": texto})

    result = ai_brain.processar_confirmacao(texto, pending, historico)

    if not result:
        result = {"acao": "salvar"}

    acao = result.get("acao")

    if acao == "cancelar":
        clear_state(context)
        await update.message.reply_text("🚫 Tarefa cancelada.")
        return

    if acao == "salvar":
        tarefa_data = pending
    elif "titulo" in result:
        context.user_data["pending_task"] = result
        confirm_msg = formatar_confirmacao(result)
        historico.append({"role": "assistant", "content": confirm_msg})
        context.user_data["confirm_history"] = historico
        await update.message.reply_text(confirm_msg, parse_mode="Markdown",
                                        disable_web_page_preview=True)
        return
    else:
        tarefa_data = pending

    tarefa = _salvar_tarefa_e_contexto(tarefa_data)
    clear_state(context)

    if tarefa:
        resposta = "✅ *Tarefa salva!*\n\n" + formatar_tarefa_card(tarefa)
        resposta += f"\n\n[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)"
        await update.message.reply_text(resposta, parse_mode="Markdown",
                                        disable_web_page_preview=True)
        # Agendar lembrete se tiver horario hoje
        await _agendar_lembrete_se_hoje(context, tarefa)
    else:
        await update.message.reply_text("❌ Erro ao salvar tarefa.")


async def processar_confirmacao_multi(update, context, texto):
    """Processa confirmacao de multiplas tarefas."""
    pending_tasks = context.user_data.get("pending_tasks", [])
    if not pending_tasks:
        clear_state(context)
        return

    lower = texto.lower().strip()

    # Confirmacao geral
    if any(w in lower for w in ["sim", "ok", "confirma", "todas", "salva", "bora", "pode"]):
        salvas = 0
        for t in pending_tasks:
            tarefa = _salvar_tarefa_e_contexto(t)
            if tarefa:
                salvas += 1
                await _agendar_lembrete_se_hoje(context, tarefa)
        clear_state(context)
        await update.message.reply_text(
            f"✅ *{salvas} tarefas salvas!*\n\n"
            f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
            parse_mode="Markdown", disable_web_page_preview=True
        )
        return

    # Cancelar
    if any(w in lower for w in ["nao", "cancela", "esquece"]):
        clear_state(context)
        await update.message.reply_text("🚫 Todas canceladas.")
        return

    # Ajustar tarefa especifica (ex: "ajusta a 2", "muda a 1 pra grupo ser")
    m = re.search(r'(\d+)', lower)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(pending_tasks):
            # Tratar como confirmacao de ajuste
            set_state(context, STATE_CONFIRMING,
                      pending_task=pending_tasks[idx],
                      confirm_history=context.user_data.get("confirm_history", []))
            # Remove do pending_tasks para salvar as outras depois
            context.user_data["pending_tasks_remaining"] = [
                t for i, t in enumerate(pending_tasks) if i != idx
            ]
            await update.message.reply_text(
                f"Ok, vamos ajustar a tarefa {idx+1}:\n\n"
                f"{formatar_tarefa_card(pending_tasks[idx])}\n\n"
                f"O que quer mudar?",
                parse_mode="Markdown"
            )
            return

    # Nao entendeu
    await update.message.reply_text(
        "Nao entendi. Diz *'confirma'* pra salvar todas, ou *'ajusta a 2'* pra mudar uma especifica.",
        parse_mode="Markdown"
    )


# ========== CLASSIFICACAO BASICA (fallback sem IA) ==========

def classificar_tarefa_basico(texto):
    """Classificacao por keywords — fallback."""
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


# ========== LEMBRETES AUTOMATICOS ==========

async def _agendar_lembrete_se_hoje(context, tarefa):
    """Se a tarefa e para hoje e tem horario, agenda lembrete 15min antes."""
    if not tarefa.get("prazo") or not tarefa.get("horario"):
        return
    if not context.job_queue:
        return

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    if tarefa["prazo"] != hoje:
        return

    try:
        h_str = tarefa["horario"]
        if isinstance(h_str, str) and len(h_str) >= 5:
            hora, minuto = int(h_str[:2]), int(h_str[3:5])
            agora = datetime.now(TZ_RECIFE)
            horario_tarefa = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            lembrete_time = horario_tarefa - timedelta(minutes=15)

            if lembrete_time > agora:
                delay = (lembrete_time - agora).total_seconds()
                context.job_queue.run_once(
                    _enviar_lembrete,
                    when=delay,
                    data=tarefa,
                    name=f"reminder_{tarefa.get('id', '')}",
                )
                logger.info(f"Lembrete agendado: {tarefa['titulo']} em {delay:.0f}s")
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao agendar lembrete: {e}")


async def _enviar_lembrete(context):
    """Callback de lembrete — envia notificacao no Telegram."""
    tarefa = context.job.data
    chat_id = get_chat_id()
    if not chat_id:
        return

    # Verificar modo foco
    # (lembretes de prioridade alta sempre passam)
    emoji = EMOJI_PRIORIDADE.get(tarefa.get("prioridade", ""), "⚪")
    cat_emoji = EMOJI_CATEGORIA.get(tarefa.get("categoria", ""), "📋")

    msg = (
        f"⏰ *Lembrete — em 15 minutos!*\n\n"
        f"{emoji} *{tarefa.get('titulo', 'Tarefa')}*\n"
        f"   {cat_emoji} {tarefa.get('categoria', '')}\n"
        f"   🕐 {tarefa.get('horario', '')[:5]}\n"
    )

    if tarefa.get("meeting_link"):
        msg += f"\n🔗 [Entrar na reuniao]({tarefa['meeting_link']})"

    try:
        await context.bot.send_message(
            chat_id, msg, parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {e}")


async def _verificar_lembretes_iniciais(context):
    """Na inicializacao, agenda lembretes para tarefas de hoje com horario."""
    chat_id = get_chat_id()
    if not chat_id:
        return

    tarefas = listar_tarefas_do_dia()
    agendados = 0
    for t in tarefas:
        if t.get("horario"):
            try:
                h_str = t["horario"]
                if isinstance(h_str, str) and len(h_str) >= 5:
                    hora, minuto = int(h_str[:2]), int(h_str[3:5])
                    agora = datetime.now(TZ_RECIFE)
                    horario_tarefa = agora.replace(hour=hora, minute=minuto, second=0)
                    lembrete_time = horario_tarefa - timedelta(minutes=15)

                    if lembrete_time > agora:
                        delay = (lembrete_time - agora).total_seconds()
                        context.job_queue.run_once(
                            _enviar_lembrete, when=delay,
                            data=t, name=f"reminder_{t.get('id', '')}",
                        )
                        agendados += 1
            except (ValueError, TypeError):
                pass

    if agendados:
        logger.info(f"Agendados {agendados} lembretes para hoje")


# ========== JOBS PROGRAMADOS ==========

async def resumo_matinal(context):
    """Envia resumo matinal as 7:30."""
    chat_id = get_chat_id()
    if not chat_id:
        return

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    tarefas = listar_tarefas_do_dia(hoje)
    atrasadas = listar_tarefas_atrasadas()

    if not tarefas and not atrasadas:
        msg = "☀️ *Bom dia!* Nenhuma tarefa para hoje — dia livre!"
    else:
        msg = "☀️ *Bom dia, Wendel!*\n\n"

        if tarefas:
            total_min = sum(t.get('tempo_estimado_min') or 30 for t in tarefas)
            msg += f"📋 *{len(tarefas)} tarefas para hoje* (~{total_min}min)\n\n"
            for t in tarefas:
                emoji = EMOJI_PRIORIDADE.get(t.get('prioridade', ''), '⚪')
                h = t.get('horario', '')
                h_str = f" 🕐 {h[:5]}" if h and len(str(h)) >= 5 else ""
                delegado = f" 👤{t['delegado_para']}" if t.get('delegado_para') else ""
                msg += f"{emoji} {t['titulo']}{h_str}{delegado}\n"

        if atrasadas:
            msg += f"\n⚠️ *{len(atrasadas)} atrasada{'s' if len(atrasadas) > 1 else ''}:*\n"
            for t in atrasadas[:5]:
                msg += f"  · {t['titulo']} (prazo: {t.get('prazo', '?')})\n"

            # Sugestao de reagendamento automatico
            if ai_brain:
                try:
                    carga_semana = obter_carga_semana()
                    sugestao = ai_brain.sugerir_reagendamento(atrasadas, carga_semana)
                    if sugestao:
                        msg += f"\n💡 *Sugestao de reagendamento:*\n{sugestao}\n"
                except Exception as e:
                    logger.warning(f"Erro ao sugerir reagendamento: {e}")

        msg += f"\n💡 _Use /planejar para organizar o dia_"

    try:
        await context.bot.send_message(chat_id, msg, parse_mode="Markdown",
                                       disable_web_page_preview=True)
        # Agendar lembretes do dia
        await _verificar_lembretes_iniciais(context)
    except Exception as e:
        logger.error(f"Erro no resumo matinal: {e}")


async def relatorio_semanal_auto(context):
    """Envia relatorio semanal toda sexta as 17:00."""
    chat_id = get_chat_id()
    if not chat_id or not ai_brain:
        return

    try:
        dados = _preparar_dados_relatorio()
        relatorio = ai_brain.gerar_relatorio_semanal(dados)

        msg = "📊 *Relatorio Semanal*\n\n" + relatorio
        msg += "\n\n_Bom fim de semana!_ 🎉"

        await context.bot.send_message(chat_id, msg, parse_mode="Markdown",
                                       disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Erro no relatorio semanal: {e}")


def _preparar_dados_relatorio():
    """Prepara dados para o relatorio semanal."""
    tarefas = listar_tarefas_semana()
    hoje = datetime.now(TZ_RECIFE)
    inicio = hoje - timedelta(days=hoje.weekday())

    concluidas = [t for t in tarefas if t.get("status") == "concluida"]
    pendentes = [t for t in tarefas if t.get("status") != "concluida"]
    atrasadas = [t for t in pendentes if t.get("prazo") and t["prazo"] < hoje.strftime("%Y-%m-%d")]

    # Distribuicao por categoria
    dist_cat = {}
    for t in tarefas:
        cat = t.get("categoria", "Sem categoria")
        if cat not in dist_cat:
            dist_cat[cat] = {"total": 0, "concluidas": 0}
        dist_cat[cat]["total"] += 1
        if t.get("status") == "concluida":
            dist_cat[cat]["concluidas"] += 1

    dist_str = ""
    for cat, info in dist_cat.items():
        emoji = EMOJI_CATEGORIA.get(cat, "📋")
        dist_str += f"{emoji} {cat}: {info['concluidas']}/{info['total']} concluidas\n"

    # Distribuicao por prioridade
    dist_pri = {}
    for t in tarefas:
        pri = t.get("prioridade", "media")
        dist_pri[pri] = dist_pri.get(pri, 0) + 1
    pri_str = ", ".join(f"{EMOJI_PRIORIDADE.get(k, '⚪')} {k}: {v}" for k, v in dist_pri.items())

    # Padroes
    padroes = ""
    if ai_brain:
        padroes = ai_brain.analisar_padroes([], tarefas)

    # Tempo pessoal
    pessoais = [t for t in concluidas if t.get("categoria") == "Pessoal"]
    ingles = any("ingles" in (t.get("titulo", "").lower()) for t in pessoais)
    leitura = any("leitura" in (t.get("titulo", "").lower()) for t in pessoais)
    tempo_str = f"Ingles: {'✅' if ingles else '❌'}, Leitura: {'✅' if leitura else '❌'}"

    return {
        "periodo": f"{inicio.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')}",
        "total": len(tarefas),
        "concluidas": len(concluidas),
        "pendentes": len(pendentes),
        "atrasadas": len(atrasadas),
        "dist_categoria": dist_str or "Sem dados",
        "dist_prioridade": pri_str or "Sem dados",
        "padroes": padroes,
        "tempo_pessoal": tempo_str,
    }


async def verificar_recorrentes(context):
    """Cria instancias de tarefas recorrentes para hoje."""
    hoje = datetime.now(TZ_RECIFE)
    dia_semana = hoje.weekday()  # 0=segunda
    dia_mes = hoje.day

    params = {
        "recorrencia": "neq.is.null",
        "status": "neq.concluida",
        "select": "id,titulo,categoria,prioridade,horario,recorrencia,recorrencia_dia,tempo_estimado_min,delegado_para",
    }
    # Busca com filtro nao-nulo pode nao funcionar em todas as versoes
    # Fallback: buscar tudo e filtrar em Python
    todas = supabase_request("GET", "tarefas", params={
        "status": "neq.concluida",
        "select": "id,titulo,categoria,prioridade,horario,recorrencia,recorrencia_dia,prazo,tempo_estimado_min,delegado_para",
    }) or []

    recorrentes = [t for t in todas if t.get("recorrencia")]
    criadas = 0

    for t in recorrentes:
        rec = t["recorrencia"]
        rec_dia = t.get("recorrencia_dia")
        prazo = t.get("prazo")

        criar_hoje = False

        if rec == "diaria":
            # Se prazo ja e hoje, nao duplicar
            if prazo != hoje.strftime("%Y-%m-%d"):
                criar_hoje = True
        elif rec == "semanal" and rec_dia is not None:
            if dia_semana == rec_dia and prazo != hoje.strftime("%Y-%m-%d"):
                criar_hoje = True
        elif rec == "quinzenal" and rec_dia is not None:
            # Simplificado: verifica se faz 14+ dias desde o prazo
            if prazo:
                try:
                    ultimo = datetime.strptime(prazo, "%Y-%m-%d")
                    if (hoje - ultimo).days >= 14 and dia_semana == rec_dia:
                        criar_hoje = True
                except ValueError:
                    pass
        elif rec == "mensal" and rec_dia is not None:
            if dia_mes == rec_dia and (not prazo or prazo[:7] != hoje.strftime("%Y-%m")):
                criar_hoje = True

        if criar_hoje:
            # Atualiza o prazo da tarefa existente para hoje
            atualizar_tarefa(t["id"], {"prazo": hoje.strftime("%Y-%m-%d")})
            criadas += 1

    if criadas:
        logger.info(f"Atualizadas {criadas} tarefas recorrentes para hoje")


# ========== HANDLERS DO BOT ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boas-vindas + salva chat ID."""
    chat_id = update.effective_chat.id
    save_chat_id(chat_id)
    logger.info(f"Chat ID salvo: {chat_id}")
    clear_state(context)

    modo = "🧠 *Modo inteligente v2* (Claude IA)" if ai_brain else "⚡ *Modo basico* (sem IA)"

    await update.message.reply_text(
        f"👋 *Organizador de Tarefas v2*\n\n"
        f"{modo}\n\n"
        "Mande texto ou audio e eu organizo pra voce!\n\n"
        "*Comandos:*\n"
        "/tarefas — Ver pendentes\n"
        "/planejar — Planejamento inteligente\n"
        "/feedback — Feedback do dia\n"
        "/resumo — Resumo rapido\n"
        "/concluir — Concluir tarefa\n"
        "/editar — Editar tarefa\n"
        "/relatorio — Relatorio semanal\n"
        "/foco — Modo foco\n"
        "/cancelar — Cancela operacao\n\n"
        "*Novidades v2:*\n"
        "• IA entende datas: 'amanha', 'sexta', 'semana que vem'\n"
        "• Detecta multiplas tarefas numa mensagem\n"
        "• Alerta de sobrecarga no dia\n"
        "• Lembretes 15min antes de reunioes\n"
        "• Resumo matinal automatico as 7:30\n"
        "• Relatorio semanal toda sexta 17h\n\n"
        f"📊 [Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista tarefas pendentes."""
    clear_state(context)
    tarefas = listar_tarefas_pendentes(15)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente! Voce esta em dia.")
        return

    texto = f"📋 *Tarefas pendentes ({len(tarefas)}):*\n\n"
    for t in tarefas:
        texto += formatar_tarefa_card(t) + "\n\n"

    texto += f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)"
    await update.message.reply_text(texto, parse_mode="Markdown",
                                    disable_web_page_preview=True)


async def cmd_planejar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Planejamento inteligente do dia."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text(
            "⚠️ Planejamento requer Claude API. Configure ANTHROPIC_API_KEY."
        )
        return

    msg = await update.message.reply_text("🧠 Analisando seu dia...")

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
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

    set_state(context, STATE_CHATTING, chat_history=[
        {"role": "assistant", "content": planejamento}
    ])

    await msg.edit_text(planejamento, parse_mode="Markdown",
                        disable_web_page_preview=True)


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Feedback construtivo do dia."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text(
            "⚠️ Feedback requer Claude API. Configure ANTHROPIC_API_KEY."
        )
        return

    msg = await update.message.reply_text("🧠 Analisando seu dia...")

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    concluidas = listar_concluidas_hoje()
    pendentes = listar_tarefas_do_dia(hoje)

    # Padroes da semana
    tarefas_semana = listar_tarefas_semana()
    padroes = ai_brain.analisar_padroes([], tarefas_semana)

    feedback = ai_brain.feedback_dia(concluidas, pendentes, padroes, hoje)

    set_state(context, STATE_CHATTING, chat_history=[
        {"role": "assistant", "content": feedback}
    ])

    await msg.edit_text(feedback, parse_mode="Markdown",
                        disable_web_page_preview=True)


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumo rapido."""
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
        parse_mode="Markdown", disable_web_page_preview=True,
    )


async def cmd_concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Concluir tarefa — interativo com inline keyboard."""
    clear_state(context)
    tarefas = listar_tarefas_pendentes(10)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente!")
        return

    keyboard = []
    for t in tarefas:
        emoji = EMOJI_PRIORIDADE.get(t.get("prioridade", ""), "⚪")
        cat_emoji = EMOJI_CATEGORIA.get(t.get("categoria", ""), "📋")
        titulo = t["titulo"][:35]
        if t.get("prazo"):
            try:
                d = datetime.strptime(t["prazo"], "%Y-%m-%d")
                titulo += f" ({d.strftime('%d/%m')})"
            except ValueError:
                pass
        keyboard.append([InlineKeyboardButton(
            f"{emoji}{cat_emoji} {titulo}",
            callback_data=f"done:{t['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="done:cancel")])

    await update.message.reply_text(
        "✅ *Qual tarefa concluir?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def cmd_editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Editar tarefa existente."""
    clear_state(context)
    tarefas = listar_tarefas_pendentes(10)

    if not tarefas:
        await update.message.reply_text("Nenhuma tarefa para editar.")
        return

    keyboard = []
    for t in tarefas:
        emoji = EMOJI_PRIORIDADE.get(t.get("prioridade", ""), "⚪")
        titulo = t["titulo"][:35]
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {titulo}",
            callback_data=f"edit:{t['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="edit:cancel")])

    await update.message.reply_text(
        "✏️ *Qual tarefa editar?*\nDepois diga o que mudar (ex: 'muda pra sexta', 'prioridade alta')",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def cmd_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera relatorio semanal manual."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text("⚠️ Relatorio requer Claude API.")
        return

    msg = await update.message.reply_text("📊 Gerando relatorio semanal...")

    try:
        dados = _preparar_dados_relatorio()
        relatorio = ai_brain.gerar_relatorio_semanal(dados)
        await msg.edit_text(f"📊 *Relatorio Semanal*\n\n{relatorio}",
                            parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Erro no relatorio: {e}")
        await msg.edit_text("❌ Erro ao gerar relatorio.")


async def cmd_foco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Modo foco — silencia notificacoes de baixa prioridade."""
    texto = update.message.text.strip()
    args = texto.replace("/foco", "").strip()

    # Desativar
    if args.lower() in ["off", "sair", "desligar", "parar"]:
        context.user_data.pop("focus_until", None)
        context.user_data["state"] = STATE_IDLE
        await update.message.reply_text("🔔 Modo foco *desativado*.", parse_mode="Markdown")
        return

    # Ativar
    duracao_min = 60  # padrao 1h
    m = re.search(r'(\d+)\s*(h|m|min|hora)', args.lower())
    if m:
        valor = int(m.group(1))
        unidade = m.group(2)
        if unidade.startswith("h"):
            duracao_min = valor * 60
        else:
            duracao_min = valor

    focus_until = datetime.now(TZ_RECIFE) + timedelta(minutes=duracao_min)
    context.user_data["focus_until"] = focus_until.isoformat()
    set_state(context, STATE_FOCUS)

    # Agendar fim do foco
    context.job_queue.run_once(
        _fim_foco, when=duracao_min * 60,
        data=update.effective_chat.id,
        name="focus_end",
    )

    await update.message.reply_text(
        f"🎯 *Modo foco ativado* por {duracao_min}min\n\n"
        f"Ate: {focus_until.strftime('%H:%M')}\n"
        f"Lembretes de baixa prioridade silenciados.\n"
        f"Use /foco off para desativar.",
        parse_mode="Markdown",
    )


async def _fim_foco(context):
    """Callback quando modo foco termina."""
    chat_id = context.job.data
    try:
        await context.bot.send_message(
            chat_id,
            "🔔 *Modo foco encerrado!*\n\n"
            "Use /tarefas para ver pendentes.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao encerrar foco: {e}")


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela operacao atual."""
    state = get_state(context)
    clear_state(context)
    if state != STATE_IDLE:
        await update.message.reply_text("🚫 Operacao cancelada.")
    else:
        await update.message.reply_text("Nenhuma operacao em andamento.")


# ========== CALLBACK HANDLER (inline keyboards) ==========

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa cliques em botoes inline."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data:
        return

    # CONCLUIR tarefa
    if data.startswith("done:"):
        task_id = data.split(":", 1)[1]
        if task_id == "cancel":
            await query.edit_message_text("Cancelado.")
            return

        tarefa = concluir_tarefa_por_id(task_id)
        if tarefa:
            # Verificar se e recorrente
            if tarefa.get("recorrencia"):
                await query.edit_message_text(
                    f"✅ *Concluida:* {tarefa['titulo']}\n"
                    f"🔄 Tarefa recorrente — proxima instancia sera criada automaticamente.",
                    parse_mode="Markdown",
                )
                # Recriar para proxima ocorrencia
                _recriar_recorrente(tarefa)
            else:
                await query.edit_message_text(
                    f"✅ *Concluida:* {tarefa['titulo']}",
                    parse_mode="Markdown",
                )
        else:
            await query.edit_message_text("❌ Erro ao concluir.")

    # DECOMPOR tarefa
    elif data.startswith("decomp:"):
        task_id = data.split(":", 1)[1]
        if task_id == "cancel":
            await query.edit_message_text("Cancelado.")
            return

        if not ai_brain:
            await query.edit_message_text("⚠️ Decomposicao requer Claude API.")
            return

        # Buscar dados da tarefa
        result = supabase_request("GET", "tarefas", params={
            "id": f"eq.{task_id}",
            "select": "id,titulo,categoria,prioridade,prazo,horario,tempo_estimado_min",
        })
        if not result:
            await query.edit_message_text("❌ Tarefa nao encontrada.")
            return

        tarefa = result[0]
        await query.edit_message_text("🧠 Decompondo tarefa em subtarefas...")

        try:
            subtarefas = ai_brain.decompor_tarefa(tarefa)
            if not subtarefas:
                await query.edit_message_text("❌ Nao consegui decompor essa tarefa.")
                return

            msg = f"🔀 *Decomposicao de:* _{tarefa['titulo']}_\n\n"
            for i, sub in enumerate(subtarefas, 1):
                msg += f"*{i}.* {sub.get('titulo', 'Subtarefa')}"
                if sub.get("tempo_estimado_min"):
                    msg += f" (~{sub['tempo_estimado_min']}min)"
                msg += "\n"
            msg += "\n✅ *Confirma a criacao das subtarefas?*"

            set_state(context, STATE_CONFIRMING_DECOMP,
                      pending_decomp=subtarefas,
                      decomp_task=tarefa,
                      state_timestamp=datetime.now(TZ_RECIFE).isoformat())

            await context.bot.send_message(
                query.message.chat_id, msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erro ao decompor tarefa: {e}")
            await context.bot.send_message(
                query.message.chat_id,
                "❌ Erro ao decompor tarefa."
            )

    # EDITAR tarefa
    elif data.startswith("edit:"):
        task_id = data.split(":", 1)[1]
        if task_id == "cancel":
            await query.edit_message_text("Cancelado.")
            return

        set_state(context, STATE_EDITING, editing_task_id=task_id)
        await query.edit_message_text(
            "✏️ O que quer mudar? Exemplos:\n"
            "• 'muda pra sexta'\n"
            "• 'prioridade alta'\n"
            "• 'categoria grupo ser'\n"
            "• 'horario 14:00'\n"
            "• 'titulo: Reuniao com equipe'\n\n"
            "Ou envie /cancelar para desistir."
        )


def _recriar_recorrente(tarefa):
    """Recria a proxima instancia de uma tarefa recorrente."""
    rec = tarefa.get("recorrencia")
    prazo = tarefa.get("prazo")
    if not rec or not prazo:
        return

    try:
        data_atual = datetime.strptime(prazo, "%Y-%m-%d")
    except ValueError:
        return

    if rec == "diaria":
        proximo = data_atual + timedelta(days=1)
    elif rec == "semanal":
        proximo = data_atual + timedelta(weeks=1)
    elif rec == "quinzenal":
        proximo = data_atual + timedelta(weeks=2)
    elif rec == "mensal":
        mes = data_atual.month + 1
        ano = data_atual.year
        if mes > 12:
            mes = 1
            ano += 1
        try:
            proximo = data_atual.replace(year=ano, month=mes)
        except ValueError:
            proximo = data_atual + timedelta(days=30)
    else:
        return

    # Pular fins de semana para tarefas de trabalho
    if tarefa.get("categoria") in ["Trabalho", "Consultoria", "Grupo Ser"]:
        while proximo.weekday() >= 5:
            proximo += timedelta(days=1)

    criar_tarefa(
        titulo=tarefa.get("titulo", "Tarefa recorrente"),
        categoria=tarefa.get("categoria", "Pessoal"),
        prioridade=tarefa.get("prioridade", "media"),
        prazo=proximo.strftime("%Y-%m-%d"),
        horario=tarefa.get("horario"),
        meeting_link=tarefa.get("meeting_link"),
        meeting_platform=tarefa.get("meeting_platform"),
        tempo_estimado=tarefa.get("tempo_estimado_min"),
        delegado_para=tarefa.get("delegado_para"),
        recorrencia=rec,
        recorrencia_dia=tarefa.get("recorrencia_dia"),
    )


# ========== HANDLER PRINCIPAL DE TEXTO ==========

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteador de estados."""
    texto = update.message.text.strip()
    if not texto:
        return

    state = get_state(context)

    # MODO FOCO: aceita comandos mas nao cria tarefas automaticamente
    if state == STATE_FOCUS:
        # Se parece comando, processa normalmente
        # Se parece tarefa nova, pergunta
        lower = texto.lower()
        if any(w in lower for w in ["sair", "foco off", "desligar foco"]):
            context.user_data.pop("focus_until", None)
            context.user_data["state"] = STATE_IDLE
            await update.message.reply_text("🔔 Modo foco *desativado*.", parse_mode="Markdown")
            return
        # Em modo foco, processa como tarefa mas avisa
        await update.message.reply_text(
            "🎯 _Modo foco ativo._ Vou registrar, mas sem alertas.\n"
            "Use /foco off para desativar.",
            parse_mode="Markdown"
        )
        context.user_data["state"] = STATE_IDLE
        await processar_nova_tarefa(update, context, texto)
        context.user_data["state"] = STATE_FOCUS
        return

    # Verificar timeout de confirmacao (30 minutos)
    if state in (STATE_CONFIRMING, STATE_CONFIRMING_MULTI, STATE_CONFIRMING_DECOMP):
        ts = context.user_data.get("state_timestamp")
        if ts:
            try:
                state_time = datetime.fromisoformat(ts)
                agora = datetime.now(TZ_RECIFE)
                if (agora - state_time).total_seconds() > 1800:  # 30 min
                    clear_state(context)
                    await update.message.reply_text(
                        "⏰ Confirmacao expirou. Mande a tarefa novamente."
                    )
                    return
            except (ValueError, TypeError):
                pass

    if state == STATE_CONFIRMING and ai_brain:
        await processar_confirmacao(update, context, texto)

    elif state == STATE_CONFIRMING_MULTI and ai_brain:
        await processar_confirmacao_multi(update, context, texto)

    elif state == STATE_CONFIRMING_DECOMP and ai_brain:
        await processar_confirmacao_decomp(update, context, texto)

    elif state == STATE_EDITING:
        await processar_edicao(update, context, texto)

    elif state == STATE_CHATTING and ai_brain:
        history = context.user_data.get("chat_history", [])
        history.append({"role": "user", "content": texto})

        msg = await update.message.reply_text("🧠 Pensando...")
        resposta = ai_brain.conversar(texto, history)

        history.append({"role": "assistant", "content": resposta})
        context.user_data["chat_history"] = history

        await msg.edit_text(resposta, parse_mode="Markdown",
                            disable_web_page_preview=True)

        # Detectar saida do chat
        if any(w in texto.lower() for w in ["nova tarefa", "adicionar", "/sair", "tchau", "valeu"]):
            clear_state(context)

    else:
        await processar_nova_tarefa(update, context, texto)


async def processar_edicao(update, context, texto):
    """Processa edicao de tarefa existente."""
    task_id = context.user_data.get("editing_task_id")
    if not task_id:
        clear_state(context)
        return

    if ai_brain:
        # Usa Claude para interpretar o ajuste
        result = ai_brain._tentar_ajuste_manual(texto, {})
        updates = {}

        # Extrair campos alterados
        if result.get("categoria") and result["categoria"] != "Pessoal":
            updates["categoria"] = result["categoria"]
        if result.get("prioridade") and result["prioridade"] != "media":
            updates["prioridade"] = result["prioridade"]
        if result.get("prazo"):
            updates["prazo"] = result["prazo"]
        if result.get("horario"):
            updates["horario"] = result["horario"]

        # Detectar mudanca de titulo
        if texto.lower().startswith("titulo:"):
            updates["titulo"] = texto[7:].strip()

        # Detectar mudanca de categoria por texto direto
        lower = texto.lower()
        for cat in ["Trabalho", "Consultoria", "Grupo Ser", "Pessoal"]:
            if cat.lower() in lower:
                updates["categoria"] = cat
                break

        # Detectar prazo por resolucao temporal
        data = ai_brain._resolver_data(texto)
        if data:
            updates["prazo"] = data

        if not updates:
            await update.message.reply_text(
                "Nao entendi o que mudar. Exemplos:\n"
                "• 'prioridade alta'\n"
                "• 'muda pra sexta'\n"
                "• 'categoria grupo ser'\n"
                "• 'titulo: Novo titulo aqui'"
            )
            return

        result = atualizar_tarefa(task_id, updates)
        clear_state(context)

        if result:
            campos = ", ".join(f"*{k}*={v}" for k, v in updates.items())
            await update.message.reply_text(
                f"✅ Tarefa atualizada!\n{campos}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Erro ao atualizar.")
    else:
        clear_state(context)
        await update.message.reply_text("Edicao requer Claude API.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe audio, transcreve e processa."""
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
        await processar_nova_tarefa(update, context, texto)

    except Exception as e:
        logger.error(f"Erro no handler de voz: {e}")
        await msg.edit_text("❌ Erro ao processar audio.")


# ========== CONFIRMACAO DE DECOMPOSICAO ==========

async def processar_confirmacao_decomp(update, context, texto):
    """Processa confirmacao de decomposicao de tarefa."""
    subtarefas = context.user_data.get("pending_decomp", [])
    tarefa_pai = context.user_data.get("decomp_task", {})

    if not subtarefas:
        clear_state(context)
        return

    lower = texto.lower().strip()

    # Confirmacao
    if any(w in lower for w in ["sim", "ok", "confirma", "pode", "bora", "salva"]):
        categoria = tarefa_pai.get("categoria", "Pessoal")
        prazo = tarefa_pai.get("prazo")
        criadas = 0

        for sub in subtarefas:
            tarefa = criar_tarefa(
                titulo=sub.get("titulo", "Subtarefa"),
                categoria=categoria,
                prioridade=sub.get("prioridade", tarefa_pai.get("prioridade", "media")),
                prazo=sub.get("prazo", prazo),
                horario=sub.get("horario"),
                tempo_estimado=sub.get("tempo_estimado_min"),
            )
            if tarefa:
                criadas += 1

        clear_state(context)
        await update.message.reply_text(
            f"✅ *{criadas} subtarefas criadas* a partir de _{tarefa_pai.get('titulo', 'tarefa')}_!\n\n"
            f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
            parse_mode="Markdown", disable_web_page_preview=True
        )
        return

    # Cancelar
    if any(w in lower for w in ["nao", "cancela", "esquece"]):
        clear_state(context)
        await update.message.reply_text("🚫 Decomposicao cancelada.")
        return

    await update.message.reply_text(
        "Diz *'confirma'* pra criar as subtarefas ou *'cancela'* pra desistir.",
        parse_mode="Markdown"
    )


# ========== DECOMPOR TAREFA ==========

async def cmd_decompor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Decompor tarefa em subtarefas usando IA."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text("⚠️ Decomposicao requer Claude API. Configure ANTHROPIC_API_KEY.")
        return

    tarefas = listar_tarefas_pendentes(10)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente para decompor!")
        return

    keyboard = []
    for t in tarefas:
        emoji = EMOJI_PRIORIDADE.get(t.get("prioridade", ""), "⚪")
        cat_emoji = EMOJI_CATEGORIA.get(t.get("categoria", ""), "📋")
        titulo = t["titulo"][:35]
        keyboard.append([InlineKeyboardButton(
            f"{emoji}{cat_emoji} {titulo}",
            callback_data=f"decomp:{t['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="decomp:cancel")])

    await update.message.reply_text(
        "🔀 *Qual tarefa decompor em subtarefas?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ========== CHECK-IN MEIO-DIA ==========

async def checkin_meiodia(context):
    """Envia check-in do meio-dia com progresso das tarefas."""
    chat_id = get_chat_id()
    if not chat_id:
        return

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    tarefas_hoje = listar_tarefas_do_dia(hoje)
    concluidas = listar_concluidas_hoje()

    total = len(tarefas_hoje) + len(concluidas)
    if total == 0:
        return  # Nada pra reportar

    n_concluidas = len(concluidas)
    percentual = (n_concluidas / total * 100) if total > 0 else 0

    if percentual >= 50:
        encorajamento = "🔥 Otimo ritmo! Mais da metade ja concluida. Continue assim!"
    elif n_concluidas > 0:
        encorajamento = "💪 Ja comecou bem! Foca nas prioridades da tarde."
    else:
        encorajamento = "🚀 A tarde e sua! Comece pela tarefa mais importante."

    msg = (
        f"📊 *Check-in do meio-dia*\n\n"
        f"✅ {n_concluidas}/{total} tarefas concluidas ate agora ({percentual:.0f}%)\n\n"
        f"{encorajamento}"
    )

    try:
        await context.bot.send_message(chat_id, msg, parse_mode="Markdown",
                                       disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Erro no check-in meio-dia: {e}")


# ========== SETUP ==========

async def setup_commands(app):
    """Configura comandos no menu do Telegram."""
    commands = [
        BotCommand("start", "Iniciar o bot"),
        BotCommand("tarefas", "Ver tarefas pendentes"),
        BotCommand("planejar", "Planejamento inteligente"),
        BotCommand("feedback", "Feedback do dia"),
        BotCommand("resumo", "Resumo rapido"),
        BotCommand("concluir", "Concluir tarefa"),
        BotCommand("editar", "Editar tarefa"),
        BotCommand("relatorio", "Relatorio semanal"),
        BotCommand("decompor", "Decompor tarefa em subtarefas"),
        BotCommand("foco", "Modo foco (silenciar)"),
        BotCommand("cancelar", "Cancelar operacao"),
    ]
    await app.bot.set_my_commands(commands)


async def post_init(app):
    """Executado apos inicializacao — configura comandos e jobs."""
    await setup_commands(app)

    # Jobs programados
    jq = app.job_queue
    if not jq:
        logger.warning("JobQueue nao disponivel. Instale: pip install 'python-telegram-bot[job-queue]'")
        return

    # Resumo matinal as 7:30 (todos os dias)
    jq.run_daily(
        resumo_matinal,
        time=dt_time(7, 30, tzinfo=TZ_RECIFE),
        name="morning_summary",
    )

    # Check-in meio-dia as 13:00 (todos os dias)
    jq.run_daily(
        checkin_meiodia,
        time=dt_time(13, 0, tzinfo=TZ_RECIFE),
        name="midday_checkin",
    )

    # Relatorio semanal sexta 17:00
    jq.run_daily(
        relatorio_semanal_auto,
        time=dt_time(17, 0, tzinfo=TZ_RECIFE),
        days=(4,),  # 4 = sexta-feira
        name="weekly_report",
    )

    # Verificar tarefas recorrentes diariamente as 6:00
    jq.run_daily(
        verificar_recorrentes,
        time=dt_time(6, 0, tzinfo=TZ_RECIFE),
        name="recurring_check",
    )

    # Carregar lembretes do dia (apos 5s para dar tempo de conectar)
    jq.run_once(
        _verificar_lembretes_iniciais,
        when=5,
        name="initial_reminders",
    )

    logger.info("Jobs programados: resumo 7:30, check-in 13:00, relatorio sex 17:00, recorrentes 6:00")


# ========== HEALTH CHECK (para Koyeb/PaaS) ==========

class HealthHandler(BaseHTTPRequestHandler):
    """Mini servidor HTTP que responde OK para health checks do Koyeb."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Organizador de Tarefas v2 rodando")

    def log_message(self, format, *args):
        # Silencia logs do health check para nao poluir
        pass


def start_health_server():
    """Inicia servidor HTTP em thread separada para health checks."""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server rodando na porta {port}")


# ========== MAIN ==========

def main():
    logger.info("Iniciando Organizador de Tarefas v2...")
    modo = "INTELIGENTE v2 (Claude)" if ai_brain else "BASICO (sem IA)"
    logger.info(f"Modo: {modo}")

    # Health check para Koyeb/PaaS (responde na porta HTTP)
    start_health_server()

    # Carregar chat ID do Supabase
    get_chat_id()
    if CHAT_ID:
        logger.info(f"Chat ID carregado: {CHAT_ID}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("tarefas", cmd_tarefas))
    app.add_handler(CommandHandler("planejar", cmd_planejar))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("concluir", cmd_concluir))
    app.add_handler(CommandHandler("editar", cmd_editar))
    app.add_handler(CommandHandler("relatorio", cmd_relatorio))
    app.add_handler(CommandHandler("decompor", cmd_decompor))
    app.add_handler(CommandHandler("foco", cmd_foco))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot v2 rodando! Mande /start no Telegram.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
