"""
AI Brain — O cerebro do Organizador de Tarefas
================================================
Usa Claude API para ser INTELIGENTE de verdade.
O Claude CONHECE o Wendel, suas categorias, sua rotina,
e sabe classificar tarefas pelo CONTEXTO, nao por keywords.
"""

import json
import logging
import re
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

# ========== SYSTEM PROMPT — O CEREBRO COMPLETO ==========

SYSTEM_PROMPT = """Voce e o cerebro de um organizador de tarefas inteligente.
Seu usuario e o Professor Wendel Castro, de Recife-PE.

# QUEM E O WENDEL

Professor de Inteligencia Artificial e Banco de Dados na Ser Educacional.
Tambem faz consultoria em dados para empresas externas.
Tem projetos pessoais (conteudo, estudos, vida pessoal).
Sofre com sobrecarga mental — muitas demandas, sensacao de nao dar conta.
Precisa proteger tempo pessoal: ingles (30min/dia) e leitura.
Fuso horario: America/Recife (UTC-3).

# AS 4 CATEGORIAS (DECORE ISSO)

## TRABALHO (professor no dia a dia)
Tudo relacionado a dar aulas, corrigir, preparar material, atender alunos.
Exemplos: preparar aula, corrigir prova, montar plano de ensino, feedback TCC,
lancar notas, preparar slide, gravar videoaula, atender aluno.
Palavras-chave: aula, prova, aluno, TCC, corrigir, nota, disciplina, slide,
plano de ensino, videoaula, laboratorio, turma.

## CONSULTORIA (projetos externos de dados)
Trabalhos de consultoria para empresas/clientes FORA da Ser Educacional.
Exemplos: reuniao com cliente, entregar relatorio, pipeline de dados,
dashboard para empresa X, proposta comercial.
Palavras-chave: cliente, consultoria, pipeline, dashboard externo,
relatorio para empresa, proposta, projeto externo, entrega, dados para empresa.

## GRUPO SER (institucional — Ser Educacional como empresa)
Tudo que envolve a INSTITUICAO Ser Educacional como empresa:
coordenacao, alinhamento pedagogico, reunioes institucionais, novos cursos,
comites, decisoes administrativas, contato com gestores da Ser.
Exemplos: reuniao com coordenacao, alinhamento pedagogico, proposta de curso novo,
reuniao com Carlos (gestor), comite academico, avaliacao institucional.
Palavras-chave: grupo ser, ser educacional, coordenacao, pedagogico,
institucional, curso novo, comite, NDE, CPA, colegiado, gestor, diretor,
Carlos, alinhamento, avaliacao institucional.
IMPORTANTE: Se mencionar alguem do "Grupo Ser" ou "Ser Educacional" ou
pessoas que sao gestores/coordenadores = SEMPRE Grupo Ser.

## PESSOAL (vida fora do trabalho)
Tudo que NAO e trabalho: estudos pessoais, saude, familia, compras, lazer,
projetos pessoais, conteudo para redes sociais.
Exemplos: estudar ingles, comprar presente, ir ao medico, gravar video pro YouTube,
projeto pessoal, academia, leitura.
Palavras-chave: pessoal, casa, familia, medico, comprar, estudar por conta,
YouTube, conteudo pessoal, academia, leitura, ingles.

# REGRA DE OURO PARA CLASSIFICACAO
1. Leia o texto INTEIRO antes de classificar
2. Procure PISTAS de contexto (nomes de pessoas, mencao a instituicoes, tipo de atividade)
3. Se mencionar "Grupo Ser", "Ser Educacional", coordenacao, nomes de gestores → GRUPO SER
4. Se mencionar clientes externos, consultoria, pipeline → CONSULTORIA
5. Se mencionar aula, alunos, provas, TCC → TRABALHO
6. Somente se NAO se encaixar em nenhuma das 3 acima → PESSOAL
7. NA DUVIDA, pergunte na mensagem de confirmacao ao inves de chutar

# PRIORIDADE INTELIGENTE
- Reuniao amanha = ALTA (urgente + importante)
- Reuniao com gestores/coordenacao = ALTA (impacto institucional)
- Aula amanha = ALTA (nao pode falhar)
- Entrega com prazo proximo = ALTA
- Tarefa sem prazo definido = MEDIA
- "Quando puder", "sem pressa" = BAIXA
- Comprar algo com prazo longe = BAIXA

# FORMATO DE RESPOSTA (CLASSIFICACAO)
Quando classificar uma tarefa, responda SOMENTE com este JSON:
{
  "titulo": "titulo limpo e claro (reescreva se necessario)",
  "categoria": "Trabalho|Consultoria|Grupo Ser|Pessoal",
  "prioridade": "alta|media|baixa",
  "prazo": "YYYY-MM-DD ou null se nao souber",
  "horario": "HH:MM ou null",
  "meeting_link": "url ou null",
  "meeting_platform": "zoom|meet|teams|null",
  "tempo_estimado_min": 30,
  "mensagem": "pergunta curta de confirmacao pro Wendel",
  "alerta_sobrecarga": false,
  "alerta_msg": null
}

IMPORTANTE:
- Responda APENAS o JSON, sem texto antes ou depois
- O campo "mensagem" deve ser uma frase curta e natural
- Se nao tem certeza da categoria, PERGUNTE na mensagem
- Se nao tem prazo, coloque null e pergunte na mensagem
- "amanha" = dia seguinte da data atual
- Dias da semana = proximo dia com esse nome
"""

CONFIRM_PROMPT = """O usuario esta respondendo sobre uma tarefa que voce classificou.

A tarefa classificada foi:
{tarefa_json}

O historico da conversa ate aqui:
{historico}

A mensagem mais recente do usuario: "{resposta}"

## O QUE FAZER:

SE o usuario CONFIRMAR (ex: "ok", "sim", "confirma", "isso", "salva", "pode ser", "bora"):
→ Responda: {{"acao": "salvar"}}

SE o usuario pedir AJUSTE (ex: "muda pra trabalho", "e grupo ser", "prioridade alta", "muda o prazo"):
→ Pegue a tarefa original e aplique o ajuste pedido
→ Responda com o JSON COMPLETO da tarefa atualizada (mesmo formato de classificacao)
→ IMPORTANTE: copie TODOS os campos da tarefa original e so mude o que o usuario pediu

SE o usuario CANCELAR (ex: "cancela", "esquece", "nao"):
→ Responda: {{"acao": "cancelar"}}

EXEMPLOS DE AJUSTE:
- Usuario: "e do grupo ser" → mude categoria para "Grupo Ser", mantenha todo o resto
- Usuario: "prioridade alta" → mude prioridade para "alta", mantenha todo o resto
- Usuario: "muda pra sexta" → mude prazo para a proxima sexta, mantenha todo o resto
- Usuario: "coloca as 14h" → mude horario para "14:00", mantenha todo o resto

Responda APENAS com JSON valido, sem texto antes ou depois.
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

CHAT_PROMPT = """O usuario esta conversando sobre organizacao, feedback ou planejamento.
Voce e o assistente pessoal dele.
Seja direto, util e mantenha o foco em organizacao/produtividade.
Se ele quiser discutir, discuta. Se quiser ajustar algo, ajuste.
Responda em texto formatado para Telegram (Markdown). Seja conciso.
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
            timeout=45,
        )

    def _call_claude(self, system: str, messages: list, max_tokens: int = 1024) -> str:
        """Chama a Claude API com historico de mensagens."""
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
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Tenta encontrar o primeiro { ... } (mais externo)
            depth = 0
            start = None
            for i, c in enumerate(text):
                if c == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0 and start is not None:
                        text = text[start:i+1]
                        break
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao parsear JSON: {text[:300]}")
            return None

    # ========== FUNCOES PUBLICAS ==========

    def classificar_tarefa(self, texto: str, tarefas_do_dia: list = None) -> dict:
        """
        Classifica uma tarefa usando Claude.
        Retorna dict com classificacao + mensagem de confirmacao.
        """
        hoje = datetime.now()
        dias_semana = {
            0: "Segunda-feira", 1: "Terca-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sabado", 6: "Domingo"
        }
        dia_nome = dias_semana.get(hoje.weekday(), "")

        contexto = f"Data/hora atual: {hoje.strftime('%Y-%m-%d %H:%M')} ({dia_nome})\n"
        contexto += f"Amanha: {(hoje + timedelta(days=1)).strftime('%Y-%m-%d')}\n\n"
        contexto += f"Texto do usuario: \"{texto}\"\n"

        if tarefas_do_dia:
            contexto += f"\nTarefas ja agendadas para hoje ({len(tarefas_do_dia)}):\n"
            for t in tarefas_do_dia:
                contexto += f"  - {t.get('titulo', '')} | {t.get('categoria', '')} | {t.get('horario', 'sem horario')}\n"
            if len(tarefas_do_dia) >= 5:
                contexto += "\n⚠️ O dia ja esta cheio! Considere alertar sobre sobrecarga.\n"

        messages = [{"role": "user", "content": contexto}]
        resposta = self._call_claude(SYSTEM_PROMPT, messages)

        logger.info(f"Claude respondeu: {resposta[:200] if resposta else 'None'}...")
        result = self._parse_json(resposta)

        if not result or "titulo" not in result:
            logger.warning(f"Classificacao falhou, usando fallback. Resposta: {resposta}")
            return {
                "titulo": texto,
                "categoria": "Pessoal",
                "prioridade": "media",
                "prazo": None,
                "horario": None,
                "meeting_link": None,
                "meeting_platform": None,
                "tempo_estimado_min": 30,
                "mensagem": "Nao consegui classificar automaticamente. Em qual categoria voce colocaria? (Trabalho, Consultoria, Grupo Ser, Pessoal)",
                "alerta_sobrecarga": False,
                "alerta_msg": None,
            }

        # Garantir que todos os campos existem
        defaults = {
            "titulo": texto,
            "categoria": "Pessoal",
            "prioridade": "media",
            "prazo": None,
            "horario": None,
            "meeting_link": None,
            "meeting_platform": None,
            "tempo_estimado_min": 30,
            "mensagem": "Confirma essa classificacao?",
            "alerta_sobrecarga": False,
            "alerta_msg": None,
        }
        for k, v in defaults.items():
            if k not in result or result[k] is None and v is not None:
                if k not in result:
                    result[k] = v

        return result

    def processar_confirmacao(self, resposta_usuario: str, tarefa_pendente: dict,
                               historico_conversa: list = None) -> dict:
        """
        Processa a resposta do usuario ao pedido de confirmacao.
        Usa historico completo da conversa para entender o contexto.
        """
        hist_str = ""
        if historico_conversa:
            for msg in historico_conversa:
                papel = "Wendel" if msg.get("role") == "user" else "Assistente"
                hist_str += f"{papel}: {msg.get('content', '')}\n"

        system = SYSTEM_PROMPT + "\n\n" + CONFIRM_PROMPT.format(
            tarefa_json=json.dumps(tarefa_pendente, ensure_ascii=False, indent=2),
            historico=hist_str or "(primeira interacao)",
            resposta=resposta_usuario,
        )

        messages = [{"role": "user", "content": resposta_usuario}]
        resposta = self._call_claude(system, messages)

        logger.info(f"Confirmacao - Claude respondeu: {resposta[:200] if resposta else 'None'}...")
        result = self._parse_json(resposta)

        if not result:
            logger.warning(f"Parse falhou na confirmacao. Resposta: {resposta}")
            # Se nao entendeu, tenta detectar intent manualmente
            lower = resposta_usuario.lower().strip() if resposta_usuario else ""
            if any(w in lower for w in ["sim", "ok", "confirma", "isso", "salva", "pode", "bora", "manda"]):
                return {"acao": "salvar"}
            if any(w in lower for w in ["nao", "cancela", "esquece", "deixa"]):
                return {"acao": "cancelar"}
            # Ultima tentativa: assume que e um ajuste, retorna com as mudancas que conseguir detectar
            return self._tentar_ajuste_manual(resposta_usuario, tarefa_pendente)

        # Se retornou acao, retorna direto
        if "acao" in result:
            return result

        # Se retornou tarefa atualizada, garante campos completos
        for k, v in tarefa_pendente.items():
            if k not in result:
                result[k] = v

        return result

    def _tentar_ajuste_manual(self, texto: str, tarefa: dict) -> dict:
        """Tenta fazer ajuste manual se Claude nao retornou JSON valido."""
        lower = texto.lower().strip()
        updated = dict(tarefa)

        # Detectar mudanca de categoria
        if "trabalho" in lower:
            updated["categoria"] = "Trabalho"
        elif "consultoria" in lower:
            updated["categoria"] = "Consultoria"
        elif "grupo ser" in lower or "ser educacional" in lower:
            updated["categoria"] = "Grupo Ser"
        elif "pessoal" in lower:
            updated["categoria"] = "Pessoal"

        # Detectar mudanca de prioridade
        if "alta" in lower or "urgente" in lower:
            updated["prioridade"] = "alta"
        elif "baixa" in lower:
            updated["prioridade"] = "baixa"
        elif "media" in lower:
            updated["prioridade"] = "media"

        return updated

    def planejar_dia(self, tarefas: list, data: str = None) -> str:
        """Gera planejamento do dia."""
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        tarefas_json = json.dumps(tarefas, ensure_ascii=False, indent=2)
        prompt = PLANNING_PROMPT.format(data=data, tarefas_json=tarefas_json)

        messages = [{"role": "user", "content": prompt}]
        resposta = self._call_claude(SYSTEM_PROMPT, messages, max_tokens=2048)
        return resposta or "Nao consegui gerar o planejamento. Tente novamente."

    def feedback_dia(self, concluidas: list, pendentes: list, data: str = None) -> str:
        """Gera feedback do dia."""
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        prompt = FEEDBACK_PROMPT.format(
            data=data,
            concluidas_json=json.dumps(concluidas, ensure_ascii=False, indent=2),
            pendentes_json=json.dumps(pendentes, ensure_ascii=False, indent=2),
        )

        messages = [{"role": "user", "content": prompt}]
        resposta = self._call_claude(SYSTEM_PROMPT, messages, max_tokens=2048)
        return resposta or "Nao consegui gerar o feedback. Tente novamente."

    def conversar(self, mensagem: str, historico: list) -> str:
        """Conversa livre sobre organizacao/feedback."""
        system = SYSTEM_PROMPT + "\n\n" + CHAT_PROMPT

        messages = []
        for msg in historico[-8:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": mensagem})

        resposta = self._call_claude(system, messages, max_tokens=1024)
        return resposta or "Desculpa, tive um problema. Tenta de novo?"
