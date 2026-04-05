"""
AI Brain v2 — O cerebro inteligente do Organizador de Tarefas
=============================================================
Melhorias v2:
- Resolucao temporal robusta (amanha, sexta, semana que vem, etc.)
- Deteccao de multiplas tarefas em uma mensagem
- Analise real de sobrecarga (baseada em tempo estimado + horarios)
- Sugestao de realocacao inteligente
- Memoria de contexto (pessoas, padroes)
- Analise de padroes de produtividade
- Relatorio semanal inteligente
- Deteccao de delegacao
- Deteccao de recorrencia

Sprint 2 — IA Mais Inteligente:
- Decomposicao de tarefas (decompor_tarefa) — quebra tarefa grande em subtarefas
- Deteccao de conflitos de horario (detectar_conflitos) — avisa se reunioes se sobrepoe
- Alerta preditivo de sobrecarga (alerta_preditivo) — avisa antes de dias lotados
- Sugestao de reagendamento (sugerir_reagendamento) — onde mover tarefas atrasadas
- Planejamento por energia — cognitivas de manha, administrativas de tarde
- Retry com backoff exponencial — tolerancia a falhas da Claude API
- Analise de padroes melhorada — categorias, dias, habitos pessoais
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

# ========== CONSTANTES TEMPORAIS ==========

DIAS_SEMANA_PT = {
    "segunda": 0, "segunda-feira": 0,
    "terca": 1, "terça": 1, "terca-feira": 1, "terça-feira": 1,
    "quarta": 2, "quarta-feira": 2,
    "quinta": 3, "quinta-feira": 3,
    "sexta": 4, "sexta-feira": 4,
    "sabado": 5, "sábado": 5,
    "domingo": 6,
}

# Jornada em minutos (configuravel)
JORNADA_INICIO = 8   # 08:00
JORNADA_FIM = 18     # 18:00
JORNADA_TOTAL_MIN = (JORNADA_FIM - JORNADA_INICIO) * 60  # 600min
BLOCOS_FIXOS_MIN = 75     # almoco 60min + cafe 15min
TEMPO_PESSOAL_MIN = 50    # ingles 30min + leitura 20min
CAPACIDADE_DIA_MIN = JORNADA_TOTAL_MIN - BLOCOS_FIXOS_MIN - TEMPO_PESSOAL_MIN  # 475min

# ========== SYSTEM PROMPT PRINCIPAL ==========

SYSTEM_PROMPT = """Voce e o cerebro de um organizador de tarefas inteligente.
Seu usuario e o Professor Wendel Castro, de Recife-PE.

# QUEM E O WENDEL

Professor de Inteligencia Artificial e Banco de Dados na Ser Educacional.
Tambem faz consultoria em dados para empresas externas.
Tem projetos pessoais (conteudo, estudos, vida pessoal).
Sofre com sobrecarga mental — muitas demandas, sensacao de nao dar conta.
Precisa proteger tempo pessoal: ingles (30min/dia) e leitura (20min/dia).
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

# CONTEXTO APRENDIDO (MEMORIA)
{contexto_memoria}

# PRIORIDADE INTELIGENTE
- Reuniao amanha = ALTA (urgente + importante)
- Reuniao com gestores/coordenacao = ALTA (impacto institucional)
- Aula amanha = ALTA (nao pode falhar)
- Entrega com prazo proximo (1-2 dias) = ALTA
- Tarefa para esta semana = MEDIA
- Tarefa sem prazo definido = MEDIA
- "Quando puder", "sem pressa" = BAIXA
- Comprar algo sem urgencia = BAIXA

# ESTIMATIVA DE TEMPO
Estime o tempo em minutos de forma REALISTA:
- Reuniao padrao: 60min
- Aula: 50min (preparacao extra se necessario)
- Corrigir provas: 90-120min (depende da turma)
- Email/mensagem: 15min
- Tarefa simples: 30min
- Projeto/relatorio: 120-180min
- Revisao de documento: 45min
Sempre erre para MAIS, nunca para menos.

# DETECCAO DE DELEGACAO
Se o texto mencionar outra pessoa como responsavel (ex: "pede pro Joao", "delegar ao Pedro",
"a Maria vai fazer"), detecte e preencha o campo "delegado_para" com o nome da pessoa.

# DETECCAO DE DUPLICATAS (MUITO IMPORTANTE)
Antes de classificar, COMPARE o texto do usuario com as tarefas ja agendadas (listadas no contexto).
Se o usuario esta tentando criar algo que JA EXISTE:
1. Inclua no campo "mensagem": "⚠️ Essa tarefa parece similar a '[titulo existente]' que já está agendada para [data]."
2. Se for EXATAMENTE igual (mesmo titulo e mesmo dia), retorne a tarefa com o campo "_possivel_duplicata": true
3. Se for similar mas com diferenças (horário diferente, dia diferente), classifique normalmente mas avise na mensagem
4. NUNCA crie duplicatas silenciosamente — SEMPRE avise o Wendel

# DETECCAO DE RECORRENCIA
Se o texto indicar repeticao (ex: "toda segunda", "todo dia", "semanalmente",
"uma vez por mes"), detecte e preencha:
- "recorrencia": "diaria" | "semanal" | "quinzenal" | "mensal"
- "recorrencia_dia": numero do dia (0=segunda...6=domingo para semanal, 1-31 para mensal)

# DETECCAO DE MULTIPLAS TAREFAS
Se o texto contem MAIS DE UMA tarefa distinta, retorne um array de tarefas.
Formato para multiplas tarefas:
{
  "multiplas": true,
  "tarefas": [ ... array de objetos tarefa ... ]
}

# FORMATO DE LISTA SEMANAL (MUITO IMPORTANTE)
O Wendel frequentemente envia a semana INTEIRA de uma vez, organizada por dia.
Exemplo:
"Segunda-feira:
Reuniao com Carlos 10h
Corrigir provas
Terca:
Aula de IA 14h
..."

Quando receber esse formato:
1. CADA LINHA e uma tarefa separada (a menos que seja continuacao obvia)
2. O DIA DA SEMANA no cabecalho define o PRAZO de todas as tarefas abaixo ate o proximo dia
3. Resolva cada dia para a data correta (ex: "Segunda-feira" = proxima segunda)
4. Se o usuario ja esta na semana mencionada, use os dias da semana ATUAL
5. Retorne TODAS as tarefas como array (pode ser 10, 20, 30 — nao tem limite)
6. Classifique CADA tarefa individualmente (categoria, prioridade, etc)

# DETECCAO DE STATUS (FEITO / NAO FEITO / EM ANDAMENTO)
O Wendel marca status nas proprias tarefas. Detecte:
- "feito", "feito ja", "ja fiz", "concluido", "pronto" → status: "concluida"
- "em andamento", "fazendo", "comecei", "em progresso" → status: "em_andamento"
- "nao fiz", "nao foi", "pendente", "falta", "nao atendido" → status: "pendente"
- "sera feito amanha", "amanha", "faremos" → status: "pendente" (com prazo ajustado)
Se nao mencionar status, assuma "pendente".
Inclua o campo "status" em cada tarefa do array.

# DETECCAO DE PESSOAS E DELEGACAO
Se o texto menciona nomes de pessoas entre parenteses ou contexto (ex: "Herica", "Ronedo",
"Luciana", "Lorena", "Simone"), detecte:
- Se a pessoa e quem o Wendel VAI encontrar → inclua no titulo
- Se a pessoa e quem o Wendel DELEGOU algo → coloque em "delegado_para"

# FORMATO DE RESPOSTA (TAREFA UNICA)
{
  "titulo": "titulo limpo e claro (reescreva se necessario)",
  "categoria": "Trabalho|Consultoria|Grupo Ser|Pessoal",
  "prioridade": "alta|media|baixa",
  "prazo": "YYYY-MM-DD ou null se nao souber",
  "horario": "HH:MM ou null",
  "meeting_link": "url ou null",
  "meeting_platform": "zoom|meet|teams|null",
  "tempo_estimado_min": 30,
  "delegado_para": "nome ou null",
  "recorrencia": "diaria|semanal|quinzenal|mensal|null",
  "recorrencia_dia": null,
  "mensagem": "pergunta curta de confirmacao pro Wendel",
  "alerta_sobrecarga": false,
  "alerta_msg": null
}

IMPORTANTE:
- Responda APENAS o JSON, sem texto antes ou depois
- O campo "mensagem" deve ser uma frase curta e natural
- Se nao tem certeza da categoria, PERGUNTE na mensagem
- Se nao tem prazo, coloque null e pergunte na mensagem
- Use a data/hora fornecida no contexto para resolver expressoes temporais
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
- Usuario: "coloca 2 horas" → mude tempo_estimado_min para 120, mantenha todo o resto

Responda APENAS com JSON valido, sem texto antes ou depois.
"""

PLANNING_PROMPT = """Planeje o dia do Wendel de forma REALISTA.

Data: {data}
Tarefas pendentes para hoje e atrasadas:
{tarefas_json}

Carga do dia: {carga_info}

Regras:
1. Distribua as tarefas em blocos de tempo realistas
2. Inclua: almoco (12:00-13:00), cafe (15:30-15:45)
3. OBRIGATORIO: ingles 30min e leitura 20min (tempo pessoal protegido)
4. Jornada: 08:00 ate 18:00 (pode flexibilizar ate 19:00 se necessario)
5. Se tem tarefa demais, sugira o que ADIAR para outro dia
6. Margens: adicione 15-20% a mais de tempo em cada tarefa
7. Reunioes com horario fixo nao podem ser movidas, organize o resto ao redor delas
8. Use o tempo_estimado_min de cada tarefa para calcular os blocos
9. Tarefas delegadas: apenas mencione que estao com a pessoa X
10. Tarefas cognitivas pesadas (preparar aula, corrigir provas, projetos) devem ir para a MANHA (8:00-12:00) quando a energia e maior
11. Tarefas administrativas e leves (emails, revisoes, delegacoes) devem ir para a TARDE (14:00-18:00)
12. Apos uma reuniao longa (>60min), sugira 15min de pausa antes da proxima tarefa


{energia_historico}Responda em texto formatado para Telegram (Markdown), NAO em JSON.
Use emojis com moderacao. Seja direto e realista.
Se o dia esta pesado demais, DIGA CLARAMENTE e sugira o que mover.
"""

FEEDBACK_PROMPT = """De o feedback do dia do Wendel.

Data: {data}
Tarefas concluidas hoje:
{concluidas_json}

Tarefas que ficaram pendentes:
{pendentes_json}

Padroes observados esta semana:
{padroes}

Regras:
1. Comece destacando o que foi FEITO (reforco positivo)
2. Mencione o que ficou pendente SEM julgamento
3. Se fez ingles/leitura, elogie
4. Se nao fez, lembre gentilmente
5. Sugira 1-2 ajustes concretos para amanha
6. Se detectou padroes de adiamento, mencione com cuidado
7. Tom: coach motivacional, NAO chefe cobrando
8. Wendel sofre com sobrecarga — alivie, nao pressione

Responda em texto formatado para Telegram (Markdown).
Maximo 15 linhas — conciso e impactante.
"""

REPORT_PROMPT = """Gere o relatorio semanal do Wendel.

Periodo: {periodo}
Total de tarefas na semana: {total}
Concluidas: {concluidas}
Pendentes que sobraram: {pendentes}
Atrasadas: {atrasadas}

Distribuicao por categoria:
{dist_categoria}

Distribuicao por prioridade:
{dist_prioridade}

Padroes detectados:
{padroes}

Tempo pessoal (ingles/leitura):
{tempo_pessoal}

Regras:
1. Comece com uma nota positiva sobre a semana
2. Mostre numeros reais (completou X de Y)
3. Destaque a categoria com mais entregas
4. Destaque a categoria com mais atrasos
5. Analise se o tempo pessoal foi respeitado
6. De 2-3 sugestoes concretas para a proxima semana
7. Tom: review profissional mas amigavel
8. Use emojis com moderacao
9. Formatado para Telegram (Markdown)
10. Maximo 25 linhas
"""

CHAT_PROMPT = """O usuario esta conversando sobre organizacao, feedback ou planejamento.
Voce e o assistente pessoal dele. Conhece a rotina, as categorias, os desafios.
Seja direto, util e mantenha o foco em organizacao/produtividade.
Se ele quiser discutir, discuta. Se quiser ajustar algo, ajuste.
Se pedir pra editar uma tarefa existente, pergunte qual e o que mudar.
Responda em texto formatado para Telegram (Markdown). Seja conciso.
"""

DECOMPOSE_PROMPT = """Voce e um assistente de decomposicao de tarefas.

O usuario tem a seguinte tarefa:
{tarefa_json}

Decomponha esta tarefa em 3 a 6 subtarefas CONCRETAS e acionaveis.

Regras:
1. Cada subtarefa deve ser algo que se possa fazer em uma sessao (15-120min)
2. Seja realista com estimativas de tempo
3. A soma dos tempos das subtarefas deve ser compativel com o tempo estimado da tarefa pai
4. Todas as subtarefas herdam a categoria "{categoria}" da tarefa pai
5. Prioridade de cada subtarefa pode variar (nem tudo e urgente dentro de uma tarefa grande)
6. Titulos claros e curtos — deve dar pra entender o que fazer so de ler

Responda APENAS com um JSON array, sem texto antes ou depois:
[
  {{"titulo": "...", "tempo_estimado_min": 30, "prioridade": "media"}},
  {{"titulo": "...", "tempo_estimado_min": 45, "prioridade": "alta"}},
  ...
]
"""


class AIBrain:
    """Cerebro do organizador — integra com Claude API."""

    def __init__(self, api_key: str, provider: str = "claude"):
        self.api_key = api_key
        self.provider = provider  # "claude" ou "gemini"

        if provider == "claude":
            self.client = httpx.Client(
                base_url="https://api.anthropic.com",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=60,
            )
        else:  # gemini
            self.client = httpx.Client(
                base_url="https://generativelanguage.googleapis.com",
                headers={"content-type": "application/json"},
                timeout=60,
            )

    # ========== INFRA ==========

    def _call_claude(self, system: str, messages: list, max_tokens: int = 4096) -> str:
        """Chama a Claude API com retry e exponential backoff em erros 429/503."""
        max_tentativas = 3
        for tentativa in range(max_tentativas):
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
                if resp.status_code == 200:
                    data = resp.json()
                    return data["content"][0]["text"]

                # Erros retriaveis: 429 (rate limit) e 503 (servico indisponivel)
                if resp.status_code in (429, 503) and tentativa < max_tentativas - 1:
                    espera = 2 ** tentativa  # 1s, 2s, 4s
                    logger.warning(
                        f"Claude API erro {resp.status_code} (tentativa {tentativa + 1}/{max_tentativas}). "
                        f"Aguardando {espera}s antes de tentar novamente..."
                    )
                    time.sleep(espera)
                    continue

                logger.error(f"Claude API erro {resp.status_code}: {resp.text}")
                return None
            except Exception as e:
                if tentativa < max_tentativas - 1:
                    espera = 2 ** tentativa
                    logger.warning(
                        f"Erro ao chamar Claude (tentativa {tentativa + 1}/{max_tentativas}): {e}. "
                        f"Aguardando {espera}s..."
                    )
                    time.sleep(espera)
                    continue
                logger.error(f"Erro ao chamar Claude apos {max_tentativas} tentativas: {e}")
                return None
        return None

    def _call_gemini(self, system: str, messages: list, max_tokens: int = 4096) -> str:
        """Chama a Gemini API com retry e exponential backoff."""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.1,
            },
        }

        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                resp = self.client.post(
                    f"/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}",
                    json=body,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    logger.error(f"Gemini resposta sem candidates: {data}")
                    return None

                if resp.status_code in (429, 503) and tentativa < max_tentativas - 1:
                    espera = 2 ** tentativa
                    logger.warning(
                        f"Gemini API erro {resp.status_code} (tentativa {tentativa + 1}/{max_tentativas}). "
                        f"Aguardando {espera}s..."
                    )
                    time.sleep(espera)
                    continue

                logger.error(f"Gemini API erro {resp.status_code}: {resp.text[:500]}")
                return None
            except Exception as e:
                if tentativa < max_tentativas - 1:
                    espera = 2 ** tentativa
                    logger.warning(
                        f"Erro ao chamar Gemini (tentativa {tentativa + 1}/{max_tentativas}): {e}. "
                        f"Aguardando {espera}s..."
                    )
                    time.sleep(espera)
                    continue
                logger.error(f"Erro ao chamar Gemini apos {max_tentativas} tentativas: {e}")
                return None
        return None

    def _call_llm(self, system: str, messages: list, max_tokens: int = 4096) -> str:
        """Roteador: chama Gemini ou Claude conforme o provider configurado."""
        if self.provider == "gemini":
            return self._call_gemini(system, messages, max_tokens)
        return self._call_llm(system, messages, max_tokens)

    def _parse_json(self, text: str) -> dict:
        """Extrai JSON de uma resposta que pode ter texto ao redor."""
        if not text:
            return None
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
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
            # Tentar array tambem
            if start is None and '[' in text:
                depth = 0
                for i, c in enumerate(text):
                    if c == '[':
                        if depth == 0:
                            start = i
                        depth += 1
                    elif c == ']':
                        depth -= 1
                        if depth == 0 and start is not None:
                            text = text[start:i+1]
                            break
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao parsear JSON: {text[:300]}")
            return None

    # ========== RESOLUCAO TEMPORAL ==========

    def _resolver_data(self, texto: str) -> str:
        """
        Resolve expressoes temporais em datas concretas.
        Retorna YYYY-MM-DD ou None.
        """
        hoje = datetime.now()
        t = texto.lower()

        # "hoje"
        if re.search(r'\bhoje\b', t):
            return hoje.strftime("%Y-%m-%d")

        # "depois de amanha" ANTES de "amanha" (senao "amanha" daria match primeiro)
        if re.search(r'depois\s+de\s+amanh[aã]', t):
            return (hoje + timedelta(days=2)).strftime("%Y-%m-%d")

        # "amanha" / "amanhã"
        if re.search(r'\bamanh[aã]\b', t):
            return (hoje + timedelta(days=1)).strftime("%Y-%m-%d")

        # "daqui a X dias"
        m = re.search(r'daqui\s+(?:a\s+)?(\d+)\s+dias?', t)
        if m:
            return (hoje + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

        # "em X dias"
        m = re.search(r'em\s+(\d+)\s+dias?', t)
        if m:
            return (hoje + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

        # "proxima segunda", "essa sexta", "na quarta", etc.
        for dia_nome, dia_num in DIAS_SEMANA_PT.items():
            pattern = rf'\b{re.escape(dia_nome)}\b'
            if re.search(pattern, t):
                dias_ate = (dia_num - hoje.weekday()) % 7
                # "essa/esta" = esta semana (pode ser hoje)
                if re.search(r'\b(essa|esta|nessa|nesta)\b', t):
                    if dias_ate == 0:
                        return hoje.strftime("%Y-%m-%d")
                else:
                    # Padrao: proximo dia com esse nome
                    if dias_ate == 0:
                        dias_ate = 7
                return (hoje + timedelta(days=dias_ate)).strftime("%Y-%m-%d")

        # "semana que vem" / "proxima semana"
        if re.search(r'semana\s+que\s+vem|pr[oó]xima\s+semana', t):
            dias_ate_segunda = (7 - hoje.weekday()) % 7
            if dias_ate_segunda == 0:
                dias_ate_segunda = 7
            return (hoje + timedelta(days=dias_ate_segunda)).strftime("%Y-%m-%d")

        # "fim do mes" / "final do mes"
        if re.search(r'fi[mn](?:al)?\s+(?:do|de)\s+m[eê]s', t):
            if hoje.month == 12:
                ultimo = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo = datetime(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
            return ultimo.strftime("%Y-%m-%d")

        # "fim da semana" = sexta
        if re.search(r'fi[mn](?:al)?\s+(?:da|de)\s+semana', t):
            dias_ate_sexta = (4 - hoje.weekday()) % 7
            if dias_ate_sexta == 0:
                dias_ate_sexta = 7
            return (hoje + timedelta(days=dias_ate_sexta)).strftime("%Y-%m-%d")

        # Data explicita DD/MM
        m = re.search(r'(?:dia\s+)?(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?', t)
        if m:
            dia = int(m.group(1))
            mes = int(m.group(2))
            ano = int(m.group(3)) if m.group(3) else hoje.year
            if ano < 100:
                ano += 2000
            try:
                data = datetime(ano, mes, dia)
                if data.date() < hoje.date():
                    data = datetime(ano + 1, mes, dia)
                return data.strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None

    def _validar_data_claude(self, texto: str, data_claude: str) -> str:
        """Valida a data do Claude contra resolucao propria. Python ganha em caso de conflito."""
        data_resolvida = self._resolver_data(texto)

        if data_resolvida and data_claude:
            if data_resolvida != data_claude:
                logger.warning(
                    f"Data divergente: Claude={data_claude}, Python={data_resolvida}. "
                    f"Usando Python (mais confiavel para expressoes temporais)."
                )
                return data_resolvida

        if data_resolvida:
            return data_resolvida

        # Validar que Claude nao retornou data no passado
        if data_claude:
            try:
                data_obj = datetime.strptime(data_claude, "%Y-%m-%d")
                if data_obj.date() < datetime.now().date():
                    logger.warning(f"Claude retornou data no passado: {data_claude}")
                    return None
                return data_claude
            except ValueError:
                return None

        return None

    # ========== ANALISE DE SOBRECARGA ==========

    def _analisar_sobrecarga(self, tarefas_dia: list, nova_tarefa: dict) -> dict:
        """Analisa se o dia esta sobrecarregado com base em tempo real."""
        total_ocupado = sum(t.get('tempo_estimado_min') or 30 for t in tarefas_dia)
        novo_tempo = nova_tarefa.get('tempo_estimado_min') or 30
        total_com_novo = total_ocupado + novo_tempo

        reunioes = [t for t in tarefas_dia if t.get('horario')]
        percentual = (total_com_novo / CAPACIDADE_DIA_MIN) * 100 if CAPACIDADE_DIA_MIN > 0 else 100

        result = {
            "sobrecarregado": percentual > 85,
            "percentual": round(percentual),
            "minutos_ocupados": total_com_novo,
            "minutos_disponiveis": CAPACIDADE_DIA_MIN,
            "reunioes_fixas": len(reunioes),
            "tarefas_total": len(tarefas_dia) + 1,
        }

        if percentual > 100:
            result["nivel"] = "critico"
            result["msg"] = (
                f"⚠️ Dia LOTADO ({percentual:.0f}% da capacidade)! "
                f"Ja tem {len(tarefas_dia)} tarefas somando {total_ocupado}min. "
                f"Impossivel fazer tudo com qualidade."
            )
        elif percentual > 85:
            result["nivel"] = "alto"
            result["msg"] = (
                f"⚠️ Dia pesado ({percentual:.0f}%). "
                f"{len(tarefas_dia)} tarefas + esta nova. Risco de nao dar conta."
            )
        elif percentual > 65:
            result["nivel"] = "moderado"
            result["msg"] = f"📊 Dia cheio ({percentual:.0f}%), mas administravel."
        else:
            result["nivel"] = "ok"
            result["msg"] = None

        return result

    def _sugerir_realocacao(self, carga_semana: dict) -> str:
        """
        Sugere o melhor dia para realocar baseado na carga da semana.
        carga_semana: dict de "YYYY-MM-DD" -> {"total_tarefas": N, "minutos_estimados": M}
        """
        hoje = datetime.now()
        melhor_dia = None
        menor_carga = float('inf')

        for i in range(1, 8):
            dia = hoje + timedelta(days=i)
            if dia.weekday() >= 5:  # pular sabado/domingo (configuravel)
                continue
            dia_str = dia.strftime("%Y-%m-%d")
            info = carga_semana.get(dia_str, {"total_tarefas": 0, "minutos_estimados": 0})
            carga = info.get("minutos_estimados", 0)
            if carga < menor_carga:
                menor_carga = carga
                melhor_dia = dia

        if melhor_dia:
            dias_semana = {
                0: "segunda", 1: "terca", 2: "quarta",
                3: "quinta", 4: "sexta", 5: "sabado", 6: "domingo"
            }
            nome = dias_semana.get(melhor_dia.weekday(), "")
            ocupacao = round((menor_carga / CAPACIDADE_DIA_MIN) * 100)
            return (
                f"💡 Sugestao: mover para {nome} ({melhor_dia.strftime('%d/%m')}) "
                f"— so {ocupacao}% ocupado."
            )
        return None

    # ========== DETECCAO DE MULTIPLAS TAREFAS ==========

    def _detectar_separadores(self, texto: str) -> bool:
        """Heuristica rapida para detectar se texto pode ter multiplas tarefas."""
        texto_lower = texto.lower()

        # Formato de lista semanal (dias da semana como cabecalhos)
        dias_encontrados = sum(1 for dia in ['segunda', 'terca', 'terça', 'quarta', 'quinta', 'sexta']
                               if re.search(rf'\b{dia}', texto_lower))
        if dias_encontrados >= 2:
            return True

        # Muitas linhas = provavelmente lista
        linhas = [l.strip() for l in texto.strip().split('\n') if l.strip()]
        if len(linhas) >= 4:
            return True

        indicadores = [
            r'\be\s+(?:tambem|ainda|depois|alem)\b',
            r'\balem\s+disso\b',
            r'\btambem\s+(?:preciso|tenho|quero|devo)\b',
            r'\boutra\s+coisa\b',
            r'\b(?:primeiro|segundo|terceiro|depois|alem)\b.*\b(?:e|tambem)\b',
        ]
        matches = sum(1 for p in indicadores if re.search(p, texto_lower))
        # Se tem multiplos verbos de acao
        acoes = re.findall(r'\b(?:preciso|tenho|quero|devo|fazer|preparar|enviar|corrigir|reuniao|reunir)\b', texto_lower)
        return matches >= 1 or len(acoes) >= 3

    # ========== CONTEXTO / MEMORIA ==========

    def _formatar_contexto_memoria(self, contextos: list) -> str:
        """Formata contextos aprendidos para injecao no prompt."""
        if not contextos:
            return "Nenhum contexto aprendido ainda."
        linhas = []
        for c in contextos:
            if c.get("tipo") == "pessoa":
                linhas.append(f"- Pessoa: {c['chave']} → {c['valor']}")
            elif c.get("tipo") == "padrao":
                linhas.append(f"- Padrao: {c['valor']}")
            elif c.get("tipo") == "preferencia":
                linhas.append(f"- Preferencia: {c['valor']}")
            else:
                linhas.append(f"- {c['valor']}")
        return "\n".join(linhas)

    def extrair_contexto(self, texto: str, classificacao: dict) -> list:
        """
        Extrai entidades/associacoes para salvar na memoria de contexto.
        Ex: "reuniao com Carlos do Grupo Ser" → Carlos = Grupo Ser
        """
        contextos = []
        texto_lower = texto.lower()

        # Detectar nomes de pessoas associados a categorias
        nomes_pattern = re.findall(
            r'(?:com\s+(?:o\s+|a\s+)?|(?:do|da|pro|pra)\s+)([A-Z][a-záéíóúãõê]+)',
            texto
        )
        categoria = classificacao.get("categoria", "")
        for nome in nomes_pattern:
            if nome.lower() not in ["grupo", "ser", "educacional", "zoom", "meet", "teams"]:
                contextos.append({
                    "chave": f"pessoa_{nome.lower()}",
                    "valor": f"{nome} esta associado a categoria '{categoria}'",
                    "tipo": "pessoa",
                })

        # Detectar delegacao
        delegado = classificacao.get("delegado_para")
        if delegado:
            contextos.append({
                "chave": f"pessoa_{delegado.lower()}",
                "valor": f"{delegado} recebe tarefas delegadas (categoria: {categoria})",
                "tipo": "pessoa",
            })

        return contextos

    # ========== FUNCOES PUBLICAS ==========

    def classificar_tarefa(self, texto: str, tarefas_do_dia: list = None,
                           carga_semana: dict = None, contextos: list = None) -> dict:
        """
        Classifica uma tarefa com inteligencia completa:
        - Resolucao temporal
        - Analise de sobrecarga
        - Sugestao de realocacao
        - Deteccao de multiplas tarefas
        - Memoria de contexto
        """
        hoje = datetime.now()
        dias_semana = {
            0: "Segunda-feira", 1: "Terca-feira", 2: "Quarta-feira",
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sabado", 6: "Domingo"
        }
        dia_nome = dias_semana.get(hoje.weekday(), "")

        # Contexto temporal
        contexto = f"Data/hora atual: {hoje.strftime('%Y-%m-%d %H:%M')} ({dia_nome})\n"
        contexto += f"Amanha: {(hoje + timedelta(days=1)).strftime('%Y-%m-%d')}\n"
        for i in range(2, 8):
            d = hoje + timedelta(days=i)
            nome_d = dias_semana.get(d.weekday(), "")
            contexto += f"{nome_d}: {d.strftime('%Y-%m-%d')}\n"

        contexto += f"\nTexto do usuario: \"{texto}\"\n"

        # Tarefas do dia para contexto
        if tarefas_do_dia:
            total_min = sum(t.get('tempo_estimado_min') or 30 for t in tarefas_do_dia)
            contexto += f"\nTarefas ja agendadas para hoje ({len(tarefas_do_dia)}, ~{total_min}min):\n"
            for t in tarefas_do_dia:
                tempo = t.get('tempo_estimado_min') or 30
                contexto += f"  - {t.get('titulo', '')} | {t.get('categoria', '')} | {t.get('horario', 'sem horario')} | ~{tempo}min\n"
            if total_min > CAPACIDADE_DIA_MIN * 0.85:
                contexto += f"\n⚠️ O dia ja esta {round(total_min/CAPACIDADE_DIA_MIN*100)}% ocupado! Considere alertar sobre sobrecarga.\n"

        # Montar system prompt com memoria
        memoria_str = self._formatar_contexto_memoria(contextos or [])
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", memoria_str)

        # Verificar se pode ter multiplas tarefas
        pode_ser_multiplas = self._detectar_separadores(texto)
        if pode_ser_multiplas:
            contexto += "\n⚠️ Este texto contem MULTIPLAS tarefas (possivelmente organizadas por dia da semana). "
            contexto += "Retorne TODAS como array JSON. NAO ignore nenhuma linha.\n"
            contexto += "Use o formato: {\"multiplas\": true, \"tarefas\": [...]}\n"

        messages = [{"role": "user", "content": contexto}]
        # Mais tokens para listas grandes
        tokens = 8192 if pode_ser_multiplas else 4096
        resposta = self._call_llm(system, messages, max_tokens=tokens)

        logger.info(f"IA ({self.provider}) respondeu: {resposta[:300] if resposta else 'NONE — chamada falhou!'}")
        result = self._parse_json(resposta)

        # Tratar multiplas tarefas
        # IMPORTANTE: passar titulo individual (nao texto completo) para pos-processamento
        # para evitar que _resolver_data sobrescreva datas corretas da IA
        if isinstance(result, dict) and result.get("multiplas") and result.get("tarefas"):
            tarefas_multiplas = []
            for t in result["tarefas"]:
                t = self._pos_processar_tarefa(t, t.get("titulo", ""), tarefas_do_dia, carga_semana)
                tarefas_multiplas.append(t)
            return {"multiplas": True, "tarefas": tarefas_multiplas}

        if isinstance(result, list):
            tarefas_multiplas = []
            for t in result:
                if isinstance(t, dict) and "titulo" in t:
                    t = self._pos_processar_tarefa(t, t.get("titulo", ""), tarefas_do_dia, carga_semana)
                    tarefas_multiplas.append(t)
            if tarefas_multiplas:
                return {"multiplas": True, "tarefas": tarefas_multiplas}

        if not result or not isinstance(result, dict) or "titulo" not in result:
            logger.warning(f"Classificacao falhou, usando fallback. Resposta: {resposta}")
            return self._fallback_classificacao(texto)

        return self._pos_processar_tarefa(result, texto, tarefas_do_dia, carga_semana)

    def _pos_processar_tarefa(self, result: dict, texto: str,
                               tarefas_do_dia: list = None,
                               carga_semana: dict = None) -> dict:
        """Pos-processamento: validacao de data, sobrecarga, defaults."""
        # Garantir defaults
        defaults = {
            "titulo": texto[:100],
            "categoria": "Pessoal",
            "prioridade": "media",
            "status": "pendente",
            "prazo": None,
            "horario": None,
            "meeting_link": None,
            "meeting_platform": None,
            "tempo_estimado_min": 30,
            "delegado_para": None,
            "recorrencia": None,
            "recorrencia_dia": None,
            "mensagem": "Confirma essa classificacao?",
            "alerta_sobrecarga": False,
            "alerta_msg": None,
        }
        for k, v in defaults.items():
            if k not in result:
                result[k] = v

        # Validar/corrigir data
        if result.get("prazo"):
            result["prazo"] = self._validar_data_claude(texto, result["prazo"])
        else:
            data_resolvida = self._resolver_data(texto)
            if data_resolvida:
                result["prazo"] = data_resolvida

        # Analise de sobrecarga
        if result.get("prazo") and tarefas_do_dia:
            hoje_str = datetime.now().strftime("%Y-%m-%d")
            # So analisa se a tarefa e para hoje
            if result["prazo"] == hoje_str:
                sobrecarga = self._analisar_sobrecarga(tarefas_do_dia, result)
                if sobrecarga["sobrecarregado"]:
                    result["alerta_sobrecarga"] = True
                    result["alerta_msg"] = sobrecarga["msg"]
                    if carga_semana:
                        sugestao = self._sugerir_realocacao(carga_semana)
                        if sugestao:
                            result["alerta_msg"] += f"\n{sugestao}"

        return result

    def _classificar_linha(self, linha: str, prazo_atual: str = None) -> dict:
        """Classifica uma unica linha de tarefa por keywords."""
        linha_lower = linha.lower().strip()
        if not linha_lower or len(linha_lower) < 3:
            return None

        categoria = "Pessoal"
        if any(w in linha_lower for w in ["grupo ser", "ser educacional", "coordenacao", "pedagogico",
                                           "carlos", "nde", "colegiado", "comite", "institucional"]):
            categoria = "Grupo Ser"
        elif any(w in linha_lower for w in ["consultoria", "cliente", "pipeline", "dados para empresa",
                                             "proposta comercial", "relatorio para empresa"]):
            categoria = "Consultoria"
        elif any(w in linha_lower for w in ["aula", "prova", "aluno", "tcc", "corrigir", "nota",
                                             "disciplina", "slide", "videoaula", "plano de ensino",
                                             "turma", "dpt", "simulado", "oab", "report", "relatorio",
                                             "reuniao", "reunia", "feedback"]):
            categoria = "Trabalho"

        prioridade = "media"
        if any(w in linha_lower for w in ["urgente", "agora", "critico"]):
            prioridade = "alta"

        # Horario
        horario = None
        time_match = re.search(r'(\d{1,2})[h:](\d{2})', linha_lower)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                horario = f"{h:02d}:{m:02d}"
                prioridade = "alta"  # tarefa com horario fixo = alta
        elif re.search(r'(\d{1,2})\s*(?:h(?:oras?)?)\b', linha_lower):
            hm = re.search(r'(\d{1,2})\s*(?:h(?:oras?)?)\b', linha_lower)
            h = int(hm.group(1))
            if 0 <= h <= 23:
                horario = f"{h:02d}:00"
                prioridade = "alta"

        # Status
        status = "pendente"
        if any(w in linha_lower for w in ["feito", "ja fiz", "concluido", "pronto"]):
            status = "concluida"
        elif any(w in linha_lower for w in ["em andamento", "fazendo", "comecei"]):
            status = "em_andamento"

        # Meeting link
        meeting_link = None
        url_match = re.search(r'(https?://\S+)', linha)
        if url_match:
            url = url_match.group(1)
            if any(p in url for p in ["zoom", "meet.google", "teams"]):
                meeting_link = url

        # Limpar titulo (remover horarios e status markers do titulo)
        titulo = linha.strip()
        titulo = re.sub(r'\b\d{1,2}[h:]\d{2}\s*(?:horas?)?\b', '', titulo)
        titulo = re.sub(r'\b\d{1,2}\s*(?:h(?:oras?)?)\b', '', titulo)
        titulo = re.sub(r'\bhoras?\b', '', titulo, flags=re.IGNORECASE)
        titulo = re.sub(r'\b(?:feito\s*j[aá]?|j[aá]\s*fiz|conclu[ií]do|pronto)\b', '', titulo, flags=re.IGNORECASE)
        titulo = re.sub(r'\s{2,}', ' ', titulo).strip(' -:,.')
        if not titulo:
            titulo = linha.strip()[:100]

        return {
            "titulo": titulo[:100],
            "categoria": categoria,
            "prioridade": prioridade,
            "status": status,
            "prazo": prazo_atual,
            "horario": horario,
            "meeting_link": meeting_link,
            "meeting_platform": None,
            "tempo_estimado_min": 60 if horario else 30,
            "delegado_para": None,
            "recorrencia": None,
            "recorrencia_dia": None,
            "mensagem": "Classificado por keywords (IA indisponivel). Confirma ou ajusta.",
            "alerta_sobrecarga": False,
            "alerta_msg": None,
        }

    def _fallback_classificacao(self, texto: str):
        """Fallback quando IA falha — classificacao por keywords com suporte a listas."""
        # Detectar se e lista semanal (multiplas tarefas)
        if self._detectar_separadores(texto):
            return self._fallback_multiplas(texto)

        # Tarefa unica
        result = self._classificar_linha(texto, self._resolver_data(texto))
        if result:
            result["mensagem"] = "Nao consegui classificar com IA. Confirma ou ajusta."
            return result

        return {
            "titulo": texto[:100],
            "categoria": "Pessoal",
            "prioridade": "media",
            "status": "pendente",
            "prazo": None,
            "horario": None,
            "meeting_link": None,
            "meeting_platform": None,
            "tempo_estimado_min": 30,
            "delegado_para": None,
            "recorrencia": None,
            "recorrencia_dia": None,
            "mensagem": "Nao consegui classificar com IA. Confirma ou ajusta.",
            "alerta_sobrecarga": False,
            "alerta_msg": None,
        }

    def _fallback_multiplas(self, texto: str) -> dict:
        """Fallback para listas semanais — separa por dia da semana."""
        hoje = datetime.now()
        linhas = texto.strip().split('\n')
        tarefas = []
        prazo_atual = None

        for linha in linhas:
            linha_strip = linha.strip()
            if not linha_strip:
                continue

            # Detectar cabecalho de dia da semana
            linha_lower = linha_strip.lower().rstrip(':. ')
            dia_encontrado = False
            for nome_dia, num_dia in DIAS_SEMANA_PT.items():
                if linha_lower == nome_dia or linha_lower.startswith(nome_dia + ':') or \
                   linha_lower.startswith(nome_dia + ' ') or linha_lower.endswith(nome_dia):
                    # Resolver data para esse dia da semana
                    dias_ate = (num_dia - hoje.weekday()) % 7
                    if dias_ate == 0 and hoje.hour >= 18:
                        dias_ate = 7
                    prazo_atual = (hoje + timedelta(days=dias_ate)).strftime("%Y-%m-%d")
                    dia_encontrado = True
                    break

            if dia_encontrado:
                # Se a linha tem mais que so o dia (ex: "Sexta: reuniao 9h")
                resto = re.sub(r'^(?:segunda|terca|terça|quarta|quinta|sexta|sabado|domingo)(?:-feira)?[:\s]*',
                               '', linha_strip, flags=re.IGNORECASE).strip()
                if resto and len(resto) > 3:
                    t = self._classificar_linha(resto, prazo_atual)
                    if t:
                        tarefas.append(t)
                continue

            # Linha normal = tarefa
            if len(linha_strip) > 3:
                t = self._classificar_linha(linha_strip, prazo_atual)
                if t:
                    tarefas.append(t)

        if tarefas:
            logger.info(f"Fallback detectou {len(tarefas)} tarefas por keywords")
            return {"multiplas": True, "tarefas": tarefas}

        # Se nao conseguiu separar, retorna como unica
        return self._classificar_linha(texto, self._resolver_data(texto))

    def processar_confirmacao(self, resposta_usuario: str, tarefa_pendente: dict,
                               historico_conversa: list = None) -> dict:
        """Processa resposta de confirmacao/ajuste com historico."""
        hist_str = ""
        if historico_conversa:
            for msg in historico_conversa:
                papel = "Wendel" if msg.get("role") == "user" else "Assistente"
                hist_str += f"{papel}: {msg.get('content', '')}\n"

        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "") + "\n\n" + CONFIRM_PROMPT.format(
            tarefa_json=json.dumps(tarefa_pendente, ensure_ascii=False, indent=2),
            historico=hist_str or "(primeira interacao)",
            resposta=resposta_usuario,
        )

        # Adicionar contexto temporal
        hoje = datetime.now()
        temporal = f"\nData atual: {hoje.strftime('%Y-%m-%d')}, Amanha: {(hoje + timedelta(days=1)).strftime('%Y-%m-%d')}\n"
        system += temporal

        messages = [{"role": "user", "content": resposta_usuario}]
        resposta = self._call_llm(system, messages)

        logger.info(f"Confirmacao - Claude respondeu: {resposta[:200] if resposta else 'None'}")
        result = self._parse_json(resposta)

        if not result:
            logger.warning(f"Parse falhou na confirmacao. Resposta: {resposta}")
            lower = resposta_usuario.lower().strip() if resposta_usuario else ""
            if any(w in lower for w in ["sim", "ok", "confirma", "isso", "salva", "pode", "bora", "manda"]):
                return {"acao": "salvar"}
            if any(w in lower for w in ["nao", "cancela", "esquece", "deixa"]):
                return {"acao": "cancelar"}
            return self._tentar_ajuste_manual(resposta_usuario, tarefa_pendente)

        if "acao" in result:
            return result

        # Tarefa atualizada — validar data
        if "prazo" in result and result["prazo"]:
            result["prazo"] = self._validar_data_claude(resposta_usuario, result["prazo"])

        for k, v in tarefa_pendente.items():
            if k not in result:
                result[k] = v

        return result

    def _tentar_ajuste_manual(self, texto: str, tarefa: dict) -> dict:
        """Fallback: ajuste manual se Claude nao retornou JSON valido."""
        lower = texto.lower().strip()
        updated = dict(tarefa)

        if "trabalho" in lower:
            updated["categoria"] = "Trabalho"
        elif "consultoria" in lower:
            updated["categoria"] = "Consultoria"
        elif "grupo ser" in lower or "ser educacional" in lower:
            updated["categoria"] = "Grupo Ser"
        elif "pessoal" in lower:
            updated["categoria"] = "Pessoal"

        if "alta" in lower or "urgente" in lower:
            updated["prioridade"] = "alta"
        elif "baixa" in lower:
            updated["prioridade"] = "baixa"
        elif "media" in lower:
            updated["prioridade"] = "media"

        data = self._resolver_data(texto)
        if data:
            updated["prazo"] = data

        time_match = re.search(r'(\d{1,2})[h:](\d{2})', lower)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                updated["horario"] = f"{h:02d}:{m:02d}"

        return updated

    # ========== PLANEJAR DIA ==========

    def planejar_dia(self, tarefas: list, data: str = None, energia_info: str = "") -> str:
        """Gera planejamento inteligente do dia."""
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        total_min = sum(t.get('tempo_estimado_min') or 30 for t in tarefas)
        reunioes = sum(1 for t in tarefas if t.get('horario'))
        ocupacao = round((total_min / CAPACIDADE_DIA_MIN) * 100)

        carga_info = (
            f"{len(tarefas)} tarefas, ~{total_min}min estimados, "
            f"{reunioes} reunioes fixas, {ocupacao}% da capacidade "
            f"(limite: {CAPACIDADE_DIA_MIN}min uteis)"
        )

        # Montar bloco de energia se disponivel
        if energia_info:
            energia_historico = (
                f"HISTORICO DE ENERGIA DO USUARIO (ultimos dias):\n"
                f"{energia_info}\n"
                f"Use esses dados para sugerir tarefas pesadas nos periodos de alta energia "
                f"e tarefas leves nos periodos de baixa energia.\n\n"
            )
        else:
            energia_historico = ""

        tarefas_json = json.dumps(tarefas, ensure_ascii=False, indent=2)
        prompt = PLANNING_PROMPT.format(
            data=data, tarefas_json=tarefas_json, carga_info=carga_info,
            energia_historico=energia_historico,
        )

        messages = [{"role": "user", "content": prompt}]
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "")
        resposta = self._call_llm(system, messages, max_tokens=2048)
        return resposta or "Nao consegui gerar o planejamento. Tente novamente."

    # ========== FEEDBACK DO DIA ==========

    def feedback_dia(self, concluidas: list, pendentes: list,
                     padroes: str = "", data: str = None) -> str:
        """Gera feedback construtivo do dia."""
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")

        prompt = FEEDBACK_PROMPT.format(
            data=data,
            concluidas_json=json.dumps(concluidas, ensure_ascii=False, indent=2),
            pendentes_json=json.dumps(pendentes, ensure_ascii=False, indent=2),
            padroes=padroes or "Nenhum padrao significativo detectado ainda.",
        )

        messages = [{"role": "user", "content": prompt}]
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "")
        resposta = self._call_llm(system, messages, max_tokens=2048)
        return resposta or "Nao consegui gerar o feedback. Tente novamente."

    # ========== RELATORIO SEMANAL ==========

    def gerar_relatorio_semanal(self, dados: dict) -> str:
        """Gera relatorio semanal completo."""
        prompt = REPORT_PROMPT.format(
            periodo=dados.get("periodo", "esta semana"),
            total=dados.get("total", 0),
            concluidas=dados.get("concluidas", 0),
            pendentes=dados.get("pendentes", 0),
            atrasadas=dados.get("atrasadas", 0),
            dist_categoria=dados.get("dist_categoria", "Sem dados"),
            dist_prioridade=dados.get("dist_prioridade", "Sem dados"),
            padroes=dados.get("padroes", "Sem padroes detectados"),
            tempo_pessoal=dados.get("tempo_pessoal", "Sem dados"),
        )

        messages = [{"role": "user", "content": prompt}]
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "")
        resposta = self._call_llm(system, messages, max_tokens=2048)
        return resposta or "Nao consegui gerar o relatorio. Tente novamente."

    # ========== CONVERSA LIVRE ==========

    def conversar(self, mensagem: str, historico: list) -> str:
        """Conversa livre sobre organizacao/feedback."""
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "") + "\n\n" + CHAT_PROMPT

        messages = []
        for msg in historico[-10:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": mensagem})

        resposta = self._call_llm(system, messages, max_tokens=1024)
        return resposta or "Desculpa, tive um problema. Tenta de novo?"

    # ========== DECOMPOSICAO DE TAREFAS ==========

    def decompor_tarefa(self, tarefa: dict) -> list:
        """Decomponhe uma tarefa grande em 3-6 subtarefas concretas via Claude."""
        categoria = tarefa.get("categoria", "Pessoal")
        tarefa_json = json.dumps(tarefa, ensure_ascii=False, indent=2)

        prompt = DECOMPOSE_PROMPT.format(
            tarefa_json=tarefa_json,
            categoria=categoria,
        )

        messages = [{"role": "user", "content": prompt}]
        system = SYSTEM_PROMPT.replace("{contexto_memoria}", "")
        resposta = self._call_llm(system, messages, max_tokens=1024)

        result = self._parse_json(resposta)

        if not result or not isinstance(result, list):
            logger.warning(f"Decomposicao falhou. Resposta: {resposta}")
            return []

        # Herdar categoria da tarefa pai e garantir campos
        subtarefas = []
        for sub in result:
            if not isinstance(sub, dict) or "titulo" not in sub:
                continue
            sub["categoria"] = categoria
            sub.setdefault("tempo_estimado_min", 30)
            sub.setdefault("prioridade", "media")
            subtarefas.append(sub)

        return subtarefas

    # ========== DETECCAO DE CONFLITOS ==========

    def detectar_conflitos(self, tarefas_dia: list, nova_tarefa: dict) -> str:
        """
        Detecta conflitos de horario entre a nova tarefa e as existentes no dia.
        Retorna mensagem de aviso se houver conflito, ou None se nao houver.
        """
        novo_horario = nova_tarefa.get("horario")
        if not novo_horario:
            return None

        try:
            novo_h, novo_m = map(int, novo_horario.split(":"))
            novo_inicio = novo_h * 60 + novo_m
            novo_tempo = nova_tarefa.get("tempo_estimado_min") or 30
            novo_fim = novo_inicio + novo_tempo
        except (ValueError, AttributeError):
            return None

        for tarefa in tarefas_dia:
            horario_existente = tarefa.get("horario")
            if not horario_existente:
                continue

            try:
                ex_h, ex_m = map(int, horario_existente.split(":"))
                ex_inicio = ex_h * 60 + ex_m
                ex_tempo = tarefa.get("tempo_estimado_min") or 30
                ex_fim = ex_inicio + ex_tempo
            except (ValueError, AttributeError):
                continue

            # Verifica sobreposicao: novo comeca antes do existente terminar
            # E novo termina depois do existente comecar
            if novo_inicio < ex_fim and novo_fim > ex_inicio:
                titulo_existente = tarefa.get("titulo", "tarefa existente")
                horario_fim_str = f"{ex_fim // 60:02d}:{ex_fim % 60:02d}"
                return (
                    f"⚠️ Conflito: '{titulo_existente}' ja esta marcada as "
                    f"{horario_existente} (ate ~{horario_fim_str}). Ajuste o horario."
                )

        return None

    # ========== SUGESTAO DE REAGENDAMENTO ==========

    def sugerir_reagendamento(self, tarefas_atrasadas: list, carga_semana: dict) -> str:
        """
        Sugere realocacao de tarefas atrasadas para os dias mais leves da semana.
        Retorna mensagem formatada com sugestoes.
        """
        if not tarefas_atrasadas:
            return None

        hoje = datetime.now()
        dias_semana_nomes = {
            0: "segunda", 1: "terca", 2: "quarta",
            3: "quinta", 4: "sexta", 5: "sabado", 6: "domingo"
        }

        # Calcular ocupacao de cada dia nos proximos 7 dias uteis
        dias_disponiveis = []
        for i in range(1, 11):
            dia = hoje + timedelta(days=i)
            if dia.weekday() >= 5:  # pular fim de semana
                continue
            dia_str = dia.strftime("%Y-%m-%d")
            info = carga_semana.get(dia_str, {"minutos_estimados": 0})
            minutos = info.get("minutos_estimados", 0)
            ocupacao = round((minutos / CAPACIDADE_DIA_MIN) * 100) if CAPACIDADE_DIA_MIN > 0 else 100
            dias_disponiveis.append({
                "data": dia_str,
                "nome": dias_semana_nomes.get(dia.weekday(), ""),
                "ocupacao": ocupacao,
                "minutos": minutos,
            })
            if len(dias_disponiveis) >= 7:
                break

        # Ordenar por ocupacao (mais leve primeiro)
        dias_disponiveis.sort(key=lambda d: d["ocupacao"])

        linhas = ["📋 Tarefas atrasadas para realocar:"]
        for i, tarefa in enumerate(tarefas_atrasadas):
            if i < len(dias_disponiveis):
                dia_sugerido = dias_disponiveis[i]
                titulo = tarefa.get("titulo", "Sem titulo")
                linhas.append(
                    f"{i + 1}. '{titulo}' → {dia_sugerido['nome']} ({dia_sugerido['ocupacao']}% ocupado)"
                )
            else:
                titulo = tarefa.get("titulo", "Sem titulo")
                linhas.append(f"{i + 1}. '{titulo}' → sem dia leve disponivel na proxima semana")

        return "\n".join(linhas)

    # ========== ALERTA PREDITIVO ==========

    def alerta_preditivo(self, carga_semana: dict) -> str:
        """
        Verifica os proximos 3 dias e alerta se algum exceder 85% da capacidade.
        Retorna mensagem de alerta ou None se tudo estiver ok.
        """
        hoje = datetime.now()
        dias_semana_nomes = {
            0: "segunda", 1: "terca", 2: "quarta",
            3: "quinta", 4: "sexta", 5: "sabado", 6: "domingo"
        }

        alertas = []
        dia_mais_leve = None
        menor_ocupacao = float('inf')

        for i in range(1, 8):
            dia = hoje + timedelta(days=i)
            if dia.weekday() >= 5:
                continue
            dia_str = dia.strftime("%Y-%m-%d")
            info = carga_semana.get(dia_str, {"minutos_estimados": 0})
            minutos = info.get("minutos_estimados", 0)
            ocupacao = round((minutos / CAPACIDADE_DIA_MIN) * 100) if CAPACIDADE_DIA_MIN > 0 else 0

            if ocupacao < menor_ocupacao:
                menor_ocupacao = ocupacao
                dia_mais_leve = {
                    "nome": dias_semana_nomes.get(dia.weekday(), ""),
                    "ocupacao": ocupacao,
                }

            # Apenas os proximos 3 dias uteis para alerta
            if len(alertas) < 3 or i <= 3:
                if ocupacao > 85 and i <= 4:  # proximos 3 dias uteis
                    nome_dia = dias_semana_nomes.get(dia.weekday(), "")
                    # Determinar se e amanha, depois de amanha, etc.
                    if i == 1:
                        label = f"amanha ({nome_dia})"
                    elif i == 2:
                        label = f"depois de amanha ({nome_dia})"
                    else:
                        label = nome_dia
                    alertas.append({"label": label, "ocupacao": ocupacao})

        if not alertas:
            return None

        # Montar mensagem com sugestao do dia mais leve
        partes = []
        for a in alertas:
            partes.append(f"{a['label']} ja tem {a['ocupacao']}% da capacidade ocupada")

        msg = "🔮 Alerta: " + "; ".join(partes) + "."
        if dia_mais_leve and dia_mais_leve["ocupacao"] < 70:
            msg += f" Considere mover algo para {dia_mais_leve['nome']} ({dia_mais_leve['ocupacao']}%)."

        return msg

    # ========== ANALISE DE PADROES ==========

    def analisar_padroes(self, historico: list, tarefas_recentes: list) -> str:
        """Analisa padroes de comportamento para feedback e relatorios."""
        if not historico and not tarefas_recentes:
            return "Sem dados suficientes para analise."

        padroes = []

        # Analisar categorias com mais atrasos
        atrasadas_por_cat = {}
        for t in tarefas_recentes:
            if t.get("status") != "concluida" and t.get("prazo"):
                try:
                    prazo = datetime.strptime(t["prazo"], "%Y-%m-%d")
                    if prazo.date() < datetime.now().date():
                        cat = t.get("categoria", "Sem categoria")
                        atrasadas_por_cat[cat] = atrasadas_por_cat.get(cat, 0) + 1
                except (ValueError, TypeError):
                    pass

        if atrasadas_por_cat:
            pior_cat = max(atrasadas_por_cat, key=atrasadas_por_cat.get)
            padroes.append(
                f"Categoria com mais atrasos: {pior_cat} ({atrasadas_por_cat[pior_cat]} tarefas)"
            )

        # Analisar dia da semana com mais tarefas incompletas
        incompletas_por_dia = {}
        for t in tarefas_recentes:
            if t.get("status") != "concluida" and t.get("prazo"):
                try:
                    prazo = datetime.strptime(t["prazo"], "%Y-%m-%d")
                    dia_semana = prazo.weekday()
                    dias_nomes = {
                        0: "segunda", 1: "terca", 2: "quarta",
                        3: "quinta", 4: "sexta", 5: "sabado", 6: "domingo"
                    }
                    nome_dia = dias_nomes.get(dia_semana, str(dia_semana))
                    incompletas_por_dia[nome_dia] = incompletas_por_dia.get(nome_dia, 0) + 1
                except (ValueError, TypeError):
                    pass

        if incompletas_por_dia:
            pior_dia = max(incompletas_por_dia, key=incompletas_por_dia.get)
            padroes.append(
                f"Dia com mais tarefas incompletas: {pior_dia} ({incompletas_por_dia[pior_dia]} tarefas)"
            )

        # Analisar se estimativas de tempo estao consistentemente erradas
        tarefas_com_tempo = [
            t for t in tarefas_recentes
            if t.get("status") == "concluida"
            and t.get("tempo_estimado_min")
            and t.get("tempo_real_min")
        ]
        if tarefas_com_tempo:
            total_estimado = sum(t["tempo_estimado_min"] for t in tarefas_com_tempo)
            total_real = sum(t["tempo_real_min"] for t in tarefas_com_tempo)
            if total_real > 0 and total_estimado > 0:
                razao = total_real / total_estimado
                if razao > 1.3:
                    padroes.append(
                        f"Estimativas de tempo otimistas: tarefas levam em media "
                        f"{round((razao - 1) * 100)}% mais tempo que o estimado. "
                        f"Considere adicionar margens maiores."
                    )
                elif razao < 0.7:
                    padroes.append(
                        f"Estimativas de tempo pessimistas: tarefas levam em media "
                        f"{round((1 - razao) * 100)}% menos tempo que o estimado. "
                        f"Pode encaixar mais coisas no dia."
                    )

        # Analisar categoria negligenciada (menos tarefas concluidas proporcionalmente)
        concluidas_por_cat = {}
        total_por_cat = {}
        for t in tarefas_recentes:
            cat = t.get("categoria", "Sem categoria")
            total_por_cat[cat] = total_por_cat.get(cat, 0) + 1
            if t.get("status") == "concluida":
                concluidas_por_cat[cat] = concluidas_por_cat.get(cat, 0) + 1

        for cat, total in total_por_cat.items():
            if total >= 3:  # so analisa se tem amostra significativa
                concluidas = concluidas_por_cat.get(cat, 0)
                taxa = concluidas / total
                if taxa < 0.4:
                    padroes.append(
                        f"Categoria '{cat}' pode estar sendo negligenciada: "
                        f"apenas {round(taxa * 100)}% das tarefas concluidas ({concluidas}/{total})"
                    )

        # Analisar tempo pessoal (ingles, leitura, academia)
        tarefas_pessoais_concluidas = [
            t for t in tarefas_recentes
            if t.get("categoria") == "Pessoal"
            and t.get("status") == "concluida"
            and any(w in (t.get("titulo", "").lower()) for w in ["ingles", "leitura", "academia"])
        ]

        # Verificar cada habito separadamente
        habitos = {"ingles": 0, "leitura": 0, "academia": 0}
        for t in tarefas_pessoais_concluidas:
            titulo = t.get("titulo", "").lower()
            for habito in habitos:
                if habito in titulo:
                    habitos[habito] += 1

        habitos_fracos = [h for h, count in habitos.items() if count < 2]
        if habitos_fracos:
            padroes.append(
                f"Habitos pessoais com pouca frequencia: {', '.join(habitos_fracos)}. "
                f"Tente manter a consistencia."
            )
        elif len(tarefas_pessoais_concluidas) < 3:
            padroes.append("Tempo pessoal (ingles/leitura/academia) pode estar sendo negligenciado")

        return "\n".join(padroes) if padroes else "Sem padroes significativos."

    # ========== COACHING IA ==========

    def gerar_coaching(self, tarefas: list, historico: str = "") -> str:
        """
        Analisa padroes das tarefas e gera uma dica personalizada (max 2 frases).
        Chamado pelo comando /coaching no Telegram.
        """
        tarefas_json = json.dumps(tarefas[:30], ensure_ascii=False, default=str)

        system = """Voce e um coach de produtividade pessoal do Professor Wendel Castro.
Analise as tarefas dele e de UMA dica curta, personalizada e acionavel (maximo 2 frases).
Foque em padroes reais que voce observa nos dados: sobrecarga, falta de tempo pessoal,
tarefas atrasadas, concentracao excessiva em uma categoria, etc.
Tom: amigavel, direto, motivacional. Nunca generico.
Responda APENAS com a dica em texto puro, sem formatacao markdown."""

        historico_ctx = f"\nHistorico recente:\n{historico}" if historico else ""

        messages = [
            {"role": "user", "content": f"Tarefas atuais:\n{tarefas_json}{historico_ctx}\n\nDe uma dica personalizada de produtividade."}
        ]

        result = self._call_llm(system, messages, max_tokens=200)
        return result.strip() if result else "Continue focando nas prioridades do dia. Voce esta no caminho certo!"

    # ========== TRIAGEM: TAREFA vs FINANÇA ==========

    def detectar_intencao(self, texto: str) -> str:
        """
        Detecta se o texto do usuário é uma TAREFA ou uma TRANSAÇÃO FINANCEIRA.
        Camada 1: palavras-chave (instantâneo, sem API).
        Camada 2: IA (só para casos ambíguos).
        Retorna: 'tarefa' ou 'financa'
        """
        lower = texto.lower()

        # Camada 1: detecção local por palavras-chave financeiras
        palavras_financa = [
            "gastei", "gasto", "paguei", "pagamento", "comprei", "compra",
            "receita", "recebi", "salario", "salário", "ganhei",
            "financ", "finanças", "financas", "dinheiro",
            "conta de", "conta do", "assinatura", "mensalidade",
            "investimento", "investir", "dividendo",
            "divida", "dívida", "parcela", "fatura",
            "reais", "r$", "saldo", "extrato",
            "renda", "lucro", "prejuízo", "prejuizo",
            "orçamento", "orcamento",
            "receita líquida", "receita liquida",
            "guarde nas", "registrar gasto", "registrar receita",
        ]

        # Verificar se tem valor monetário no texto (ex: 50, 8000, 26.977,00)
        import re
        tem_valor = bool(re.search(r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\b', lower))
        tem_palavra_financa = any(p in lower for p in palavras_financa)

        if tem_palavra_financa and tem_valor:
            return "financa"
        if tem_palavra_financa:
            # Palavras fortes que sozinhas indicam finança
            palavras_fortes = ["gastei", "paguei", "recebi", "ganhei", "comprei",
                               "receita", "salario", "salário", "financ", "finanças",
                               "financas", "guarde nas", "receita líquida", "receita liquida"]
            if any(p in lower for p in palavras_fortes):
                return "financa"

        # Camada 2: IA para casos ambíguos (só se tem valor mas sem palavra-chave clara)
        if tem_valor and not tem_palavra_financa:
            system = """Classifique a mensagem como "tarefa" ou "financa".
- tarefa = algo para FAZER (atividade, compromisso, lembrete)
- financa = sobre DINHEIRO (gasto, receita, pagamento, compra)
Responda APENAS: tarefa ou financa"""

            messages = [{"role": "user", "content": texto}]
            result = self._call_llm(system, messages, max_tokens=100)
            if result:
                clean = result.strip().lower().replace("ç", "c")
                if "financa" in clean:
                    return "financa"

        return "tarefa"

    # ========== MODULO FINANCEIRO ==========

    def classificar_transacao(self, texto: str, categorias_disponiveis: list = None) -> dict:
        """
        Classifica uma transacao financeira a partir de texto livre.
        Retorna: tipo, valor, descricao, categoria, data, recorrente, dia_vencimento
        """
        hoje = datetime.now().strftime("%Y-%m-%d")
        dia_semana = datetime.now().strftime("%A")

        cats_despesa = ["Alimentação", "Transporte", "Moradia", "Assinaturas", "Lazer", "Saúde", "Educação", "Vestuário", "Outros"]
        cats_receita = ["Salário", "Aulas Optativas", "Consultoria", "Freelance", "Outros Receita"]

        if categorias_disponiveis:
            cats_all = categorias_disponiveis
        else:
            cats_all = cats_despesa + cats_receita

        system = f"""Voce e o assistente financeiro do Professor Wendel Castro.
Extraia os dados de uma transacao financeira a partir do texto do usuario.

Data de hoje: {hoje} ({dia_semana})

Categorias de DESPESA: {', '.join(cats_despesa)}
Categorias de RECEITA: {', '.join(cats_receita)}

Regras:
- Se o usuario diz "gastei", "paguei", "comprei", "assinatura" = despesa
- Se o usuario diz "recebi", "ganhei", "entrou", "salario", "pagamento" = receita
- Extraia o valor numerico (aceite R$, reais, etc)
- Se nao tem data explicita, use hoje ({hoje})
- Detecte se e recorrente: "todo mes", "mensal", "assinatura" = recorrente
- Classifique na categoria mais adequada
- Gere uma descricao limpa e curta

SEMPRE responda em JSON valido, sem markdown:
{{
  "tipo": "despesa|receita",
  "valor": 50.00,
  "descricao": "descricao limpa",
  "categoria": "uma das categorias acima",
  "data": "YYYY-MM-DD",
  "recorrente": false,
  "recorrencia": "mensal|semanal|anual|null",
  "dia_vencimento": null,
  "mensagem": "confirmacao curta para o usuario"
}}"""

        messages = [{"role": "user", "content": texto}]
        result = self._call_llm(system, messages, max_tokens=1024)

        if not result:
            return None

        try:
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                clean = clean.rsplit("```", 1)[0]
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erro ao parsear transacao: {e}\nResposta: {result}")
            return None

    def gerar_resumo_financeiro(self, transacoes: list, orcamentos: list = None, metas: list = None) -> str:
        """
        Gera um resumo financeiro inteligente com insights e coaching.
        """
        system = """Voce e o coach financeiro do Professor Wendel Castro.
Analise as transacoes do mes e gere um resumo com:
1. Balanco geral (receitas - despesas)
2. Top 3 categorias de gasto
3. Se tem orcamento, compare gasto vs limite (alerte se >80%)
4. Dica personalizada baseada nos padroes
5. Conexao com as metas financeiras (se houver)

Tom: direto, motivacional, sem rodeios. Maximo 300 palavras.
Use emojis com moderacao. Formate com markdown simples (* para negrito)."""

        dados = json.dumps({
            "transacoes": transacoes[:50],
            "orcamentos": orcamentos or [],
            "metas": metas or [],
        }, ensure_ascii=False, default=str)

        messages = [{"role": "user", "content": f"Dados financeiros:\n{dados}\n\nGere o resumo."}]
        result = self._call_llm(system, messages, max_tokens=1000)
        return result.strip() if result else "Sem dados suficientes para gerar resumo."
