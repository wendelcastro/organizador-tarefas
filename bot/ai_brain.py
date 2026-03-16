"""
AI Brain — O cerebro do Organizador de Tarefas
================================================
Usa Claude API para ser INTELIGENTE de verdade:
- Classifica tarefas com contexto (nao keywords)
- Confirma antes de salvar (pergunta no Telegram)
- Planeja o dia de forma realista
- Detecta sobrecarga e sugere redistribuicao
- Da feedback construtivo no fim do dia
- Aprende padroes do usuario ao longo do tempo
- Protege tempo pessoal (ingles, leitura)
"""

import json
import logging
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

# ========== SYSTEM PROMPT — A PERSONALIDADE DA IA ==========

SYSTEM_PROMPT = """Voce e o assistente pessoal do Professor Wendel Castro.
Wendel e professor de IA e Banco de Dados na Ser Educacional (Recife-PE).
Ele tambem faz consultorias em dados e tem projetos pessoais.

## SEU PAPEL
Voce e o CEREBRO de um organizador de tarefas inteligente.
Nao e um chatbot generico — voce ORGANIZA a vida do Wendel.

## O QUE VOCE SABE SOBRE O WENDEL
- Sofre com sobrecarga mental: muitas demandas, sensacao de nao dar conta
- Tende a colocar tarefas demais no mesmo dia
- Precisa proteger tempo pessoal: ingles (30min/dia) e leitura
- Trabalha como professor, consultor e tem projetos pessoais
- Categorias: Trabalho, Consultoria, Grupo Ser, Pessoal
- Fuso horario: America/Recife (UTC-3)

## COMO VOCE FUNCIONA

### Quando recebe uma tarefa nova:
1. Analise o texto e extraia: titulo limpo, categoria, prioridade, prazo, horario
2. SEMPRE responda em formato JSON com a classificacao E uma pergunta de confirmacao
3. Seja inteligente: "reuniao com coordenacao" = Grupo Ser + alta prioridade
4. Se nao conseguir inferir prazo, PERGUNTE
5. Se o dia ja esta cheio, ALERTE sobre sobrecarga

### Quando recebe pedido de planejamento do dia:
1. Olhe todas as tarefas pendentes para o dia
2. Distribua de forma REALISTA com margens de tempo
3. Inclua pausas (almoco, cafe)
4. PROTEJA ingles e leitura — nao podem ser cortados
5. Se tem tarefas demais, sugira redistribuir

### Quando recebe pedido de feedback:
1. Resuma o que foi concluido no dia
2. Destaque o que ficou pendente sem julgamento
3. De feedback CONSTRUTIVO — Wendel precisa de apoio, nao pressao
4. Sugira ajustes para o dia seguinte

## REGRAS DE PRIORIZACAO
- Nao e so alta/media/baixa
- Considere: prazo (urgencia) + impacto (importancia) + contexto
- Aula amanha = URGENTE E IMPORTANTE
- Comprar presente com prazo longe = pode esperar
- Reuniao com coordenacao = alta (impacto institucional)

## TOM DE VOZ
- Portugues BR, informal mas respeitoso
- Direto e objetivo — Wendel nao quer textao
- Use emojis com moderacao
- Seja honesto: se tem tarefa demais, DIGA
- Nunca seja passivo-agressivo ou robótico

## FORMATO DE RESPOSTA PARA CLASSIFICACAO DE TAREFA
Quando classificar uma tarefa, responda APENAS com JSON valido:
{
  "titulo": "titulo limpo e claro da tarefa",
  "categoria": "Trabalho|Consultoria|Grupo Ser|Pessoal",
  "prioridade": "alta|media|baixa",
  "prazo": "YYYY-MM-DD ou null",
  "horario": "HH:MM ou null",
  "meeting_link": "url ou null",
  "meeting_platform": "zoom|meet|teams|null",
  "tempo_estimado_min": 30,
  "mensagem": "mensagem curta de confirmacao para o Wendel",
  "alerta_sobrecarga": false,
  "alerta_msg": null
}
"""

CONFIRM_PROMPT = """O usuario esta CONFIRMANDO ou AJUSTANDO uma tarefa.
A tarefa pendente de confirmacao e:
{tarefa_json}

Se o usuario confirmar (ex: "ok", "sim", "confirma", "isso", "salva", "pode ser"):
Responda com: {{"acao": "salvar"}}

Se o usuario quiser ajustar (ex: "muda pra sexta", "prioridade baixa", "e trabalho"):
Responda com a tarefa atualizada no mesmo formato JSON de classificacao.

Se o usuario cancelar (ex: "cancela", "nao", "esquece"):
Responda com: {{"acao": "cancelar"}}

Responda APENAS com JSON valido.
"""

PLANNING_PROMPT = """Planeje o dia do Wendel de forma REALISTA.

Data: {data}
Tarefas pendentes para hoje e atrasadas:
{tarefas_json}

Regras:
1. Distribua as tarefas em blocos de tempo realistas
2. Inclua: almoco (12:00-13:00), cafe (15:30-15:45)
3. OBRIGATORIO: ingles 30min e leitura 20min (tempo pessoal protegido)
4. Jornada: 08:00 ate 18:00 (pode flexibilizar ate 19:00 se necessario)
5. Se tem tarefa demais, sugira o que ADIAR para outro dia
6. Margens: adicione 15-20% a mais de tempo em cada tarefa
7. Reunioes com horario fixo nao podem ser movidas

Responda em texto formatado para Telegram (Markdown), NAO em JSON.
Use emojis com moderacao. Seja direto e realista.
Se o dia esta pesado demais, DIGA CLARAMENTE.
"""

FEEDBACK_PROMPT = """De o feedback do dia do Wendel.

Data: {data}
Tarefas concluidas hoje:
{concluidas_json}

Tarefas que ficaram pendentes:
{pendentes_json}

Regras:
1. Comece destacando o que foi FEITO (reforco positivo)
2. Mencione o que ficou pendente SEM julgamento
3. Se fez ingles/leitura, elogie
4. Se nao fez, lembre gentilmente
5. Sugira 1-2 ajustes concretos para amanha
6. Tom: coach motivacional, NAO chefe cobrando
7. Wendel sofre com sobrecarga — alivie, nao pressione

Responda em texto formatado para Telegram (Markdown).
Maximo 15 linhas — conciso e impactante.
"""

CHAT_PROMPT = """O usuario esta conversando sobre o feedback ou sobre organizacao.
Historico recente:
{historico}

Responda como o assistente pessoal dele.
Seja direto, util e mantenha o foco em organizacao/produtividade.
Se ele quiser discutir, discuta. Se quiser ajustar algo, ajuste.
Responda em texto formatado para Telegram (Markdown).
"""


class AIBrain:
    """Cerebro do organizador — integra com Claude API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=30,
        )

    def _call_claude(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        """Chama a Claude API e retorna a resposta como texto."""
        try:
            resp = self.client.post(
                "/v1/messages",
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )

            if resp.status_code != 200:
                logger.error(f"Claude API erro {resp.status_code}: {resp.text}")
                return None

            data = resp.json()
            return data["content"][0]["text"]

        except Exception as e:
            logger.error(f"Erro ao chamar Claude: {e}")
            return None

    def _call_claude_with_history(self, system: str, messages: list, max_tokens: int = 1024) -> str:
        """Chama Claude com historico de mensagens."""
        try:
            resp = self.client.post(
                "/v1/messages",
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                },
            )

            if resp.status_code != 200:
                logger.error(f"Claude API erro {resp.status_code}: {resp.text}")
                return None

            data = resp.json()
            return data["content"][0]["text"]

        except Exception as e:
            logger.error(f"Erro ao chamar Claude: {e}")
            return None

    def _parse_json(self, text: str) -> dict:
        """Extrai JSON de uma resposta que pode ter texto ao redor."""
        if not text:
            return None
        # Tenta extrair JSON de dentro de ```json ... ``` ou direto
        import re
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Tenta encontrar o primeiro { ... }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao parsear JSON: {text[:200]}")
            return None

    # ========== FUNCOES PUBLICAS ==========

    def classificar_tarefa(self, texto: str, tarefas_do_dia: list = None) -> dict:
        """
        Classifica uma tarefa usando Claude.
        Retorna dict com classificacao + mensagem de confirmacao.
        """
        hoje = datetime.now()
        contexto = f"Data/hora atual: {hoje.strftime('%Y-%m-%d %H:%M')} ({hoje.strftime('%A')})\n"
        contexto += f"Texto do usuario: {texto}\n"

        if tarefas_do_dia:
            contexto += f"\nTarefas ja no dia de hoje ({len(tarefas_do_dia)}):\n"
            for t in tarefas_do_dia:
                contexto += f"- {t.get('titulo', '')} ({t.get('horario', 'sem horario')})\n"

        resposta = self._call_claude(SYSTEM_PROMPT, contexto)
        result = self._parse_json(resposta)

        if not result:
            # Fallback: retorna classificacao basica
            return {
                "titulo": texto,
                "categoria": "Pessoal",
                "prioridade": "media",
                "prazo": None,
                "horario": None,
                "meeting_link": None,
                "meeting_platform": None,
                "tempo_estimado_min": 30,
                "mensagem": "Nao consegui classificar automaticamente. Confirma como esta ou ajusta?",
                "alerta_sobrecarga": False,
                "alerta_msg": None,
            }

        return result

    def processar_confirmacao(self, resposta_usuario: str, tarefa_pendente: dict) -> dict:
        """
        Processa a resposta do usuario ao pedido de confirmacao.
        Retorna: {"acao": "salvar"}, {"acao": "cancelar"}, ou tarefa atualizada.
        """
        system = SYSTEM_PROMPT + "\n\n" + CONFIRM_PROMPT.format(
            tarefa_json=json.dumps(tarefa_pendente, ensure_ascii=False)
        )
        resposta = self._call_claude(system, resposta_usuario)
        result = self._parse_json(resposta)

        if not result:
            # Se nao entendeu, assume confirmacao
            return {"acao": "salvar"}

        return result

    def planejar_dia(self, tarefas: list, data: str = None) -> str:
        """
        Gera planejamento do dia.
        Retorna texto formatado para Telegram.
        """
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        tarefas_json = json.dumps(tarefas, ensure_ascii=False, indent=2)
        prompt = PLANNING_PROMPT.format(data=data, tarefas_json=tarefas_json)

        resposta = self._call_claude(SYSTEM_PROMPT, prompt, max_tokens=2048)
        return resposta or "Nao consegui gerar o planejamento. Tente novamente."

    def feedback_dia(self, concluidas: list, pendentes: list, data: str = None) -> str:
        """
        Gera feedback do dia.
        Retorna texto formatado para Telegram.
        """
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        prompt = FEEDBACK_PROMPT.format(
            data=data,
            concluidas_json=json.dumps(concluidas, ensure_ascii=False, indent=2),
            pendentes_json=json.dumps(pendentes, ensure_ascii=False, indent=2),
        )

        resposta = self._call_claude(SYSTEM_PROMPT, prompt, max_tokens=2048)
        return resposta or "Nao consegui gerar o feedback. Tente novamente."

    def conversar(self, mensagem: str, historico: list) -> str:
        """
        Conversa livre sobre organizacao/feedback.
        Usa historico para manter contexto.
        """
        system = SYSTEM_PROMPT + "\n\n" + CHAT_PROMPT.format(
            historico=json.dumps(historico[-6:], ensure_ascii=False)  # ultimas 6 msgs
        )

        messages = []
        for msg in historico[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": mensagem})

        resposta = self._call_claude_with_history(system, messages, max_tokens=1024)
        return resposta or "Desculpa, tive um problema. Tenta de novo?"
