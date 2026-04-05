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
  /energia   — Registrar nivel de energia (1-5)
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
import urllib.parse
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
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    print("ERRO: Preencha TELEGRAM_BOT_TOKEN, SUPABASE_URL e SUPABASE_SERVICE_KEY no .env")
    sys.exit(1)

BOT_USER_ID = os.getenv("BOT_USER_ID")  # UUID do dono no Supabase Auth

if os.getenv("SUPABASE_SERVICE_KEY"):
    print("Usando service_role key (ignora RLS)")
    if not BOT_USER_ID:
        print("AVISO: BOT_USER_ID não configurado. Registros criados pelo bot ficarão sem dono.")
elif os.getenv("SUPABASE_ANON_KEY"):
    print("AVISO: Usando anon key. Com RLS ativo, o bot pode não ter acesso. Configure SUPABASE_SERVICE_KEY.")

if not GROQ_API_KEY:
    print("AVISO: GROQ_API_KEY nao configurada. Transcricao de audio desabilitada.")

# Calendar sync
from calendar_sync import (
    build_google_auth_url, build_microsoft_auth_url,
    sync_all_calendars, get_upcoming_events,
    _load_tokens, _save_tokens, _verify_state,
    exchange_google_code, exchange_microsoft_code,
    create_google_event,
)

# IA: importar cerebro (Gemini gratuito como prioridade, Claude como alternativa)
ai_brain = None
if GEMINI_API_KEY:
    from ai_brain import AIBrain
    ai_brain = AIBrain(GEMINI_API_KEY, provider="gemini")
    print("Gemini API conectada — modo inteligente v2 ativado (free tier)!")
elif ANTHROPIC_API_KEY:
    from ai_brain import AIBrain
    ai_brain = AIBrain(ANTHROPIC_API_KEY, provider="claude")
    print("Claude API conectada — modo inteligente v2 ativado!")
else:
    print("AVISO: Nenhuma API de IA configurada (GEMINI_API_KEY ou ANTHROPIC_API_KEY). Bot em modo basico.")

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
STATE_REFLEXAO = "reflexao"  # Reflexao noturna
STATE_AGUARDANDO_ANEXO = "aguardando_anexo"  # Aguardando conteudo do anexo


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
                "pending_decomp", "decomp_task", "state_timestamp",
                "reflexao_timestamp", "titulo_anexo"]:
        context.user_data.pop(key, None)


# ========== SUPABASE HELPERS ==========

def supabase_request(method, endpoint, data=None, params=None, extra_headers=None):
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
    if extra_headers:
        headers.update(extra_headers)

    # Injetar user_id em inserts e updates (service_role não tem auth.uid())
    if data and BOT_USER_ID and method in ("POST", "PATCH"):
        if isinstance(data, dict) and "user_id" not in data:
            data["user_id"] = BOT_USER_ID

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


def detectar_duplicatas(titulo_novo, prazo_novo=None, tarefas_existentes=None):
    """Detecta tarefas similares já existentes para evitar duplicatas.

    Retorna lista de tarefas similares (vazia se nenhuma).
    Usa SequenceMatcher para comparação fuzzy de títulos.
    """
    from difflib import SequenceMatcher

    if not titulo_novo:
        return []

    if not tarefas_existentes:
        # Buscar tarefas pendentes dos próximos 7 dias
        hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
        fim = (datetime.now(TZ_RECIFE) + timedelta(days=7)).strftime("%Y-%m-%d")
        tarefas_existentes = supabase_request("GET", "tarefas", params={
            "status": "neq.concluida",
            "prazo": f"gte.{hoje}",
            "order": "prazo.asc",
            "select": "id,titulo,categoria,prioridade,prazo,horario,status",
        }) or []

    titulo_lower = titulo_novo.lower().strip()
    if not titulo_lower:
        return []

    similares = []

    for t in tarefas_existentes:
        titulo_existente = (t.get("titulo") or "").lower().strip()
        if not titulo_existente:
            continue

        # Comparação exata
        if titulo_lower == titulo_existente:
            t["_similaridade"] = 100
            t["_tipo_match"] = "exata"
            similares.append(t)
            continue

        # Comparação fuzzy
        ratio = SequenceMatcher(None, titulo_lower, titulo_existente).ratio()
        if ratio >= 0.75:
            t["_similaridade"] = round(ratio * 100)
            t["_tipo_match"] = "similar"
            similares.append(t)
            continue

        # Verificar se um contém o outro
        if len(titulo_lower) > 5 and len(titulo_existente) > 5:
            if titulo_lower in titulo_existente or titulo_existente in titulo_lower:
                t["_similaridade"] = 85
                t["_tipo_match"] = "contida"
                similares.append(t)
                continue

    # Se tem prazo, priorizar duplicatas no mesmo dia
    if prazo_novo and similares:
        similares.sort(key=lambda x: (
            0 if x.get("prazo") == prazo_novo else 1,
            -x.get("_similaridade", 0)
        ))

    return similares


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


async def cmd_status(update, context):
    """Diagnostico do bot — verifica se IA esta funcionando."""
    info = []
    info.append("🔧 *Diagnóstico do Bot*\n")

    # Provider de IA
    if ai_brain:
        info.append(f"🧠 IA: *{ai_brain.provider.upper()}*")
        # Teste rapido de chamada
        try:
            test_resp = ai_brain._call_llm(
                "Responda apenas: OK",
                [{"role": "user", "content": "Teste de conexao. Responda apenas: OK"}],
                max_tokens=10,
            )
            if test_resp:
                info.append(f"✅ API respondendo: {test_resp[:50]}")
            else:
                info.append("❌ API NÃO respondeu (retornou None)")
        except Exception as e:
            info.append(f"❌ Erro ao chamar API: {e}")
    else:
        info.append("⚠️ IA: *DESATIVADA* (sem GEMINI_API_KEY ou ANTHROPIC_API_KEY)")

    # Env vars
    info.append(f"\n📋 *Variáveis:*")
    info.append(f"  GEMINI\\_API\\_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    info.append(f"  ANTHROPIC\\_API\\_KEY: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    info.append(f"  GROQ\\_API\\_KEY: {'✅' if GROQ_API_KEY else '❌'}")
    info.append(f"  SUPABASE: {'✅' if SUPABASE_URL else '❌'}")

    await update.message.reply_text("\n".join(info), parse_mode="Markdown")


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
        linhas.append(f"   🔗 [Entrar na reunião]({tarefa['meeting_link']})")

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

    # Badge de duplicata, se detectada
    if isinstance(tarefa, dict) and tarefa.get("_duplicatas"):
        for d in tarefa["_duplicatas"][:1]:
            linhas.append(f"   ⚠️ _Similar a: {d.get('titulo')} ({d.get('prazo', 'sem data')})_")

    return "\n".join(linhas)


def formatar_confirmacao(classificacao):
    """Formata mensagem de confirmação."""
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

            # Verificar duplicatas para cada tarefa do lote
            todas_pendentes = supabase_request("GET", "tarefas", params={
                "status": "neq.concluida",
                "order": "prazo.asc",
                "select": "id,titulo,categoria,prioridade,prazo,horario,status",
            }) or []

            tarefas_com_aviso = []
            for t in tarefas:
                dups = detectar_duplicatas(t.get("titulo", ""), t.get("prazo"), todas_pendentes)
                if dups:
                    t["_duplicatas"] = dups[:2]
                tarefas_com_aviso.append(t)
            tarefas = tarefas_com_aviso

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

        # Verificar duplicatas antes de confirmar
        duplicatas = detectar_duplicatas(
            classificacao.get("titulo", ""),
            classificacao.get("prazo"),
        )
        if duplicatas:
            classificacao["_duplicatas"] = duplicatas

        confirm_msg = formatar_confirmacao(classificacao)

        # Adicionar alertas extras a mensagem
        if classificacao.get("_duplicatas"):
            dup_list = classificacao["_duplicatas"][:3]  # Máximo 3
            confirm_msg += "\n\n⚠️ *Possível duplicata encontrada:*\n"
            for d in dup_list:
                prazo_d = d.get("prazo", "sem data")
                confirm_msg += f"  • _{d.get('titulo')}_ ({prazo_d}) — {d.get('_similaridade')}% similar\n"
            confirm_msg += "\nDeseja criar mesmo assim?"
        if classificacao.get("_alerta_conflito"):
            confirm_msg += f"\n\n⚠️ *Conflito de horário:* {classificacao['_alerta_conflito']}"
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
            # Criar evento no Google Calendar (modo basico)
            if classificacao.get("prazo"):
                try:
                    google_tokens = _load_tokens("google")
                    if google_tokens:
                        event_id = create_google_event(
                            titulo=classificacao["titulo"],
                            data=classificacao["prazo"],
                            horario_inicio=classificacao.get("horario"),
                        )
                        if event_id:
                            resposta += "\n\n📅 Adicionado ao Google Calendar"
                except Exception as e:
                    logger.warning(f"Erro ao criar evento no Google Calendar (modo basico): {e}")
            await update.message.reply_text(resposta, parse_mode="Markdown",
                                            disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Erro ao criar tarefa.")


def _salvar_tarefa_e_contexto(tarefa_data):
    """Salva tarefa no Supabase e extrai contexto para memoria.

    Retorna tupla (tarefa, google_calendar_ok) onde google_calendar_ok indica
    se o evento foi criado no Google Calendar.
    """
    # Última verificação anti-duplicata (safety net)
    duplicatas_exatas = detectar_duplicatas(tarefa_data.get("titulo", ""), tarefa_data.get("prazo"))
    duplicatas_exatas = [d for d in duplicatas_exatas if d.get("_similaridade", 0) == 100
                         and d.get("prazo") == tarefa_data.get("prazo")]
    if duplicatas_exatas:
        logger.warning(f"Duplicata exata detectada: '{tarefa_data.get('titulo')}' já existe para {tarefa_data.get('prazo')}")
        # Retorna a tarefa existente em vez de criar uma nova
        return duplicatas_exatas[0], False

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

    # Criar evento no Google Calendar se a tarefa tem data e Google esta conectado
    google_calendar_ok = False
    if tarefa and tarefa_data.get("prazo"):
        try:
            google_tokens = _load_tokens("google")
            if google_tokens:
                event_id = create_google_event(
                    titulo=tarefa_data.get("titulo", "Tarefa"),
                    data=tarefa_data["prazo"],
                    horario_inicio=tarefa_data.get("horario"),
                    horario_fim=None,
                    descricao=f"[Organizador] {tarefa_data.get('categoria', 'Pessoal')} — {tarefa_data.get('prioridade', 'media')}",
                )
                if event_id:
                    google_calendar_ok = True
        except Exception as e:
            logger.warning(f"Erro ao criar evento no Google Calendar: {e}")

    return tarefa, google_calendar_ok


def _criar_copias_recorrencia_semanal(tarefa_data):
    """Para tarefas diárias, cria cópias para o restante da semana atual."""
    rec = tarefa_data.get("recorrencia")
    if rec != "diaria":
        return []

    hoje = datetime.now(TZ_RECIFE)
    prazo_str = tarefa_data.get("prazo") or hoje.strftime("%Y-%m-%d")

    try:
        prazo_base = datetime.strptime(prazo_str, "%Y-%m-%d")
    except ValueError:
        prazo_base = hoje

    copias_criadas = []
    cat = tarefa_data.get("categoria", "Pessoal")
    # Para categorias de trabalho, apenas dias úteis (seg-sex). Para pessoal, todos os dias.
    max_dia = 4 if cat in ("Trabalho", "Consultoria", "Grupo Ser") else 6

    for offset in range(1, 7):
        dia = prazo_base + timedelta(days=offset)
        # Não ultrapassar o final da semana (domingo)
        if dia.weekday() > max_dia:
            continue
        # Não criar se mesma data que a base
        if dia.strftime("%Y-%m-%d") == prazo_str:
            continue
        # Não criar datas passadas
        if dia.date() < hoje.date():
            continue

        tarefa = criar_tarefa(
            titulo=tarefa_data.get("titulo", "Tarefa"),
            categoria=tarefa_data.get("categoria", "Pessoal"),
            prioridade=tarefa_data.get("prioridade", "media"),
            prazo=dia.strftime("%Y-%m-%d"),
            horario=tarefa_data.get("horario"),
            tempo_estimado=tarefa_data.get("tempo_estimado_min"),
        )
        if tarefa:
            copias_criadas.append(tarefa)

    return copias_criadas


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

    tarefa, gcal_ok = _salvar_tarefa_e_contexto(tarefa_data)
    # Criar cópias para a semana se for diária
    copias = _criar_copias_recorrencia_semanal(tarefa_data) if tarefa else []
    clear_state(context)

    if tarefa:
        resposta = "✅ *Tarefa salva!*\n\n" + formatar_tarefa_card(tarefa)
        if gcal_ok:
            resposta += "\n\n📅 Adicionado ao Google Calendar"
        if copias:
            resposta += f"\n\n🔄 Tarefa diária — criada para mais {len(copias)} dia(s) desta semana"
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
        gcal_count = 0
        total_copias = 0
        for t in pending_tasks:
            tarefa, gcal_ok = _salvar_tarefa_e_contexto(t)
            if tarefa:
                salvas += 1
                if gcal_ok:
                    gcal_count += 1
                await _agendar_lembrete_se_hoje(context, tarefa)
                # Criar cópias para a semana se for diária
                copias = _criar_copias_recorrencia_semanal(t)
                total_copias += len(copias)
        clear_state(context)
        gcal_msg = f"\n📅 {gcal_count} adicionada(s) ao Google Calendar" if gcal_count else ""
        copias_msg = f"\n🔄 +{total_copias} cópia(s) diária(s) criadas para a semana" if total_copias else ""
        await update.message.reply_text(
            f"✅ *{salvas} tarefas salvas!*{gcal_msg}{copias_msg}\n\n"
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
        "Não entendi. Diz *'confirma'* pra salvar todas, ou *'ajusta a 2'* pra mudar uma específica.",
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
        msg += f"\n🔗 [Entrar na reunião]({tarefa['meeting_link']})"

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

        msg = "📊 *Relatório Semanal*\n\n" + relatorio
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

    modo = "🧠 *Modo inteligente v2* (Claude IA)" if ai_brain else "⚡ *Modo básico* (sem IA)"

    await update.message.reply_text(
        f"👋 *Organizador de Tarefas v2*\n\n"
        f"{modo}\n\n"
        "Mande texto ou áudio e eu organizo pra você!\n\n"
        "*Comandos:*\n"
        "/tarefas — Ver pendentes\n"
        "/planejar — Planejamento inteligente\n"
        "/feedback — Feedback do dia\n"
        "/resumo — Resumo rápido\n"
        "/concluir — Concluir tarefa\n"
        "/excluir — Excluir tarefa\n"
        "/editar — Editar tarefa\n"
        "/relatório — Relatório semanal\n"
        "/foco — Modo foco\n"
        "/cancelar — Cancela operação\n\n"
        "*Novidades v2:*\n"
        "• IA entende datas: 'amanha', 'sexta', 'semana que vem'\n"
        "• Detecta múltiplas tarefas numa mensagem\n"
        "• Alerta de sobrecarga no dia\n"
        "• Lembretes 15min antes de reuniões\n"
        "• Resumo matinal automático às 7:30\n"
        "• Relatório semanal toda sexta 17h\n\n"
        f"📊 [Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista tarefas pendentes."""
    clear_state(context)
    tarefas = listar_tarefas_pendentes(15)

    if not tarefas:
        await update.message.reply_text("✅ Nenhuma tarefa pendente! Você está em dia.")
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
            "• 🇬🇧 Inglês (30min)\n"
            "• 📖 Leitura\n"
            "• 🧠 Projeto pessoal"
        )
        return

    # Buscar historico de energia dos ultimos 7 dias
    energia_info = ""
    try:
        data_7dias = (datetime.now(TZ_RECIFE) - timedelta(days=7)).strftime("%Y-%m-%d")
        registros = supabase_request("GET", "energia_diaria", params={
            "data": f"gte.{data_7dias}",
            "order": "data.desc,periodo.asc",
        }) or []
        if registros:
            linhas = []
            for r in registros:
                bolas = "●" * r["nivel"] + "○" * (5 - r["nivel"])
                linhas.append(f"  {r['data']} {r['periodo']}: {bolas} ({r['nivel']}/5)")
            energia_info = "\n".join(linhas)
    except Exception as e:
        logger.warning(f"Erro ao buscar energia: {e}")

    planejamento = ai_brain.planejar_dia(todas, hoje, energia_info=energia_info)

    set_state(context, STATE_CHATTING, chat_history=[
        {"role": "assistant", "content": planejamento}
    ])

    await msg.edit_text(planejamento, parse_mode="Markdown",
                        disable_web_page_preview=True)


async def cmd_energia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registrar nivel de energia do periodo (1-5)."""
    clear_state(context)

    args = context.args or []

    if not args:
        await update.message.reply_text(
            "⚡ *Registrar energia do período*\n\n"
            "Uso:\n"
            "• `/energia 4` — registra no período atual (auto)\n"
            "• `/energia 3 manha` — registra para manhã\n\n"
            "Níveis: 1 (exausto) a 5 (energia total)\n"
            "Períodos: manhã, tarde, noite",
            parse_mode="Markdown",
        )
        return

    # Validar nivel
    try:
        nivel = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Nível deve ser um número de 1 a 5.")
        return

    if nivel < 1 or nivel > 5:
        await update.message.reply_text("❌ Nível deve ser entre 1 e 5.")
        return

    # Detectar periodo
    if len(args) >= 2:
        periodo = args[1].lower()
        if periodo not in ("manha", "tarde", "noite"):
            await update.message.reply_text(
                "❌ Período inválido. Use: manhã, tarde ou noite."
            )
            return
    else:
        hora = datetime.now(TZ_RECIFE).hour
        if 6 <= hora <= 11:
            periodo = "manha"
        elif 12 <= hora <= 17:
            periodo = "tarde"
        else:
            periodo = "noite"

    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")

    # Upsert no Supabase (merge-duplicates usa a constraint UNIQUE(data, periodo))
    result = supabase_request(
        "POST", "energia_diaria",
        data={"data": hoje, "periodo": periodo, "nivel": nivel},
        extra_headers={"Prefer": "return=representation,resolution=merge-duplicates"},
    )

    if not result:
        await update.message.reply_text("❌ Erro ao salvar energia. Tente novamente.")
        return

    # Feedback visual
    bolas = "●" * nivel + "○" * (5 - nivel)
    periodo_display = {"manha": "manha", "tarde": "tarde", "noite": "noite"}[periodo]
    await update.message.reply_text(
        f"⚡ Energia da {periodo_display}: {bolas} ({nivel}/5)"
    )


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
        f"✅ Concluídas esta semana: *{resumo['concluidas_semana']}*\n"
        f"🔴 Atrasadas: *{resumo['atrasadas']}*\n"
        f"🎥 Reuniões pendentes: *{resumo['reunioes_pendentes']}*\n"
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
        await update.message.reply_text("⚠️ Relatório requer Claude API.")
        return

    msg = await update.message.reply_text("📊 Gerando relatório semanal...")

    try:
        dados = _preparar_dados_relatorio()
        relatorio = ai_brain.gerar_relatorio_semanal(dados)
        await msg.edit_text(f"📊 *Relatório Semanal*\n\n{relatorio}",
                            parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Erro no relatorio: {e}")
        await msg.edit_text("❌ Erro ao gerar relatório.")


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


async def cmd_coaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Coaching IA — dica personalizada baseada nos padroes de tarefas."""
    clear_state(context)

    if not ai_brain:
        await update.message.reply_text(
            "⚠️ Coaching requer IA. Configure GEMINI_API_KEY ou ANTHROPIC_API_KEY."
        )
        return

    msg = await update.message.reply_text("🧠 Analisando seus padroes...")

    tarefas = listar_tarefas_pendentes(20)
    concluidas = listar_concluidas_hoje()
    atrasadas = listar_tarefas_atrasadas()

    todas = tarefas + concluidas + atrasadas
    if not todas:
        await msg.edit_text("📭 Sem tarefas para analisar. Crie algumas primeiro!")
        return

    # Montar historico resumido
    historico = ""
    if concluidas:
        historico += f"Concluídas hoje: {len(concluidas)}. "
    if atrasadas:
        historico += f"Atrasadas: {len(atrasadas)}. "

    try:
        dica = ai_brain.gerar_coaching(todas, historico)
        await msg.edit_text(
            f"🎯 *Coaching IA*\n\n{dica}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro no coaching: {e}")
        await msg.edit_text("❌ Erro ao gerar coaching. Tente novamente.")


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buscar em tarefas, eventos, anotacoes e anexos."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "🔍 *Busca inteligente*\n\n"
            "Uso: /buscar reunião com fulano\n\n"
            "Busca em tarefas, eventos, anotações semanais e anexos.",
            parse_mode="Markdown",
        )
        return

    results = []

    # 1. Buscar tarefas por titulo
    tarefas = supabase_request("GET", "tarefas", params={
        "titulo": f"ilike.%{query}%",
        "order": "created_at.desc",
        "limit": "5",
    }) or []
    for t in tarefas:
        cat_emoji = EMOJI_CATEGORIA.get(t.get("categoria", ""), "📋")
        results.append(
            f"📋 *{t['titulo']}*\n"
            f"   {cat_emoji} {t.get('categoria', '')} · {t.get('prazo', 'sem data')} · {t.get('status', '')}"
        )

    # 2. Buscar eventos do calendario
    eventos = supabase_request("GET", "eventos_calendario", params={
        "titulo": f"ilike.%{query}%",
        "order": "data_inicio.desc",
        "limit": "5",
    }) or []
    for ev in eventos:
        results.append(
            f"📅 *{ev['titulo']}*\n"
            f"   {ev.get('dia', '')} {ev.get('horario_inicio', '')} · {ev.get('provider', '')}"
        )

    # 3. Buscar anotacoes semanais
    semanas = supabase_request("GET", "historico_semanal", params={
        "annotation": f"ilike.%{query}%",
        "order": "week_start.desc",
        "limit": "3",
    }) or []
    for s in semanas:
        annotation_preview = (s.get("annotation", ""))[:100]
        results.append(
            f"📝 *Semana {s['week_start']}*\n"
            f"   {annotation_preview}..."
        )

    # 4. Buscar anexos
    anexos = supabase_request("GET", "anexos", params={
        "or": f"(titulo.ilike.%{query}%,conteudo.ilike.%{query}%)",
        "order": "created_at.desc",
        "limit": "5",
    }) or []
    for a in anexos:
        preview = (a.get("conteudo", ""))[:80]
        tipo_icon = {"texto": "📄", "transcricao": "🎙️", "link": "🔗", "arquivo": "📎"}.get(a["tipo"], "📄")
        results.append(
            f"{tipo_icon} *{a.get('titulo', 'Anexo')}*\n"
            f"   {preview}..."
        )

    if not results:
        await update.message.reply_text(f'🔍 Nenhum resultado para "{query}"')
        return

    header = f'🔍 *Resultados para "{query}"* ({len(results)} encontrados)\n\n'
    await update.message.reply_text(
        header + "\n\n".join(results),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_anexar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anexar texto/transcricao a uma tarefa ou avulso."""
    if not context.args:
        await update.message.reply_text(
            "📎 *Anexar conteúdo*\n\n"
            "Uso:\n"
            "• `/anexar Título do anexo` — depois envie o conteúdo\n"
            "• Responda a uma mensagem com `/anexar Título`\n\n"
            "O anexo fica salvo e aparece nas buscas.",
            parse_mode="Markdown",
        )
        return

    titulo = " ".join(context.args)

    # Se esta respondendo a uma mensagem, salva direto
    if update.message.reply_to_message:
        conteudo = update.message.reply_to_message.text or ""
        if not conteudo:
            await update.message.reply_text("❌ A mensagem respondida não tem texto.")
            return

        data = {
            "tipo": "texto",
            "titulo": titulo,
            "conteudo": conteudo,
        }
        result = supabase_request("POST", "anexos", data=data)
        if result:
            await update.message.reply_text(
                f"📎 Anexo salvo: *{titulo}*\n({len(conteudo)} caracteres)",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Erro ao salvar anexo.")
    else:
        # Aguardar conteudo na proxima mensagem
        set_state(context, STATE_AGUARDANDO_ANEXO, titulo_anexo=titulo)
        await update.message.reply_text(
            f"📎 Título: *{titulo}*\n\nAgora envie o conteúdo (texto, transcrição, etc):",
            parse_mode="Markdown",
        )


async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analisa tarefas duplicadas ou repetitivas para limpeza."""
    clear_state(context)

    todas = supabase_request("GET", "tarefas", params={
        "status": "neq.concluida",
        "order": "titulo.asc",
        "select": "id,titulo,categoria,prioridade,prazo,horario,status",
    }) or []

    if not todas:
        await update.message.reply_text("Nenhuma tarefa pendente.")
        return

    from difflib import SequenceMatcher

    # Encontrar grupos de tarefas similares
    grupos = []
    usados = set()

    for i, t1 in enumerate(todas):
        if i in usados:
            continue
        grupo = [t1]
        for j, t2 in enumerate(todas):
            if j <= i or j in usados:
                continue
            titulo1 = (t1.get("titulo") or "").lower()
            titulo2 = (t2.get("titulo") or "").lower()
            if not titulo1 or not titulo2:
                continue
            ratio = SequenceMatcher(None, titulo1, titulo2).ratio()
            if ratio >= 0.7 or (len(titulo1) > 5 and titulo1 in titulo2) or (len(titulo2) > 5 and titulo2 in titulo1):
                grupo.append(t2)
                usados.add(j)
        if len(grupo) > 1:
            usados.add(i)
            grupos.append(grupo)

    if not grupos:
        await update.message.reply_text(
            "✅ Nenhuma duplicata encontrada! Suas tarefas estão organizadas."
        )
        return

    msg = f"🔍 *Encontrei {len(grupos)} grupo(s) de tarefas similares:*\n\n"
    total_duplicatas = 0

    for idx, grupo in enumerate(grupos, 1):
        msg += f"*Grupo {idx}:* ({len(grupo)} tarefas)\n"
        for t in grupo:
            prazo = t.get("prazo", "sem data")
            msg += f"  • {t.get('titulo')} — {prazo}\n"
            total_duplicatas += 1
        msg += "\n"

    msg += f"Total: {total_duplicatas} tarefas em {len(grupos)} grupos similares.\n"
    msg += "\nUse /excluir para remover as duplicatas."

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_excluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Excluir tarefa (inline keyboard)."""
    clear_state(context)
    tarefas = supabase_request("GET", "tarefas", params={
        "status": "neq.concluida",
        "order": "prazo.asc.nullslast",
        "limit": "20",
    }) or []

    if not tarefas:
        await update.message.reply_text("Nenhuma tarefa pendente para excluir.")
        return

    keyboard = []
    for t in tarefas:
        prazo_str = t.get("prazo", "")
        if prazo_str:
            try:
                d = datetime.strptime(prazo_str, "%Y-%m-%d")
                prazo_str = d.strftime("%d/%m")
            except ValueError:
                pass
        label = f"🗑️ {t['titulo'][:35]}"
        if prazo_str:
            label += f" ({prazo_str})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"excluir_{t['id']}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🗑️ *Qual tarefa quer excluir?*\nToque na tarefa:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela operacao atual."""
    state = get_state(context)
    clear_state(context)
    if state != STATE_IDLE:
        await update.message.reply_text("🚫 Operação cancelada.")
    else:
        await update.message.reply_text("Nenhuma operação em andamento.")


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
                    f"✅ *Concluída:* {tarefa['titulo']}\n"
                    f"🔄 Tarefa recorrente — próxima instância será criada automaticamente.",
                    parse_mode="Markdown",
                )
                # Recriar para proxima ocorrencia
                _recriar_recorrente(tarefa)
            else:
                await query.edit_message_text(
                    f"✅ *Concluída:* {tarefa['titulo']}",
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
            await query.edit_message_text("⚠️ Decomposição requer Claude API.")
            return

        # Buscar dados da tarefa
        result = supabase_request("GET", "tarefas", params={
            "id": f"eq.{task_id}",
            "select": "id,titulo,categoria,prioridade,prazo,horario,tempo_estimado_min",
        })
        if not result:
            await query.edit_message_text("❌ Tarefa não encontrada.")
            return

        tarefa = result[0]
        await query.edit_message_text("🧠 Decompondo tarefa em subtarefas...")

        try:
            subtarefas = ai_brain.decompor_tarefa(tarefa)
            if not subtarefas:
                await query.edit_message_text("❌ Não consegui decompor essa tarefa.")
                return

            msg = f"🔀 *Decomposição de:* _{tarefa['titulo']}_\n\n"
            for i, sub in enumerate(subtarefas, 1):
                msg += f"*{i}.* {sub.get('titulo', 'Subtarefa')}"
                if sub.get("tempo_estimado_min"):
                    msg += f" (~{sub['tempo_estimado_min']}min)"
                msg += "\n"
            msg += "\n✅ *Confirma a criação das subtarefas?*"

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

    # EXCLUIR tarefa
    elif data.startswith("excluir_"):
        task_id = data.replace("excluir_", "")
        # Find the task title
        tarefa = supabase_request("GET", "tarefas", params={"id": f"eq.{task_id}", "select": "titulo"})
        titulo = tarefa[0]["titulo"] if tarefa else "?"
        keyboard = [
            [InlineKeyboardButton("✅ Sim, excluir", callback_data=f"confirmar_excluir_{task_id}")],
            [InlineKeyboardButton("❌ Não, manter", callback_data=f"cancelar_excluir_{task_id}")]
        ]
        await query.edit_message_text(
            f"⚠️ *Excluir esta tarefa?*\n\n🗑️ {titulo}\n\nEssa ação não pode ser desfeita.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("confirmar_excluir_"):
        task_id = data.replace("confirmar_excluir_", "")
        # Delete related subtarefas and anexos first (safety)
        supabase_request("DELETE", "subtarefas", params={"tarefa_id": f"eq.{task_id}"})
        supabase_request("DELETE", "anexos", params={"tarefa_id": f"eq.{task_id}"})
        # Delete the task
        result = supabase_request("DELETE", "tarefas", params={"id": f"eq.{task_id}"})
        await query.edit_message_text("✅ Tarefa excluída com sucesso!")

    elif data.startswith("cancelar_excluir_"):
        await query.edit_message_text("👍 Tarefa mantida.")

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
            "• 'titulo: Reunião com equipe'\n\n"
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


# ========== MÓDULO FINANCEIRO ==========

STATE_CONFIRMING_TRANSACAO = "confirming_transacao"

def criar_transacao(tipo, valor, descricao, categoria, data=None, recorrente=False,
                    recorrencia=None, dia_vencimento=None, notas=""):
    """Cria uma transação financeira no Supabase."""
    from datetime import date as date_type
    transacao = {
        "tipo": tipo,
        "valor": float(valor),
        "descricao": descricao,
        "categoria": categoria,
        "data": data or datetime.now(TZ_RECIFE).strftime("%Y-%m-%d"),
        "recorrente": recorrente,
        "recorrencia": recorrencia,
        "dia_vencimento": dia_vencimento,
        "notas": notas,
        "origem": "telegram",
    }
    result = supabase_request("POST", "transacoes", transacao)
    return result[0] if result else None


def obter_transacoes_mes(mes=None, ano=None):
    """Obtém todas as transações do mês."""
    agora = datetime.now(TZ_RECIFE)
    m = mes or agora.month
    a = ano or agora.year
    inicio = f"{a}-{m:02d}-01"
    if m == 12:
        fim = f"{a + 1}-01-01"
    else:
        fim = f"{a}-{m + 1:02d}-01"

    result = supabase_request("GET", "transacoes", params={
        "and": f"(data.gte.{inicio},data.lt.{fim})",
        "order": "data.desc,created_at.desc",
        "select": "*",
    })
    return result or []


def obter_orcamentos_mes(mes=None, ano=None):
    """Obtém orçamentos do mês."""
    agora = datetime.now(TZ_RECIFE)
    m = mes or agora.month
    a = ano or agora.year
    mes_str = f"{a}-{m:02d}-01"
    result = supabase_request("GET", "orcamento_mensal", params={
        "mes": f"eq.{mes_str}",
        "select": "*",
    })
    return result or []


def obter_metas_financeiras():
    """Obtém metas financeiras ativas."""
    result = supabase_request("GET", "metas_financeiras", params={
        "status": "eq.ativa",
        "select": "*",
        "order": "created_at.asc",
    })
    return result or []


def calcular_saldo_mes(transacoes):
    """Calcula receitas, despesas e saldo de uma lista de transações."""
    receitas = sum(float(t["valor"]) for t in transacoes if t["tipo"] == "receita")
    despesas = sum(float(t["valor"]) for t in transacoes if t["tipo"] == "despesa")
    return {"receitas": receitas, "despesas": despesas, "saldo": receitas - despesas}


def gastos_por_categoria(transacoes):
    """Agrupa despesas por categoria."""
    cats = {}
    for t in transacoes:
        if t["tipo"] == "despesa":
            cat = t["categoria"]
            cats[cat] = cats.get(cat, 0) + float(t["valor"])
    return dict(sorted(cats.items(), key=lambda x: x[1], reverse=True))


def formatar_valor(v):
    """Formata valor em reais."""
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_transacao_card(t):
    """Formata uma transação para exibição."""
    icon = "🟢" if t["tipo"] == "receita" else "🔴"
    sinal = "+" if t["tipo"] == "receita" else "-"
    return f"{icon} *{t['descricao']}* — {sinal} {formatar_valor(t['valor'])}\n   📁 {t['categoria']} · 📅 {t['data']}"


async def cmd_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registrar gasto: /gasto 50 almoço ou texto livre."""
    texto = " ".join(context.args) if context.args else ""

    if not texto:
        await update.message.reply_text(
            "💸 *Como registrar um gasto:*\n\n"
            "`/gasto 50 almoço`\n"
            "`/gasto 320 conta de celular`\n"
            "ou envie como texto livre:\n"
            "\"gastei 50 reais no uber\"",
            parse_mode="Markdown"
        )
        return

    if ai_brain:
        resultado = ai_brain.classificar_transacao(texto)
        if resultado:
            resultado["tipo"] = "despesa"  # Forçar como despesa
            context.user_data["state"] = STATE_CONFIRMING_TRANSACAO
            context.user_data["pending_transacao"] = resultado

            msg = (
                f"💸 *Confirmar gasto:*\n\n"
                f"📝 {resultado.get('descricao', texto)}\n"
                f"💰 {formatar_valor(resultado.get('valor', 0))}\n"
                f"📁 {resultado.get('categoria', 'Outros')}\n"
                f"📅 {resultado.get('data', 'hoje')}\n"
            )
            if resultado.get("recorrente"):
                msg += f"🔄 Recorrente ({resultado.get('recorrencia', 'mensal')})\n"
            msg += "\n✅ Confirmar? (sim/não/editar)"
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

    # Fallback: tentar parsear manualmente
    import re
    match = re.search(r"(\d+[.,]?\d*)", texto)
    if match:
        valor = float(match.group(1).replace(",", "."))
        desc = re.sub(r"\d+[.,]?\d*\s*(reais|r\$)?", "", texto, flags=re.IGNORECASE).strip()
        desc = desc or "Gasto"
        transacao = criar_transacao("despesa", valor, desc, "Outros")
        if transacao:
            await update.message.reply_text(
                f"✅ *Gasto registrado!*\n\n{formatar_transacao_card(transacao)}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Erro ao registrar gasto.")
    else:
        await update.message.reply_text("❌ Não encontrei um valor. Tente: `/gasto 50 almoço`", parse_mode="Markdown")


async def cmd_receita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registrar receita: /receita 8000 aulas optativas."""
    texto = " ".join(context.args) if context.args else ""

    if not texto:
        await update.message.reply_text(
            "💰 *Como registrar uma receita:*\n\n"
            "`/receita 8000 aulas optativas`\n"
            "`/receita 6000 consultoria IA`\n",
            parse_mode="Markdown"
        )
        return

    if ai_brain:
        resultado = ai_brain.classificar_transacao(texto)
        if resultado:
            resultado["tipo"] = "receita"  # Forçar como receita
            context.user_data["state"] = STATE_CONFIRMING_TRANSACAO
            context.user_data["pending_transacao"] = resultado

            msg = (
                f"💰 *Confirmar receita:*\n\n"
                f"📝 {resultado.get('descricao', texto)}\n"
                f"💵 {formatar_valor(resultado.get('valor', 0))}\n"
                f"📁 {resultado.get('categoria', 'Outros Receita')}\n"
                f"📅 {resultado.get('data', 'hoje')}\n"
                f"\n✅ Confirmar? (sim/não)"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

    # Fallback
    import re
    match = re.search(r"(\d+[.,]?\d*)", texto)
    if match:
        valor = float(match.group(1).replace(",", "."))
        desc = re.sub(r"\d+[.,]?\d*\s*(reais|r\$)?", "", texto, flags=re.IGNORECASE).strip()
        desc = desc or "Receita"
        transacao = criar_transacao("receita", valor, desc, "Outros Receita")
        if transacao:
            await update.message.reply_text(
                f"✅ *Receita registrada!*\n\n{formatar_transacao_card(transacao)}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Erro ao registrar receita.")
    else:
        await update.message.reply_text("❌ Não encontrei um valor. Tente: `/receita 8000 salário`", parse_mode="Markdown")


async def cmd_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra saldo do mês atual."""
    transacoes = obter_transacoes_mes()
    saldo = calcular_saldo_mes(transacoes)

    agora = datetime.now(TZ_RECIFE)
    dias_restantes = (agora.replace(month=agora.month % 12 + 1, day=1) - agora).days if agora.month < 12 else (agora.replace(year=agora.year + 1, month=1, day=1) - agora).days
    mes_nome = agora.strftime("%B/%Y").capitalize()

    icon_saldo = "🟢" if saldo["saldo"] >= 0 else "🔴"

    msg = (
        f"💰 *Saldo — {mes_nome}*\n\n"
        f"📈 Receitas: {formatar_valor(saldo['receitas'])}\n"
        f"📉 Despesas: {formatar_valor(saldo['despesas'])}\n"
        f"{'─' * 25}\n"
        f"{icon_saldo} *Saldo: {formatar_valor(saldo['saldo'])}*\n\n"
        f"📅 Faltam {dias_restantes} dias no mês"
    )

    # Quanto sobra por dia
    if saldo["saldo"] > 0 and dias_restantes > 0:
        por_dia = saldo["saldo"] / dias_restantes
        msg += f"\n💡 Disponível: ~{formatar_valor(por_dia)}/dia"

    # Alertas de orçamento
    orcamentos = obter_orcamentos_mes()
    if orcamentos:
        gastos = gastos_por_categoria(transacoes)
        alertas = []
        for orc in orcamentos:
            cat = orc["categoria"]
            gasto = gastos.get(cat, 0)
            limite = float(orc["limite"])
            pct = (gasto / limite * 100) if limite > 0 else 0
            if pct >= 80:
                emoji = "🔴" if pct >= 100 else "🟡"
                alertas.append(f"{emoji} {cat}: {formatar_valor(gasto)}/{formatar_valor(limite)} ({pct:.0f}%)")
        if alertas:
            msg += "\n\n⚠️ *Alertas de orçamento:*\n" + "\n".join(alertas)

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_extrato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista últimas transações."""
    transacoes = obter_transacoes_mes()

    if not transacoes:
        await update.message.reply_text("📋 Nenhuma transação este mês. Use /gasto ou /receita para começar!")
        return

    ultimas = transacoes[:15]
    linhas = [formatar_transacao_card(t) for t in ultimas]

    saldo = calcular_saldo_mes(transacoes)
    agora = datetime.now(TZ_RECIFE)
    mes_nome = agora.strftime("%B/%Y").capitalize()

    msg = f"📋 *Extrato — {mes_nome}*\n({len(transacoes)} transações)\n\n"
    msg += "\n\n".join(linhas)
    msg += f"\n\n{'─' * 25}\n"
    msg += f"📈 Receitas: {formatar_valor(saldo['receitas'])}\n"
    msg += f"📉 Despesas: {formatar_valor(saldo['despesas'])}\n"
    icon = "🟢" if saldo["saldo"] >= 0 else "🔴"
    msg += f"{icon} *Saldo: {formatar_valor(saldo['saldo'])}*"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_orcamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define orçamento mensal: /orcamento Alimentação 800."""
    args = context.args
    if not args or len(args) < 2:
        # Mostrar orçamentos atuais
        orcamentos = obter_orcamentos_mes()
        transacoes = obter_transacoes_mes()
        gastos = gastos_por_categoria(transacoes)

        if not orcamentos:
            await update.message.reply_text(
                "📊 *Orçamento Mensal*\n\n"
                "Nenhum orçamento definido.\n\n"
                "*Para criar:*\n"
                "`/orcamento Alimentação 800`\n"
                "`/orcamento Transporte 300`\n"
                "`/orcamento Lazer 200`\n\n"
                "*Categorias:* Alimentação, Transporte, Moradia, Assinaturas, Lazer, Saúde, Educação, Vestuário, Outros",
                parse_mode="Markdown"
            )
            return

        msg = "📊 *Orçamento Mensal*\n\n"
        for orc in orcamentos:
            cat = orc["categoria"]
            limite = float(orc["limite"])
            gasto = gastos.get(cat, 0)
            pct = (gasto / limite * 100) if limite > 0 else 0
            barra = "█" * int(min(pct, 100) / 10) + "░" * (10 - int(min(pct, 100) / 10))
            emoji = "🟢" if pct < 60 else ("🟡" if pct < 80 else "🔴")
            msg += f"{emoji} *{cat}*\n   {barra} {pct:.0f}%\n   {formatar_valor(gasto)} / {formatar_valor(limite)}\n\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Criar/atualizar orçamento
    try:
        valor = float(args[-1].replace(",", "."))
        categoria = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ Use: `/orcamento Alimentação 800`", parse_mode="Markdown")
        return

    agora = datetime.now(TZ_RECIFE)
    mes_str = f"{agora.year}-{agora.month:02d}-01"

    # Upsert
    existing = supabase_request("GET", "orcamento_mensal", params={
        "categoria": f"eq.{categoria}",
        "mes": f"eq.{mes_str}",
    })
    if existing:
        supabase_request("PATCH", f"orcamento_mensal?id=eq.{existing[0]['id']}", {
            "limite": valor,
        })
    else:
        supabase_request("POST", "orcamento_mensal", {
            "categoria": categoria,
            "limite": valor,
            "mes": mes_str,
        })

    await update.message.reply_text(
        f"✅ Orçamento definido!\n\n📁 *{categoria}*: {formatar_valor(valor)}/mês",
        parse_mode="Markdown"
    )


async def cmd_financeiro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumo financeiro completo do mês com IA."""
    transacoes = obter_transacoes_mes()
    if not transacoes:
        await update.message.reply_text("📊 Nenhuma transação este mês. Comece com /gasto ou /receita!")
        return

    saldo = calcular_saldo_mes(transacoes)
    gastos = gastos_por_categoria(transacoes)
    orcamentos = obter_orcamentos_mes()
    metas = obter_metas_financeiras()
    agora = datetime.now(TZ_RECIFE)
    mes_nome = agora.strftime("%B/%Y").capitalize()

    msg = f"📊 *Resumo Financeiro — {mes_nome}*\n\n"
    icon = "🟢" if saldo["saldo"] >= 0 else "🔴"
    msg += f"📈 Receitas: {formatar_valor(saldo['receitas'])}\n"
    msg += f"📉 Despesas: {formatar_valor(saldo['despesas'])}\n"
    msg += f"{icon} *Saldo: {formatar_valor(saldo['saldo'])}*\n\n"

    if gastos:
        msg += "📁 *Gastos por categoria:*\n"
        total_desp = saldo["despesas"] or 1
        for cat, val in list(gastos.items())[:6]:
            pct = val / total_desp * 100
            msg += f"  • {cat}: {formatar_valor(val)} ({pct:.0f}%)\n"
        msg += "\n"

    # IA coaching
    if ai_brain:
        await update.message.reply_text(msg + "🧠 _Gerando análise IA..._", parse_mode="Markdown")
        try:
            resumo_ia = ai_brain.gerar_resumo_financeiro(
                transacoes[:30],
                orcamentos,
                metas
            )
            await update.message.reply_text(f"🧠 *Coaching Financeiro:*\n\n{resumo_ia}", parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Erro no resumo financeiro IA: {e}")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def processar_confirmacao_transacao(update, context, texto):
    """Processa confirmação de transação financeira."""
    pending = context.user_data.get("pending_transacao")
    if not pending:
        clear_state(context)
        return

    lower = texto.lower().strip()

    if any(w in lower for w in ["sim", "ok", "confirma", "pode", "bora", "salva"]):
        transacao = criar_transacao(
            tipo=pending.get("tipo", "despesa"),
            valor=pending.get("valor", 0),
            descricao=pending.get("descricao", ""),
            categoria=pending.get("categoria", "Outros"),
            data=pending.get("data"),
            recorrente=pending.get("recorrente", False),
            recorrencia=pending.get("recorrencia"),
            dia_vencimento=pending.get("dia_vencimento"),
        )
        clear_state(context)
        if transacao:
            await update.message.reply_text(
                f"✅ *Transação salva!*\n\n{formatar_transacao_card(transacao)}\n\n"
                f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
                parse_mode="Markdown", disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("❌ Erro ao salvar transação.")

    elif any(w in lower for w in ["não", "nao", "cancela", "cancelar"]):
        clear_state(context)
        await update.message.reply_text("🚫 Transação cancelada.")
    else:
        await update.message.reply_text("Confirmar? Responda *sim* ou *não*.", parse_mode="Markdown")


async def alerta_vencimentos_job(context):
    """Job diário que alerta sobre contas a vencer nos próximos 3 dias."""
    if not CHAT_ID:
        return
    try:
        agora = datetime.now(TZ_RECIFE)
        hoje = agora.strftime("%Y-%m-%d")
        em3dias = (agora + timedelta(days=3)).strftime("%Y-%m-%d")

        # Buscar transações recorrentes com vencimento próximo
        recorrentes = supabase_request("GET", "transacoes", params={
            "recorrente": "eq.true",
            "tipo": "eq.despesa",
            "select": "descricao,valor,categoria,dia_vencimento",
        })
        if not recorrentes:
            return

        dia_hoje = agora.day
        alertas = []
        for t in recorrentes:
            dia = t.get("dia_vencimento")
            if dia and dia_hoje <= dia <= dia_hoje + 3:
                alertas.append(f"📌 *{t['descricao']}* — {formatar_valor(t['valor'])} (dia {dia})")

        if alertas:
            msg = "⏰ *Contas a vencer nos próximos dias:*\n\n" + "\n".join(alertas)
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Erro no alerta de vencimentos: {e}")


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
    if state in (STATE_CONFIRMING, STATE_CONFIRMING_MULTI, STATE_CONFIRMING_DECOMP, STATE_CONFIRMING_TRANSACAO):
        ts = context.user_data.get("state_timestamp")
        if ts:
            try:
                state_time = datetime.fromisoformat(ts)
                agora = datetime.now(TZ_RECIFE)
                if (agora - state_time).total_seconds() > 1800:  # 30 min
                    clear_state(context)
                    await update.message.reply_text(
                        "⏰ Confirmação expirou. Mande a tarefa novamente."
                    )
                    return
            except (ValueError, TypeError):
                pass

    if state == STATE_CONFIRMING_TRANSACAO:
        await processar_confirmacao_transacao(update, context, texto)

    elif state == STATE_CONFIRMING and ai_brain:
        await processar_confirmacao(update, context, texto)

    elif state == STATE_CONFIRMING_MULTI and ai_brain:
        await processar_confirmacao_multi(update, context, texto)

    elif state == STATE_CONFIRMING_DECOMP and ai_brain:
        await processar_confirmacao_decomp(update, context, texto)

    elif state == STATE_EDITING:
        await processar_edicao(update, context, texto)

    elif state == STATE_AGUARDANDO_ANEXO:
        titulo_anexo = context.user_data.get("titulo_anexo", "Sem titulo")
        data = {
            "tipo": "texto",
            "titulo": titulo_anexo,
            "conteudo": texto,
        }
        result = supabase_request("POST", "anexos", data=data)
        clear_state(context)
        if result:
            await update.message.reply_text(
                f"📎 Anexo salvo: *{titulo_anexo}*\n({len(texto)} caracteres)",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Erro ao salvar anexo.")

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

    elif state == STATE_REFLEXAO:
        # Salvar reflexao noturna no Supabase
        global _reflexao_pendente, _reflexao_timestamp
        try:
            hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
            supabase_request("POST", "reflexoes", {
                "data": hoje,
                "pergunta": "reflexao_noturna",
                "resposta": texto,
            })
            await update.message.reply_text(
                "✨ Reflexão salva! Vai aparecer na sua revisão semanal.\n\n"
                "Descanse bem, amanhã é um novo dia! 💪",
            )
        except Exception as e:
            logger.error(f"Erro ao salvar reflexao: {e}")
            await update.message.reply_text("Anotei mentalmente! 😊")
        _reflexao_pendente = False
        _reflexao_timestamp = None
        clear_state(context)

    else:
        # Verificar se ha reflexao pendente (dentro de 2 horas)
        if _reflexao_pendente and _reflexao_timestamp:
            agora = datetime.now(TZ_RECIFE)
            if (agora - _reflexao_timestamp).total_seconds() <= 7200:  # 2 horas
                # Salvar como reflexao em vez de criar tarefa
                try:
                    hoje = agora.strftime("%Y-%m-%d")
                    supabase_request("POST", "reflexoes", {
                        "data": hoje,
                        "pergunta": "reflexao_noturna",
                        "resposta": texto,
                    })
                    await update.message.reply_text(
                        "✨ Reflexao salva! Vai aparecer na sua revisao semanal.\n\n"
                        "Descanse bem, amanha e um novo dia! 💪",
                    )
                except Exception as e:
                    logger.error(f"Erro ao salvar reflexao: {e}")
                    await update.message.reply_text("Anotei mentalmente! 😊")
                _reflexao_pendente = False
                _reflexao_timestamp = None
                return
            else:
                # Expirou, limpar flag
                _reflexao_pendente = False
                _reflexao_timestamp = None
        # Triagem inteligente: tarefa ou finança?
        if ai_brain:
            intencao = ai_brain.detectar_intencao(texto)
            if intencao == "financa":
                resultado = ai_brain.classificar_transacao(texto)
                if resultado and resultado.get("valor"):
                    context.user_data["state"] = STATE_CONFIRMING_TRANSACAO
                    context.user_data["pending_transacao"] = resultado
                    context.user_data["state_timestamp"] = datetime.now(TZ_RECIFE).isoformat()

                    tipo_icon = "💰" if resultado.get("tipo") == "receita" else "💸"
                    tipo_label = "receita" if resultado.get("tipo") == "receita" else "gasto"
                    msg = (
                        f"{tipo_icon} *Detectei uma {tipo_label}:*\n\n"
                        f"📝 {resultado.get('descricao', texto)}\n"
                        f"💵 {formatar_valor(resultado.get('valor', 0))}\n"
                        f"📁 {resultado.get('categoria', 'Outros')}\n"
                        f"📅 {resultado.get('data', 'hoje')}\n"
                    )
                    if resultado.get("recorrente"):
                        msg += f"🔄 Recorrente ({resultado.get('recorrencia', 'mensal')})\n"
                    msg += "\n✅ Confirmar? (sim/não)"
                    await update.message.reply_text(msg, parse_mode="Markdown")
                    return
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
                "Não entendi o que mudar. Exemplos:\n"
                "• 'prioridade alta'\n"
                "• 'muda pra sexta'\n"
                "• 'categoria grupo ser'\n"
                "• 'titulo: Novo título aqui'"
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
        await update.message.reply_text("Edição requer Claude API.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe audio, transcreve e processa."""
    if not GROQ_API_KEY:
        await update.message.reply_text(
            "🎤 Áudio recebido, mas transcrição não está configurada.\n"
            "Configure GROQ_API_KEY no .env"
        )
        return

    msg = await update.message.reply_text("🎤 Transcrevendo áudio...")

    try:
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)

        tmp_dir = tempfile.mkdtemp()
        ogg_path = os.path.join(tmp_dir, "audio.ogg")
        await file.download_to_drive(ogg_path)

        texto = transcrever_audio(ogg_path)

        if not texto:
            await msg.edit_text("❌ Não consegui transcrever. Tente novamente ou mande por texto.")
            return

        await msg.edit_text(f"🎤 Entendi: _{texto}_\n\nProcessando...", parse_mode="Markdown")
        await processar_nova_tarefa(update, context, texto)

    except Exception as e:
        logger.error(f"Erro no handler de voz: {e}")
        await msg.edit_text("❌ Erro ao processar áudio.")


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
        tarefa_id = tarefa_pai.get("id")
        criadas = 0

        for i, sub in enumerate(subtarefas):
            # Salvar na tabela subtarefas (vinculada a tarefa pai)
            result = supabase_request("POST", "subtarefas", {
                "tarefa_id": tarefa_id,
                "titulo": sub.get("titulo", "Subtarefa"),
                "ordem": i,
                "concluida": False,
            })
            if result:
                criadas += 1

        clear_state(context)
        await update.message.reply_text(
            f"✅ *{criadas} subtarefas criadas* para _{tarefa_pai.get('titulo', 'tarefa')}_!\n\n"
            f"[📊 Dashboard](https://wendelcastro.github.io/organizador-tarefas/web/)",
            parse_mode="Markdown", disable_web_page_preview=True
        )
        return

    # Cancelar
    if any(w in lower for w in ["nao", "cancela", "esquece"]):
        clear_state(context)
        await update.message.reply_text("🚫 Decomposição cancelada.")
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
        await update.message.reply_text("⚠️ Decomposição requer Claude API. Configure ANTHROPIC_API_KEY.")
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
        encorajamento = "🔥 Ótimo ritmo! Mais da metade já concluída. Continue assim!"
    elif n_concluidas > 0:
        encorajamento = "💪 Já começou bem! Foca nas prioridades da tarde."
    else:
        encorajamento = "🚀 A tarde é sua! Comece pela tarefa mais importante."

    msg = (
        f"📊 *Check-in do meio-dia*\n\n"
        f"✅ {n_concluidas}/{total} tarefas concluídas até agora ({percentual:.0f}%)\n\n"
        f"{encorajamento}"
    )

    try:
        await context.bot.send_message(chat_id, msg, parse_mode="Markdown",
                                       disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Erro no check-in meio-dia: {e}")


# Flag global para reflexao noturna
_reflexao_pendente = False
_reflexao_timestamp = None


async def reflexao_noturna(context):
    """Reflexao do final do dia - 18:00."""
    global _reflexao_pendente, _reflexao_timestamp
    chat_id = get_chat_id()
    if not chat_id:
        return
    try:
        # Stats do dia
        concluidas = listar_concluidas_hoje()
        pendentes = listar_tarefas_do_dia()
        n_concluidas = len(concluidas) if concluidas else 0
        n_pendentes = len(pendentes) if pendentes else 0

        msg = "🌅 *Reflexão do dia*\n\n"
        msg += f"Hoje você concluiu *{n_concluidas}* tarefa(s)"
        if n_pendentes > 0:
            msg += f" e ficaram *{n_pendentes}* pendente(s)"
        msg += ".\n\n"
        msg += "💭 *Como foi seu dia?*\n"
        msg += "Me conta: o que fez de melhor? O que ficou pra amanhã?\n\n"
        msg += "_Responde com texto livre — vou guardar pra sua revisão semanal._"

        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
        )
        # Ativar flag para capturar resposta (valida por 2 horas)
        _reflexao_pendente = True
        _reflexao_timestamp = datetime.now(TZ_RECIFE)
    except Exception as e:
        logger.error(f"Erro na reflexao noturna: {e}")


# ========== CALENDARIO (Google + Microsoft) ==========

async def cmd_conectar_google(update, context):
    """Conectar Google Calendar."""
    chat_id = update.effective_chat.id
    url = build_google_auth_url(chat_id)
    if not url:
        await update.message.reply_text(
            "⚠️ Integração Google não configurada. Adicione GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET nas variáveis de ambiente."
        )
        return
    await update.message.reply_text(
        f"🔗 Clique no link abaixo para conectar seu Google Calendar:\n\n{url}\n\nApós autorizar, volte aqui.",
        disable_web_page_preview=True,
    )


async def cmd_conectar_microsoft(update, context):
    """Conectar Microsoft Teams/Outlook Calendar."""
    chat_id = update.effective_chat.id
    url = build_microsoft_auth_url(chat_id)
    if not url:
        await update.message.reply_text(
            "⚠️ Integração Microsoft não configurada. Adicione MICROSOFT_CLIENT_ID e MICROSOFT_CLIENT_SECRET nas variáveis de ambiente."
        )
        return
    await update.message.reply_text(
        f"🔗 Clique no link abaixo para conectar seu Outlook/Teams Calendar:\n\n{url}\n\nApós autorizar, volte aqui.",
        disable_web_page_preview=True,
    )


async def cmd_desconectar(update, context):
    """Desconectar um calendario."""
    args = context.args
    if not args or args[0] not in ("google", "microsoft"):
        await update.message.reply_text("Uso: /desconectar google  ou  /desconectar microsoft")
        return
    provider = args[0]
    supabase_request("DELETE", "configuracoes", params={"chave": f"eq.{provider}_calendar_tokens"})
    await update.message.reply_text(f"✅ {provider.title()} Calendar desconectado.")


async def cmd_agenda(update, context):
    """Mostrar agenda do dia com eventos de todos os calendarios."""
    hoje = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d")
    eventos = supabase_request("GET", "eventos_calendario", params={
        "dia": f"eq.{hoje}",
        "order": "data_inicio.asc",
    }) or []

    if not eventos:
        await update.message.reply_text(
            "📅 Nenhum evento no calendário para hoje.\n\n"
            "Use /conectar_google ou /conectar_microsoft para sincronizar."
        )
        return

    lines = [f"📅 *Agenda de Hoje* ({hoje})\n"]
    for ev in eventos:
        icon = "🟦" if ev["provider"] == "microsoft" else "🟩"
        time_str = f"{ev['horario_inicio']}-{ev['horario_fim']}" if ev["horario_inicio"] else "Dia todo"
        platform = ""
        if ev.get("meeting_link"):
            platform = f" · [Entrar]({ev['meeting_link']})"
        lines.append(f"{icon} *{time_str}* — {ev['titulo']}{platform}")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True,
    )


async def cmd_sync(update, context):
    """Forcar sincronizacao dos calendarios."""
    await update.message.reply_text("🔄 Sincronizando calendários...")
    results = sync_all_calendars()

    parts = []
    if results["google"] > 0:
        parts.append(f"Google Calendar: {results['google']} eventos")
    if results.get("google_tasks", 0) > 0:
        parts.append(f"Google Tasks: {results['google_tasks']} tarefas")
    if results["microsoft"] > 0:
        parts.append(f"Outlook: {results['microsoft']} eventos")
    if results["errors"]:
        parts.append(f"Erros: {', '.join(results['errors'])}")
    if not parts:
        parts.append("Nenhum calendário conectado")

    await update.message.reply_text(f"✅ Sync completo!\n" + "\n".join(parts))


async def sync_calendarios_job(context):
    """Job que sincroniza calendarios a cada 15 minutos."""
    try:
        results = sync_all_calendars()
        total = results.get("google", 0) + results.get("microsoft", 0) + results.get("google_tasks", 0)
        if total > 0:
            logger.info(f"Calendar sync: {total} eventos sincronizados")

        # Agendar lembretes para eventos proximos
        await agendar_lembretes_calendario(context)
    except Exception as e:
        logger.error(f"Erro no sync de calendarios: {e}")


async def agendar_lembretes_calendario(context):
    """Agenda lembretes Telegram para eventos proximos."""
    agora = datetime.now(TZ_RECIFE)
    eventos = get_upcoming_events(minutes_ahead=45)

    for ev in eventos:
        try:
            inicio = datetime.fromisoformat(ev["data_inicio"])
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=TZ_RECIFE)
            delta = (inicio - agora).total_seconds()
            reminder_delay = delta - 900  # 15 min antes

            if 0 < reminder_delay < 2700:  # entre 0 e 45 min
                job_name = f"cal_reminder_{ev['id']}"
                existing = context.job_queue.get_jobs_by_name(job_name)
                if not existing:
                    context.job_queue.run_once(
                        enviar_lembrete_calendario,
                        when=reminder_delay,
                        data=ev,
                        name=job_name,
                    )
        except Exception as e:
            logger.error(f"Erro agendando lembrete calendario: {e}")


async def enviar_lembrete_calendario(context):
    """Envia lembrete de evento do calendario."""
    ev = context.job.data
    icon = "🟦" if ev["provider"] == "microsoft" else "🟩"
    platform = ev.get("meeting_platform", "").title() or ev["provider"].title()

    msg = f"⏰ *Em 15 minutos:*\n\n"
    msg += f"{icon} *{ev['titulo']}*\n"
    msg += f"🕐 {ev['horario_inicio']} - {ev['horario_fim']}\n"
    if ev.get("local_evento"):
        msg += f"📍 {ev['local_evento']}\n"
    msg += f"📌 {platform}\n"
    if ev.get("meeting_link"):
        msg += f"\n🔗 [Entrar na reunião]({ev['meeting_link']})"

    # Obter chat_id da configuracoes
    chat_id = get_chat_id()
    if chat_id:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=msg,
                parse_mode="Markdown", disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Erro enviando lembrete calendario: {e}")


# ========== SETUP ==========

async def setup_commands(app):
    """Configura comandos no menu do Telegram."""
    commands = [
        BotCommand("start", "Iniciar o bot"),
        BotCommand("tarefas", "Ver tarefas pendentes"),
        BotCommand("planejar", "Planejamento inteligente"),
        BotCommand("feedback", "Feedback do dia"),
        BotCommand("resumo", "Resumo rápido"),
        BotCommand("concluir", "Concluir tarefa"),
        BotCommand("editar", "Editar tarefa"),
        BotCommand("relatorio", "Relatório semanal"),
        BotCommand("decompor", "Decompor tarefa em subtarefas"),
        BotCommand("energia", "Registrar nível de energia (1-5)"),
        BotCommand("coaching", "Dica personalizada de produtividade"),
        BotCommand("buscar", "Buscar em tarefas, eventos e anexos"),
        BotCommand("anexar", "Anexar texto/nota a uma tarefa"),
        BotCommand("excluir", "Excluir tarefa"),
        BotCommand("limpar", "Encontrar tarefas duplicadas"),
        BotCommand("foco", "Modo foco (silenciar)"),
        BotCommand("cancelar", "Cancelar operação"),
        BotCommand("gasto", "Registrar gasto"),
        BotCommand("receita", "Registrar receita"),
        BotCommand("saldo", "Ver saldo do mês"),
        BotCommand("extrato", "Últimas transações"),
        BotCommand("orcamento", "Orçamento mensal"),
        BotCommand("financeiro", "Resumo financeiro com IA"),
        BotCommand("agenda", "Ver agenda do dia (todos os calendários)"),
        BotCommand("sync", "Sincronizar calendarios agora"),
        BotCommand("conectar_google", "Conectar Google Calendar"),
        BotCommand("conectar_microsoft", "Conectar Outlook/Teams"),
        BotCommand("desconectar", "Desconectar calendário"),
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

    # Reflexao noturna as 18:00 (todos os dias)
    jq.run_daily(
        reflexao_noturna,
        time=dt_time(18, 0, tzinfo=TZ_RECIFE),
        name="evening_reflection",
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

    # Alerta de vencimentos financeiros as 8:00
    jq.run_daily(
        alerta_vencimentos_job,
        time=dt_time(8, 0, tzinfo=TZ_RECIFE),
        name="finance_due_alert",
    )

    # Carregar lembretes do dia (apos 5s para dar tempo de conectar)
    jq.run_once(
        _verificar_lembretes_iniciais,
        when=5,
        name="initial_reminders",
    )

    # Sync de calendarios a cada 15 minutos (primeiro sync apos 60s)
    jq.run_repeating(sync_calendarios_job, interval=900, first=60, name="calendar_sync")

    logger.info("Jobs programados: resumo 7:30, check-in 13:00, reflexao 18:00, relatorio sex 17:00, recorrentes 6:00, calendar sync 15min")


# ========== HEALTH CHECK (para Koyeb/PaaS) ==========

class HealthHandler(BaseHTTPRequestHandler):
    """Mini servidor HTTP: health check + OAuth callbacks do Google/Microsoft."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/auth/google/callback":
            self._handle_oauth_callback("google", params)
        elif path == "/auth/microsoft/callback":
            self._handle_oauth_callback("microsoft", params)
        else:
            # Health check (comportamento original)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK - Organizador de Tarefas v2 rodando")

    def _handle_oauth_callback(self, provider, params):
        """Processa callback OAuth do Google ou Microsoft."""
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if not code or not state:
            self._respond(400, "Parâmetros faltando (code ou state)")
            return

        chat_id = _verify_state(state)
        if not chat_id:
            self._respond(403, "Estado inválido ou expirado")
            return

        try:
            if provider == "google":
                exchange_google_code(code)
            else:
                exchange_microsoft_code(code)

            self._respond(200, f"✅ {provider.title()} Calendar conectado com sucesso! Pode fechar esta janela e voltar ao Telegram.")

            # Salvar chat_id para notificacoes futuras
            _save_tokens(f"{provider}_chat_id", {"chat_id": chat_id})

        except Exception as e:
            logger.error(f"OAuth {provider} error: {e}")
            self._respond(500, f"Erro ao conectar: {e}")

    def _respond(self, code, message):
        """Envia resposta HTML formatada."""
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#0D1B2A;color:#F5F2ED">
        <h1 style="color:#C4993D">{message}</h1>
        <p>Volte para o Telegram.</p></body></html>"""
        self.wfile.write(html.encode())

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

    # Keep-alive: pinga a propria porta a cada 4 min para evitar sleeping do Koyeb free tier
    def _keep_alive():
        import urllib.request
        while True:
            time.sleep(240)  # 4 minutos
            try:
                urllib.request.urlopen(f"http://localhost:{port}/")
            except Exception:
                pass
    ka_thread = threading.Thread(target=_keep_alive, daemon=True)
    ka_thread.start()


# ========== MAIN ==========

def main():
    logger.info("Iniciando Organizador de Tarefas v2...")
    if ai_brain:
        modo = f"INTELIGENTE v2 ({ai_brain.provider.upper()})"
    else:
        modo = "BASICO (sem IA)"
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
    app.add_handler(CommandHandler("energia", cmd_energia))
    app.add_handler(CommandHandler("coaching", cmd_coaching))
    app.add_handler(CommandHandler("foco", cmd_foco))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("anexar", cmd_anexar))
    app.add_handler(CommandHandler("excluir", cmd_excluir))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("conectar_google", cmd_conectar_google))
    app.add_handler(CommandHandler("conectar_microsoft", cmd_conectar_microsoft))
    app.add_handler(CommandHandler("desconectar", cmd_desconectar))
    app.add_handler(CommandHandler("gasto", cmd_gasto))
    app.add_handler(CommandHandler("receita", cmd_receita))
    app.add_handler(CommandHandler("saldo", cmd_saldo))
    app.add_handler(CommandHandler("extrato", cmd_extrato))
    app.add_handler(CommandHandler("orcamento", cmd_orcamento))
    app.add_handler(CommandHandler("financeiro", cmd_financeiro))
    app.add_handler(CommandHandler("agenda", cmd_agenda))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Bot v2 rodando! Mande /start no Telegram.")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
        poll_interval=2.0,
        timeout=15,
    )


if __name__ == "__main__":
    main()
