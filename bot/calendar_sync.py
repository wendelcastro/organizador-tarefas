"""
Calendar Sync — Integracao Google Calendar + Microsoft Outlook/Teams
====================================================================
Modulo auto-contido que gerencia:
- OAuth2 (Google + Microsoft)
- Fetch de eventos via API
- Normalizacao para schema unificado
- Sincronizacao com Supabase (tabela eventos_calendario)
- Lembretes de eventos proximos

Usa httpx (sync) para todas as chamadas HTTP.
Tokens OAuth ficam na tabela 'configuracoes' do Supabase.
"""

import os
import json
import time
import hmac
import hashlib
import re
import urllib.parse
import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

# ========== CONSTANTES ==========

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_URL = "https://www.googleapis.com/calendar/v3"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/tasks.readonly"

GOOGLE_TASKS_URL = "https://tasks.googleapis.com/tasks/v1"

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_GRAPH_URL = "https://graph.microsoft.com/v1.0"
MICROSOFT_SCOPES = "Calendars.Read offline_access"

# ========== CONFIGURACAO ==========

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
BOT_PUBLIC_URL = os.getenv("BOT_PUBLIC_URL", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
OAUTH_SECRET = os.getenv("OAUTH_SECRET_KEY", "organizador-default-secret")

TZ_RECIFE = timezone(timedelta(hours=-3))

# Timeout padrao para chamadas HTTP
HTTP_TIMEOUT = 15


# ========== SUPABASE HELPER (local, nao depende de main.py) ==========

def _supabase_request(method, endpoint, data=None, params=None, extra_headers=None):
    """Faz requisicao HTTP para a API REST do Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL ou SUPABASE_ANON_KEY nao configurados")
        return None

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

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            if method == "GET":
                resp = client.get(url, headers=headers)
            elif method == "POST":
                resp = client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                resp = client.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                resp = client.delete(url, headers=headers)
            else:
                return None

            if resp.status_code >= 400:
                logger.error(f"Supabase {method} {endpoint} erro {resp.status_code}: {resp.text}")
                return None
            if resp.status_code == 204 or not resp.text:
                return []
            return resp.json()
    except Exception as e:
        logger.error(f"Supabase request error: {e}")
        return None


# ========== OAUTH STATE (HMAC) ==========

def _sign_state(chat_id):
    """Assina chat_id para o parametro state do OAuth."""
    msg = str(chat_id).encode()
    sig = hmac.new(OAUTH_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:16]
    return f"{chat_id}:{sig}"


def _verify_state(state):
    """Verifica e extrai chat_id do state OAuth."""
    try:
        chat_id, sig = state.rsplit(":", 1)
        expected = hmac.new(OAUTH_SECRET.encode(), chat_id.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expected):
            return int(chat_id)
    except Exception:
        pass
    return None


# ========== AUTH URLs ==========

def build_google_auth_url(chat_id):
    """Gera URL de autorizacao do Google Calendar."""
    if not GOOGLE_CLIENT_ID or not BOT_PUBLIC_URL:
        return None

    params = {
        "response_type": "code",
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{BOT_PUBLIC_URL}/auth/google/callback",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": _sign_state(chat_id),
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def build_microsoft_auth_url(chat_id):
    """Gera URL de autorizacao do Microsoft/Teams Calendar."""
    if not MICROSOFT_CLIENT_ID or not BOT_PUBLIC_URL:
        return None

    params = {
        "response_type": "code",
        "client_id": MICROSOFT_CLIENT_ID,
        "redirect_uri": f"{BOT_PUBLIC_URL}/auth/microsoft/callback",
        "scope": MICROSOFT_SCOPES,
        "state": _sign_state(chat_id),
    }
    return f"{MICROSOFT_AUTH_URL}?{urllib.parse.urlencode(params)}"


# ========== TOKEN EXCHANGE ==========

def exchange_google_code(code):
    """Troca authorization code por tokens do Google."""
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{BOT_PUBLIC_URL}/auth/google/callback",
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()

    # Calcular expires_at absoluto
    expires_in = tokens.get("expires_in", 3600)
    tokens["expires_at"] = time.time() + expires_in

    _save_tokens("google", tokens)
    logger.info("Google Calendar tokens salvos com sucesso")
    return tokens


def exchange_microsoft_code(code):
    """Troca authorization code por tokens da Microsoft."""
    data = {
        "code": code,
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "redirect_uri": f"{BOT_PUBLIC_URL}/auth/microsoft/callback",
        "grant_type": "authorization_code",
        "scope": MICROSOFT_SCOPES,
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        resp = client.post(MICROSOFT_TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()

    expires_in = tokens.get("expires_in", 3600)
    tokens["expires_at"] = time.time() + expires_in

    _save_tokens("microsoft", tokens)
    logger.info("Microsoft Calendar tokens salvos com sucesso")
    return tokens


# ========== TOKEN STORAGE (Supabase configuracoes) ==========

def _save_tokens(provider, tokens):
    """Salva tokens OAuth na tabela configuracoes do Supabase (upsert)."""
    chave = f"{provider}_calendar_tokens"
    valor = json.dumps(tokens) if isinstance(tokens, dict) else tokens

    _supabase_request(
        "POST",
        "configuracoes",
        data={"chave": chave, "valor": valor},
        extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )


def _load_tokens(provider):
    """Carrega tokens OAuth da tabela configuracoes."""
    result = _supabase_request("GET", "configuracoes", params={
        "chave": f"eq.{provider}_calendar_tokens",
        "select": "valor",
    })
    if result and len(result) > 0:
        try:
            return json.loads(result[0]["valor"])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return None


# ========== TOKEN REFRESH ==========

def _refresh_google_token(refresh_token):
    """Renova access_token do Google usando refresh_token."""
    data = {
        "refresh_token": refresh_token,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        resp = client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        new_tokens = resp.json()

    new_tokens["refresh_token"] = refresh_token  # Google nem sempre retorna refresh_token
    new_tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 3600)
    return new_tokens


def _refresh_microsoft_token(refresh_token):
    """Renova access_token da Microsoft usando refresh_token."""
    data = {
        "refresh_token": refresh_token,
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "scope": MICROSOFT_SCOPES,
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        resp = client.post(MICROSOFT_TOKEN_URL, data=data)
        resp.raise_for_status()
        new_tokens = resp.json()

    new_tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 3600)
    return new_tokens


def get_valid_token(provider):
    """Retorna access_token valido, renovando se necessario."""
    tokens = _load_tokens(provider)
    if not tokens:
        return None

    # Verificar expiracao (com margem de 5 min)
    expires_at = tokens.get("expires_at", 0)
    if time.time() > expires_at - 300:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            logger.warning(f"{provider}: token expirado sem refresh_token")
            return None
        try:
            if provider == "google":
                tokens = _refresh_google_token(refresh_token)
            else:
                tokens = _refresh_microsoft_token(refresh_token)
            _save_tokens(provider, tokens)
            logger.info(f"{provider}: token renovado com sucesso")
        except Exception as e:
            logger.error(f"{provider}: erro ao renovar token: {e}")
            return None

    return tokens.get("access_token")


# ========== FETCH EVENTS ==========

def fetch_google_events(days_ahead=14):
    """Busca eventos do Google Calendar."""
    token = get_valid_token("google")
    if not token:
        return []

    now = datetime.now(TZ_RECIFE)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(
                f"{GOOGLE_CALENDAR_URL}/calendars/primary/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": "200",
                },
            )
            if resp.status_code == 401:
                logger.warning("Google: token invalido, tentando renovar...")
                # Forcar refresh
                tokens = _load_tokens("google")
                if tokens and tokens.get("refresh_token"):
                    new_tokens = _refresh_google_token(tokens["refresh_token"])
                    _save_tokens("google", new_tokens)
                    resp = client.get(
                        f"{GOOGLE_CALENDAR_URL}/calendars/primary/events",
                        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
                        params={
                            "timeMin": time_min,
                            "timeMax": time_max,
                            "singleEvents": "true",
                            "orderBy": "startTime",
                            "maxResults": "200",
                        },
                    )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Google Calendar fetch error: {e}")
        return []

    events = []
    for item in data.get("items", []):
        try:
            events.append(_normalize_event(item, "google"))
        except Exception as e:
            logger.warning(f"Google: erro ao normalizar evento: {e}")
    return events


def fetch_microsoft_events(days_ahead=14):
    """Busca eventos do Microsoft/Outlook Calendar."""
    token = get_valid_token("microsoft")
    if not token:
        return []

    now = datetime.now(TZ_RECIFE)
    start_dt = now.strftime("%Y-%m-%dT%H:%M:%S")
    end_dt = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(
                f"{MICROSOFT_GRAPH_URL}/me/calendarView",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Prefer": 'outlook.timezone="America/Recife"',
                },
                params={
                    "startDateTime": start_dt,
                    "endDateTime": end_dt,
                    "$select": "id,subject,body,location,start,end,onlineMeeting,recurrence,isAllDay",
                    "$orderby": "start/dateTime",
                    "$top": "200",
                },
            )
            if resp.status_code == 401:
                logger.warning("Microsoft: token invalido, tentando renovar...")
                tokens = _load_tokens("microsoft")
                if tokens and tokens.get("refresh_token"):
                    new_tokens = _refresh_microsoft_token(tokens["refresh_token"])
                    _save_tokens("microsoft", new_tokens)
                    resp = client.get(
                        f"{MICROSOFT_GRAPH_URL}/me/calendarView",
                        headers={
                            "Authorization": f"Bearer {new_tokens['access_token']}",
                            "Prefer": 'outlook.timezone="America/Recife"',
                        },
                        params={
                            "startDateTime": start_dt,
                            "endDateTime": end_dt,
                            "$select": "id,subject,body,location,start,end,onlineMeeting,recurrence,isAllDay",
                            "$orderby": "start/dateTime",
                            "$top": "200",
                        },
                    )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Microsoft Calendar fetch error: {e}")
        return []

    events = []
    for item in data.get("value", []):
        try:
            events.append(_normalize_event(item, "microsoft"))
        except Exception as e:
            logger.warning(f"Microsoft: erro ao normalizar evento: {e}")
    return events


def fetch_google_tasks():
    """Busca tarefas do Google Tasks (todas as listas, apenas nao concluidas)."""
    token = get_valid_token("google")
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            # 1. Buscar todas as listas de tarefas
            resp = client.get(
                f"{GOOGLE_TASKS_URL}/users/@me/lists",
                headers=headers,
            )
            if resp.status_code == 401:
                logger.warning("Google Tasks: token invalido ou escopo tasks.readonly nao autorizado. "
                               "O usuario precisa desconectar e reconectar o Google para autorizar o novo escopo.")
                return []
            if resp.status_code == 403:
                logger.warning("Google Tasks: escopo tasks.readonly nao autorizado. "
                               "O usuario precisa desconectar e reconectar o Google para autorizar o novo escopo.")
                return []
            resp.raise_for_status()
            task_lists = resp.json().get("items", [])

            # 2. Para cada lista, buscar tarefas pendentes
            all_tasks = []
            for tl in task_lists:
                list_id = tl.get("id")
                if not list_id:
                    continue

                resp = client.get(
                    f"{GOOGLE_TASKS_URL}/lists/{list_id}/tasks",
                    headers=headers,
                    params={
                        "showCompleted": "false",
                        "showHidden": "false",
                        "maxResults": "100",
                    },
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])

                for task in items:
                    try:
                        normalized = _normalize_google_task(task)
                        if normalized:
                            all_tasks.append(normalized)
                    except Exception as e:
                        logger.warning(f"Google Tasks: erro ao normalizar tarefa: {e}")

            return all_tasks

    except Exception as e:
        logger.error(f"Google Tasks fetch error: {e}")
        return []


def _normalize_google_task(task):
    """Normaliza uma tarefa do Google Tasks para o formato eventos_calendario."""
    titulo = task.get("title", "").strip()
    if not titulo:
        return None  # Tarefas sem titulo sao separadores/vazias

    due = task.get("due")  # formato RFC 3339: "2026-03-22T00:00:00.000Z"
    if due:
        try:
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(TZ_RECIFE)
            dia = due_dt.strftime("%Y-%m-%d")
            # Google Tasks due e apenas data, tratar como all-day
            data_inicio = due_dt.replace(hour=0, minute=0, second=0).isoformat()
            data_fim = (due_dt.replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat()
        except (ValueError, TypeError):
            dia = None
            data_inicio = None
            data_fim = None
    else:
        dia = None
        data_inicio = None
        data_fim = None

    # Links da tarefa (se existir)
    links = task.get("links", [])
    meeting_link = links[0].get("link", "") if links else ""

    return {
        "external_id": task.get("id", ""),
        "provider": "google",
        "titulo": f"[Task] {titulo}",
        "descricao": (task.get("notes") or "")[:500],
        "local_evento": "",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "dia": dia,
        "horario_inicio": "",
        "horario_fim": "",
        "all_day": True,
        "meeting_link": meeting_link,
        "meeting_platform": _detect_meeting_platform(meeting_link) if meeting_link else None,
        "recorrente": False,
    }


def create_google_event(titulo, data, horario_inicio=None, horario_fim=None, descricao=""):
    """Cria um evento no Google Calendar.

    Args:
        titulo: Titulo do evento
        data: Data no formato "YYYY-MM-DD"
        horario_inicio: Horario de inicio "HH:MM" (None = all-day)
        horario_fim: Horario de fim "HH:MM" (None = 1h apos inicio ou all-day)
        descricao: Descricao do evento

    Returns:
        ID do evento criado ou None em caso de erro.
    """
    token = get_valid_token("google")
    if not token:
        logger.warning("Google Calendar: sem token valido para criar evento. "
                       "O usuario precisa reconectar o Google com escopo calendar (read/write).")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    if horario_inicio:
        # Evento com horario
        start_dt = f"{data}T{horario_inicio}:00-03:00"
        if horario_fim:
            end_dt = f"{data}T{horario_fim}:00-03:00"
        else:
            # Default: 1h apos inicio
            try:
                h, m = map(int, horario_inicio.split(":"))
                end_h = h + 1
                if end_h >= 24:
                    end_h = 23
                    m = 59
                end_dt = f"{data}T{end_h:02d}:{m:02d}:00-03:00"
            except (ValueError, TypeError):
                end_dt = start_dt

        body = {
            "summary": titulo,
            "description": descricao,
            "start": {"dateTime": start_dt, "timeZone": "America/Recife"},
            "end": {"dateTime": end_dt, "timeZone": "America/Recife"},
        }
    else:
        # Evento all-day
        try:
            dt = datetime.strptime(data, "%Y-%m-%d")
            next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            next_day = data

        body = {
            "summary": titulo,
            "description": descricao,
            "start": {"date": data},
            "end": {"date": next_day},
        }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.post(
                f"{GOOGLE_CALENDAR_URL}/calendars/primary/events",
                headers=headers,
                json=body,
            )
            if resp.status_code == 401:
                logger.warning("Google Calendar: token invalido para criar evento. "
                               "O usuario precisa desconectar e reconectar com escopo calendar (read/write).")
                return None
            if resp.status_code == 403:
                logger.warning("Google Calendar: sem permissao para criar eventos. "
                               "Escopo calendar.readonly ativo — precisa reconectar com escopo calendar (read/write).")
                return None
            resp.raise_for_status()
            created = resp.json()
            event_id = created.get("id")
            logger.info(f"Google Calendar: evento criado — {titulo} ({data}) id={event_id}")
            return event_id
    except Exception as e:
        logger.error(f"Google Calendar: erro ao criar evento: {e}")
        return None


# ========== NORMALIZE ==========

def _strip_html(text):
    """Remove tags HTML de texto."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _detect_meeting_platform(link):
    """Detecta plataforma de reuniao a partir do link."""
    if not link:
        return None
    link_lower = link.lower()
    if "teams.microsoft" in link_lower or "teams.live" in link_lower:
        return "teams"
    if "meet.google" in link_lower:
        return "meet"
    if "zoom.us" in link_lower:
        return "zoom"
    return None


def _parse_datetime_to_recife(dt_str):
    """Converte string datetime para datetime com timezone Recife."""
    if not dt_str:
        return None
    try:
        # Tenta ISO format com timezone
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(TZ_RECIFE)
    except (ValueError, TypeError):
        pass
    try:
        # Formato sem timezone (assume Recife)
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_RECIFE)
        return dt.astimezone(TZ_RECIFE)
    except (ValueError, TypeError):
        return None


def _normalize_event(raw, provider):
    """Normaliza evento para schema unificado."""
    if provider == "google":
        return _normalize_google_event(raw)
    else:
        return _normalize_microsoft_event(raw)


def _normalize_google_event(raw):
    """Normaliza evento do Google Calendar."""
    # Datas
    start = raw.get("start", {})
    end = raw.get("end", {})
    all_day = "date" in start and "dateTime" not in start

    if all_day:
        data_inicio = datetime.strptime(start["date"], "%Y-%m-%d").replace(tzinfo=TZ_RECIFE)
        data_fim = datetime.strptime(end.get("date", start["date"]), "%Y-%m-%d").replace(tzinfo=TZ_RECIFE)
    else:
        data_inicio = _parse_datetime_to_recife(start.get("dateTime"))
        data_fim = _parse_datetime_to_recife(end.get("dateTime"))

    if not data_inicio:
        raise ValueError("Evento Google sem data de inicio")

    # Meeting link
    meeting_link = raw.get("hangoutLink", "")
    if not meeting_link:
        conf_data = raw.get("conferenceData", {})
        entry_points = conf_data.get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                meeting_link = ep.get("uri", "")
                break

    return {
        "external_id": raw.get("id", ""),
        "provider": "google",
        "titulo": raw.get("summary", "(Sem titulo)"),
        "descricao": raw.get("description", "")[:500],
        "local_evento": raw.get("location", ""),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat() if data_fim else data_inicio.isoformat(),
        "dia": data_inicio.strftime("%Y-%m-%d"),
        "horario_inicio": "" if all_day else data_inicio.strftime("%H:%M"),
        "horario_fim": "" if all_day else (data_fim.strftime("%H:%M") if data_fim else ""),
        "all_day": all_day,
        "meeting_link": meeting_link or "",
        "meeting_platform": _detect_meeting_platform(meeting_link),
        "recorrente": bool(raw.get("recurringEventId")),
    }


def _normalize_microsoft_event(raw):
    """Normaliza evento do Microsoft/Outlook Calendar."""
    all_day = raw.get("isAllDay", False)

    start = raw.get("start", {})
    end = raw.get("end", {})
    data_inicio = _parse_datetime_to_recife(start.get("dateTime"))
    data_fim = _parse_datetime_to_recife(end.get("dateTime"))

    if not data_inicio:
        raise ValueError("Evento Microsoft sem data de inicio")

    # Meeting link
    online_meeting = raw.get("onlineMeeting") or {}
    meeting_link = online_meeting.get("joinUrl", "")
    meeting_platform = "teams" if online_meeting.get("joinUrl") else None

    # Se nao for Teams, tentar detectar por link
    if not meeting_platform and meeting_link:
        meeting_platform = _detect_meeting_platform(meeting_link)

    # Descricao (strip HTML)
    body = raw.get("body", {})
    descricao = _strip_html(body.get("content", ""))[:500] if body.get("contentType") == "html" else body.get("content", "")[:500]

    # Local
    location = raw.get("location", {})
    local_evento = location.get("displayName", "") if isinstance(location, dict) else ""

    return {
        "external_id": raw.get("id", ""),
        "provider": "microsoft",
        "titulo": raw.get("subject", "(Sem titulo)"),
        "descricao": descricao,
        "local_evento": local_evento,
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat() if data_fim else data_inicio.isoformat(),
        "dia": data_inicio.strftime("%Y-%m-%d"),
        "horario_inicio": "" if all_day else data_inicio.strftime("%H:%M"),
        "horario_fim": "" if all_day else (data_fim.strftime("%H:%M") if data_fim else ""),
        "all_day": all_day,
        "meeting_link": meeting_link or "",
        "meeting_platform": meeting_platform,
        "recorrente": bool(raw.get("recurrence")),
    }


# ========== SYNC ==========

def sync_all_calendars():
    """Sincroniza todos os calendarios conectados com o Supabase."""
    results = {"google": 0, "microsoft": 0, "google_tasks": 0, "errors": []}

    for provider in ("google", "microsoft"):
        tokens = _load_tokens(provider)
        if not tokens:
            continue

        try:
            if provider == "google":
                events = fetch_google_events()
            else:
                events = fetch_microsoft_events()

            if not events:
                continue

            # Upsert cada evento
            for ev in events:
                resp = _supabase_request(
                    "POST",
                    "eventos_calendario",
                    data=ev,
                    extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
                )
                if resp is not None:
                    results[provider] += 1

            # Limpar eventos antigos deste provider que nao vieram mais no sync
            # (apenas para o range sincronizado)
            if events:
                synced_ids = [ev["external_id"] for ev in events]
                now = datetime.now(TZ_RECIFE)
                future = (now + timedelta(days=14))

                # Buscar eventos existentes no range
                existing = _supabase_request("GET", "eventos_calendario", params={
                    "provider": f"eq.{provider}",
                    "data_inicio": f"gte.{now.isoformat()}",
                    "data_fim": f"lte.{future.isoformat()}",
                    "select": "id,external_id",
                })
                if existing:
                    for ex in existing:
                        if ex.get("external_id") not in synced_ids:
                            _supabase_request("DELETE", f"eventos_calendario?id=eq.{ex['id']}")

            logger.info(f"Calendar sync {provider}: {results[provider]} eventos")

        except Exception as e:
            error_msg = f"{provider}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"Calendar sync error — {error_msg}")

    # Sync Google Tasks (usa mesmo token Google, escopo tasks.readonly)
    google_tokens = _load_tokens("google")
    if google_tokens:
        try:
            tasks = fetch_google_tasks()
            for t in tasks:
                if not t.get("data_inicio"):
                    continue  # Tarefas sem data nao entram no calendario
                resp = _supabase_request(
                    "POST",
                    "eventos_calendario",
                    data=t,
                    extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
                )
                if resp is not None:
                    results["google_tasks"] += 1

            if tasks:
                logger.info(f"Calendar sync google_tasks: {results['google_tasks']} tarefas")
        except Exception as e:
            error_msg = f"google_tasks: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"Calendar sync error — {error_msg}")

    return results


# ========== UPCOMING EVENTS (para lembretes) ==========

def get_upcoming_events(minutes_ahead=60):
    """Busca eventos proximos do Supabase (para agendar lembretes)."""
    now = datetime.now(TZ_RECIFE)
    future = now + timedelta(minutes=minutes_ahead)

    result = _supabase_request("GET", "eventos_calendario", params={
        "data_inicio": f"gte.{now.isoformat()}",
        "data_fim": f"lte.{future.isoformat()}",
        "all_day": "eq.false",
        "order": "data_inicio.asc",
        "select": "id,external_id,provider,titulo,descricao,local_evento,data_inicio,data_fim,horario_inicio,horario_fim,meeting_link,meeting_platform",
    })
    return result or []
