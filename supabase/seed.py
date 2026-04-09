"""
Seed: Insere tarefas de exemplo no Supabase.
Rode: python supabase/seed.py

Requer variáveis de ambiente em .env (na raiz do projeto ou em bot/):
  SUPABASE_URL=https://seu-projeto.supabase.co
  SUPABASE_ANON_KEY=...  (ou SUPABASE_SERVICE_KEY para bypass de RLS)
"""
import os
import sys
import urllib.request
import json
from pathlib import Path

# Carrega .env (tenta raiz e pasta bot/)
try:
    from dotenv import load_dotenv
    for candidate in (Path(__file__).resolve().parent.parent / ".env",
                      Path(__file__).resolve().parent.parent / "bot" / ".env"):
        if candidate.exists():
            load_dotenv(candidate)
            break
except ImportError:
    pass  # dotenv é opcional — também aceita variáveis já exportadas

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERRO: Defina SUPABASE_URL e SUPABASE_ANON_KEY (ou SUPABASE_SERVICE_KEY) no .env")
    sys.exit(1)

tarefas = [
    {"titulo": "Preparar aula de IA - Modulo 3", "categoria": "Trabalho", "prioridade": "alta", "status": "pendente", "prazo": "2026-03-18", "horario": "08:00", "origem": "telegram"},
    {"titulo": "Reuniao equipe de dados", "categoria": "Consultoria", "prioridade": "alta", "status": "em_andamento", "prazo": "2026-03-17", "horario": "14:00", "meeting_link": "https://meet.google.com/abc-defg-hij", "meeting_platform": "meet", "origem": "telegram"},
    {"titulo": "Revisar proposta novo curso Python", "categoria": "Grupo Ser", "prioridade": "media", "status": "pendente", "prazo": "2026-03-19", "origem": "dashboard"},
    {"titulo": "Corrigir provas Banco de Dados", "categoria": "Trabalho", "prioridade": "alta", "status": "em_andamento", "prazo": "2026-03-18", "origem": "telegram"},
    {"titulo": "Alinhamento pedagogico semestral", "categoria": "Grupo Ser", "prioridade": "alta", "status": "pendente", "prazo": "2026-03-20", "horario": "10:00", "meeting_link": "https://teams.microsoft.com/l/meetup-join/abc", "meeting_platform": "teams", "origem": "telegram"},
    {"titulo": "Gravar video sobre Claude Code", "categoria": "Pessoal", "prioridade": "alta", "status": "pendente", "prazo": "2026-03-19", "horario": "19:00", "origem": "claude_code"},
    {"titulo": "Feedback alunos do TCC", "categoria": "Trabalho", "prioridade": "media", "status": "pendente", "prazo": "2026-03-19", "horario": "16:00", "meeting_link": "https://zoom.us/j/123456789", "meeting_platform": "zoom", "origem": "telegram"},
    {"titulo": "Comprar presente aniversario Mae", "categoria": "Pessoal", "prioridade": "media", "status": "pendente", "prazo": "2026-03-22", "origem": "telegram"},
    {"titulo": "Planejar conteudo da semana", "categoria": "Pessoal", "prioridade": "media", "status": "concluida", "prazo": "2026-03-16", "origem": "dashboard"},
    {"titulo": "Enviar relatorio mensal consultoria", "categoria": "Consultoria", "prioridade": "media", "status": "concluida", "prazo": "2026-03-15", "origem": "telegram"},
]

url = f"{SUPABASE_URL}/rest/v1/tarefas"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

print("Inserindo tarefas no Supabase...")
for i, tarefa in enumerate(tarefas, 1):
    data = json.dumps(tarefa).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"  [{i}/{len(tarefas)}] {tarefa['titulo'][:40]}... OK")
    except Exception as e:
        print(f"  [{i}/{len(tarefas)}] ERRO: {e}")

print(f"\nPronto! {len(tarefas)} tarefas inseridas.")
print("Atualize o dashboard no navegador para ver os dados reais!")
