"""
Seed: Insere tarefas de exemplo no Supabase.
Rode: python supabase/seed.py
"""
import urllib.request
import json

SUPABASE_URL = "https://vhfuthaqonzuasgpbcrg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoZnV0aGFxb256dWFzZ3BiY3JnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2ODk4OTgsImV4cCI6MjA4OTI2NTg5OH0.uJgJL-qrJtPqGUCWMO3e1a1JwudGvfUab4FxNC8SsBM"

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
