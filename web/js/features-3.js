// ========== PAINEL ADMIN (owner only) ==========
async function renderAdmin() {
  const container = document.getElementById('adminView');
  if (!isMetasOwner()) {
    container.innerHTML = '<div class="empty-state"><p>Acesso restrito ao administrador.</p></div>';
    return;
  }

  container.innerHTML = '<div style="padding:1rem"><div class="cleanup-status"><div class="spinner"></div><div>Carregando painel admin...</div></div></div>';

  try {
    // Carregar usuários com contagens
    const { data: perfis, error: pErr } = await sb
      .from('perfis_usuario')
      .select('user_id, role, status, nome_exibicao, ultimo_acesso, created_at, codigo_convite_usado')
      .order('created_at', { ascending: true });

    // Emails dos usuários (via auth.users não é acessível direto — usamos o email do currentUser para o owner e perfis para o resto)
    // Na prática, precisamos da view admin_usuarios_resumo, mas ela lê auth.users que RLS não permite.
    // Alternativa: guardar email no perfil. Por agora, mostrar user_id resumido.

    // Carregar convites
    const { data: convites, error: cErr } = await sb
      .from('codigos_convite')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(20);

    // Contagens por usuário
    const { data: tarefaCounts } = await sb.from('tarefas').select('user_id').then(r => {
      const counts = {};
      (r.data || []).forEach(t => { counts[t.user_id] = (counts[t.user_id] || 0) + 1; });
      return { data: counts };
    });

    const users = perfis || [];
    const invites = convites || [];

    let html = '<div style="padding:0.5rem 1rem">';
    html += '<h2 style="font-family:\'Inter\',sans-serif;font-weight:700;letter-spacing:-0.02em;font-size:1.4rem;color:var(--text-primary);margin-bottom:1rem">Painel Administrativo</h2>';

    // ===== SEÇÃO: GERAR CONVITE =====
    html += '<div class="review-card" style="margin-bottom:1rem">';
    html += '<h3 style="margin-bottom:0.75rem">Gerar código de convite</h3>';
    html += '<div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap">';
    html += '<select id="adminInviteExpiry" class="auth-input" style="width:auto;padding:0.4rem 0.6rem;font-size:0.85rem">';
    html += '<option value="1">1 dia</option><option value="3">3 dias</option><option value="7" selected>7 dias</option><option value="30">30 dias</option>';
    html += '</select>';
    html += '<button class="auth-btn" style="width:auto;padding:0.5rem 1.2rem;font-size:0.85rem" onclick="adminGerarConvite()">Gerar convite</button>';
    html += '</div>';
    html += '<div id="adminConviteResult" style="margin-top:0.75rem"></div>';
    html += '</div>';

    // ===== SEÇÃO: CONVITES EXISTENTES =====
    html += '<div class="review-card" style="margin-bottom:1rem">';
    html += '<h3 style="margin-bottom:0.75rem">Convites (' + invites.length + ')</h3>';
    if (invites.length === 0) {
      html += '<p style="color:var(--text-muted);font-size:0.85rem">Nenhum convite gerado ainda.</p>';
    } else {
      html += '<div style="overflow-x:auto"><table style="width:100%;font-size:0.8rem;border-collapse:collapse">';
      html += '<tr style="color:var(--text-muted);text-align:left"><th style="padding:0.4rem">Código</th><th>Criado</th><th>Expira</th><th>Status</th></tr>';
      invites.forEach(c => {
        const criado = new Date(c.created_at).toLocaleDateString('pt-BR');
        const expira = new Date(c.expira_em).toLocaleDateString('pt-BR');
        const now = new Date();
        let status = '';
        if (c.usado_por) status = '<span style="color:#4CAF50">Usado</span>';
        else if (!c.ativo) status = '<span style="color:var(--text-muted)">Desativado</span>';
        else if (new Date(c.expira_em) < now) status = '<span style="color:var(--pri-alta)">Expirado</span>';
        else status = '<span style="color:var(--success)">Ativo</span>';
        html += '<tr style="border-top:1px solid var(--border-subtle)">';
        html += '<td style="padding:0.4rem;font-family:monospace;font-weight:bold;letter-spacing:0.1em">' + c.codigo + '</td>';
        html += '<td>' + criado + '</td><td>' + expira + '</td><td>' + status + '</td>';
        html += '</tr>';
      });
      html += '</table></div>';
    }
    html += '</div>';

    // ===== SEÇÃO: USUÁRIOS =====
    html += '<div class="review-card" style="margin-bottom:1rem">';
    html += '<h3 style="margin-bottom:0.75rem">Usuários (' + users.length + ')</h3>';
    html += '<div style="overflow-x:auto"><table style="width:100%;font-size:0.8rem;border-collapse:collapse">';
    html += '<tr style="color:var(--text-muted);text-align:left"><th style="padding:0.4rem">Usuário</th><th>Role</th><th>Status</th><th>Tarefas</th><th>Último acesso</th><th>Ações</th></tr>';
    users.forEach(u => {
      const isOwner = u.role === 'owner';
      const isSelf = u.user_id === currentUser?.id;
      const nome = u.nome_exibicao || u.user_id.substring(0, 8) + '...';
      const conviteUsado = u.codigo_convite_usado || '-';
      const ultimoAcesso = u.ultimo_acesso ? new Date(u.ultimo_acesso).toLocaleDateString('pt-BR') : 'Nunca';
      const nTarefas = tarefaCounts?.[u.user_id] || 0;
      const statusColor = u.status === 'ativo' ? '#4CAF50' : u.status === 'desativado' ? 'var(--pri-alta)' : '#FFC107';

      html += '<tr style="border-top:1px solid var(--border-subtle)">';
      html += '<td style="padding:0.5rem"><div>' + nome + '</div><div style="font-size:0.7rem;color:var(--text-muted)">Convite: ' + conviteUsado + '</div></td>';
      html += '<td>' + (isOwner ? '<strong style="color:var(--accent)">Owner</strong>' : 'Usuário') + '</td>';
      html += '<td><span style="color:' + statusColor + '">' + (u.status || 'ativo') + '</span></td>';
      html += '<td style="text-align:center">' + nTarefas + '</td>';
      html += '<td>' + ultimoAcesso + '</td>';
      html += '<td>';
      if (!isSelf && !isOwner) {
        if (u.status === 'ativo') {
          html += '<button onclick="adminToggleUser(\'' + u.user_id + '\',\'desativado\')" style="font-size:0.7rem;padding:0.2rem 0.5rem;background:var(--pri-alta);color:white;border:none;border-radius:4px;cursor:pointer" title="Desativar">Desativar</button> ';
        } else {
          html += '<button onclick="adminToggleUser(\'' + u.user_id + '\',\'ativo\')" style="font-size:0.7rem;padding:0.2rem 0.5rem;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer" title="Ativar">Ativar</button> ';
        }
        html += '<button onclick="adminDeleteUser(\'' + u.user_id + '\')" style="font-size:0.7rem;padding:0.2rem 0.5rem;background:transparent;color:var(--pri-alta);border:1px solid var(--pri-alta);border-radius:4px;cursor:pointer" title="Excluir">Excluir</button>';
      } else if (isSelf) {
        html += '<span style="font-size:0.7rem;color:var(--text-muted)">Você</span>';
      }
      html += '</td></tr>';
    });
    html += '</table></div></div>';

    html += '</div>';
    container.innerHTML = html;
  } catch(e) {
    console.error('renderAdmin:', e);
    container.innerHTML = '<div class="empty-state"><p>Erro ao carregar painel admin.</p></div>';
  }
}

async function adminGerarConvite() {
  const resultEl = document.getElementById('adminConviteResult');
  const days = parseInt(document.getElementById('adminInviteExpiry').value) || 7;
  resultEl.innerHTML = '<span style="color:var(--text-muted)">Gerando...</span>';

  try {
    // Gerar código aleatório no JS (6 chars uppercase sem ambiguidades)
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let codigo = '';
    for (let i = 0; i < 6; i++) codigo += chars[Math.floor(Math.random() * chars.length)];

    const expira = new Date();
    expira.setDate(expira.getDate() + days);

    const { error } = await sb.from('codigos_convite').insert({
      codigo,
      criado_por: currentUser.id,
      expira_em: expira.toISOString()
    });

    if (error) throw error;

    resultEl.innerHTML = `
      <div style="background:rgba(185,145,91,0.08);border:1px solid rgba(185,145,91,0.2);border-radius:0.5rem;padding:0.75rem;text-align:center">
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.3rem">Código de convite (válido por ${days} dias)</div>
        <div style="font-size:1.8rem;font-weight:bold;letter-spacing:0.3em;color:var(--accent);font-family:var(--font-mono)">${codigo}</div>
        <button onclick="navigator.clipboard.writeText('${codigo}').then(()=>this.textContent='Copiado!')" style="margin-top:0.5rem;padding:0.3rem 1rem;font-size:0.8rem;background:var(--bg-glass);border:1px solid var(--border-subtle);border-radius:50px;color:var(--text-primary);cursor:pointer">Copiar código</button>
      </div>`;

    // Refresh lista de convites
    setTimeout(() => renderAdmin(), 500);
  } catch(e) {
    resultEl.innerHTML = '<span style="color:var(--pri-alta)">Erro: ' + (e.message || e) + '</span>';
  }
}

async function adminToggleUser(userId, novoStatus) {
  if (!confirm(`Tem certeza que deseja ${novoStatus === 'desativado' ? 'desativar' : 'reativar'} este usuário?`)) return;
  try {
    await sb.from('perfis_usuario').update({ status: novoStatus }).eq('user_id', userId);
    renderAdmin();
  } catch(e) {
    alert('Erro: ' + (e.message || e));
  }
}

async function adminDeleteUser(userId) {
  if (!confirm('ATENÇÃO: Excluir este usuário vai remover o perfil dele. As tarefas e dados ficarão órfãos. Tem certeza?')) return;
  if (!confirm('Esta ação é IRREVERSÍVEL. Confirma exclusão?')) return;
  try {
    await sb.from('perfis_usuario').delete().eq('user_id', userId);
    renderAdmin();
  } catch(e) {
    alert('Erro: ' + (e.message || e));
  }
}

// ========== METAS 2026 ==========
const METAS_CONFIG = {
  narrativa: '"De Executor Talentoso a Empresário da Própria Carreira."',
  pilares: [
    {
      id: 'carreira',
      icon: '🚀',
      nome: 'Carreira & Inovação',
      cor: 'var(--cat-trabalho)',
      categorias: ['Trabalho', 'Grupo Ser'],
      palavras: ['ai lab', 'ativa', 'servidor', 'mvp', 'piloto', 'mindset', 'inovação', 'lab', 'ferramenta', 'startup', 'saas', 'white label', 'dev', 'desenvolvedor'],
      metas: [
        {
          trimestre: 'Q1',
          titulo: 'AI Lab e Conquista de Território',
          descricao: 'Estruturar e oficializar o Laboratório de IA dentro do Grupo Ser, usando o Ativa AI como projeto piloto.',
          acoes: [
            'Oficialização: Apresentar o AI Lab para a diretoria',
            'Infraestrutura: Liberação dos 2 servidores + contrato do dev',
            'Expansão: Rodar piloto do Mindset em segunda IES'
          ],
          indicadores: ['Servidores instalados e rodando', 'Ativa AI usado por professores pilotos']
        },
        {
          trimestre: 'Q2',
          titulo: 'Validação do Negócio (Startup)',
          descricao: 'Produto pronto para fora do Grupo Ser (White label ou SaaS). Fechar 1 consultoria externa 6k+.',
          acoes: [
            'Ativa AI ou Mindset prontos para oferecer externamente',
            'Fechar 1 consultoria externa de IA (ticket 6k+)'
          ],
          indicadores: ['Produto oferecido externamente', 'Receita de consultoria externa']
        },
        {
          trimestre: 'anual',
          titulo: 'Reconhecimento Nacional & Equity',
          descricao: 'Grupo Ser reconhecido como case de inovação em IA no ensino. Promoção ou contrato de sociedade.',
          acoes: [
            'Grupo Ser como case nacional de IA na educação',
            'Promoção ou equity na ferramenta'
          ],
          indicadores: ['Reconhecimento público do case', 'Contrato formalizado']
        }
      ]
    },
    {
      id: 'financas',
      icon: '💰',
      nome: 'Finanças',
      cor: 'var(--cat-consultoria)',
      categorias: ['Pessoal', 'Consultoria'],
      palavras: ['financeiro', 'investimento', 'banco', 'conta', 'dinheiro', 'salário', 'dívida', 'pagar', 'optativa', 'consultoria', 'renegociar', 'assinatura', 'extrato', 'orçamento', 'reserva', 'caixa'],
      metas: [
        {
          trimestre: 'Q1',
          titulo: 'Saneamento Financeiro & Caixa Rápido',
          descricao: 'Organizar a casa financeira, cortar R$500 em custos fixos e blindar renda extra.',
          acoes: [
            'Renegociar plano de celular (baixar de 320 para <150)',
            'Auditar e cortar assinaturas desnecessárias',
            'Abrir conta separada para aulas optativas e consultorias',
            'Realizar reparo elétrico do AP'
          ],
          indicadores: ['Redução de R$500+ em custos fixos', 'Dívidas mapeadas com plano de pagamento']
        },
        {
          trimestre: 'Q2',
          titulo: 'Viajar Leve',
          descricao: 'Viagem nacional em família paga à vista. Dívidas de curto prazo quitadas.',
          acoes: [
            'Viagem nacional realizada (paga à vista)',
            'Dívidas curtas quitadas com renda das optativas'
          ],
          indicadores: ['Viagem realizada', 'Dívidas curtas zeradas']
        },
        {
          trimestre: 'anual',
          titulo: 'Caixa Robusto',
          descricao: 'Viagem internacional de 2027 garantida no caixa.',
          acoes: ['Reserva financeira para viagem internacional 2027'],
          indicadores: ['Valor reservado para 2027']
        }
      ]
    },
    {
      id: 'marca',
      icon: '📱',
      nome: 'Marca Pessoal',
      cor: 'var(--cat-pessoal)',
      categorias: ['Consultoria', 'Pessoal'],
      palavras: ['instagram', 'conteúdo', 'post', 'stories', 'reels', 'gravar', 'filmar', 'edição', 'corte', 'nugget', 'seguidor', 'palestra', 'notável', 'marca', 'autoridade', 'digital', 'direct', 'orçamento'],
      metas: [
        {
          trimestre: 'Q1',
          titulo: 'Autoridade Digital (Notável Mestre)',
          descricao: 'Transformar aulas em conteúdo de alto valor. 2-3 posts estratégicos por semana.',
          acoes: [
            'Gravar/filmar trechos das aulas',
            'Extrair 1 nugget (corte de insight) por semana',
            'Mostrar bastidores do AI Lab nos stories'
          ],
          indicadores: ['Crescimento consistente de seguidores', 'Pedidos de orçamento via direct']
        },
        {
          trimestre: 'anual',
          titulo: '10k+ e Agenda de Palestras',
          descricao: 'Instagram com 10k+ seguidores e agenda de palestras aberta.',
          acoes: [
            'Alcançar 10k seguidores',
            'Abrir agenda de palestras pagas'
          ],
          indicadores: ['10k+ seguidores', 'Palestras agendadas']
        }
      ]
    },
    {
      id: 'saude',
      icon: '🏃',
      nome: 'Saúde & Esporte',
      cor: 'var(--pri-alta)',
      categorias: ['Pessoal'],
      palavras: ['academia', 'treino', 'corrida', 'correr', 'beach', 'tennis', 'dieta', 'peso', 'kg', 'álcool', 'exercício', 'saúde', 'musculação', 'cardio', 'alongamento', 'físico'],
      metas: [
        {
          trimestre: 'Q1',
          titulo: 'Máquina Física (10k e 78kg)',
          descricao: 'Recuperar peso de performance (78kg) e correr 10km.',
          acoes: [
            'Correr 10km',
            'Treino específico de Beach Tennis',
            'Dieta: cortar álcool seg-qui, alimentação limpa'
          ],
          indicadores: ['10km corridos', 'Peso 78kg', 'Torneio do trimestre']
        },
        {
          trimestre: 'anual',
          titulo: 'Seleção Paraense de Beach Tennis',
          descricao: 'Classificar para a Seleção Paraense e competir no Brasileiro em Novembro.',
          acoes: [
            'Classificar para Seleção Paraense',
            'Competir no Brasileiro (Nov)'
          ],
          indicadores: ['Convocação para Seleção', 'Participação no Brasileiro']
        }
      ]
    }
  ]
};


function getCurrentQuarter() {
  const m = new Date().getMonth();
  if (m < 3) return 'Q1';
  if (m < 6) return 'Q2';
  if (m < 9) return 'Q3';
  return 'Q4';
}

function matchTaskToPilar(task, pilar) {
  // Categoria match
  const catMatch = pilar.categorias.includes(task.categoria);
  // Keyword match
  const titulo = (task.titulo || '').toLowerCase();
  const notas = (task.notas || '').toLowerCase();
  const texto = titulo + ' ' + notas;
  const kwMatch = pilar.palavras.some(kw => texto.includes(kw));
  return catMatch && kwMatch;
}

function getPilarStats(pilar) {
  const related = tasks.filter(t => matchTaskToPilar(t, pilar));
  const done = related.filter(t => t.status === 'concluida').length;
  const total = related.length;
  const pending = related.filter(t => t.status !== 'concluida');
  const thisWeek = (() => {
    const week = getWeekRange();
    return related.filter(t => {
      if (t.status !== 'concluida') return false;
      const d = (t.updated_at || t.created_at || '').split('T')[0];
      return d >= week.start && d <= week.end;
    }).length;
  })();
  // Dias sem atividade
  const lastActivity = related
    .filter(t => t.status === 'concluida')
    .map(t => t.updated_at || t.created_at || '')
    .sort().reverse()[0];
  const daysSince = lastActivity
    ? Math.floor((Date.now() - new Date(lastActivity).getTime()) / 86400000)
    : 999;
  return { related, done, total, pending, thisWeek, daysSince };
}

function getMetasForQuarter(pilar) {
  const q = metasQuarterFilter === 'current' ? getCurrentQuarter() : metasQuarterFilter;
  if (q === 'all') return pilar.metas;
  return pilar.metas.filter(m => m.trimestre === q || m.trimestre === 'anual');
}

// Perfil do usuário atual (carregado após login)

async function loadUserProfile() {
  if (!currentUser) { userProfile = null; return; }
  try {
    const { data, error } = await sb
      .from('perfis_usuario')
      .select('*')
      .eq('user_id', currentUser.id)
      .maybeSingle();

    if (error) {
      if (error.code === '42P01' || /does not exist/i.test(error.message || '')) {
        console.warn('[perfil] Tabela perfis_usuario não existe. Rode a migration 016.');
      } else {
        console.warn('[perfil] Erro ao carregar:', error);
      }
      userProfile = { role: 'user' };
      return;
    }

    if (data) {
      userProfile = data;
      console.log('[perfil] Carregado — role:', data.role);
    } else {
      // Perfil não existe — criar
      console.warn('[perfil] Criando perfil...');
      await sb.from('perfis_usuario')
        .insert({ user_id: currentUser.id, role: 'user' });
      userProfile = { role: 'user' };
    }

    // Auto-promoção: se não é owner, verificar se o sistema tem algum owner
    // Se não tem, este usuário é o primeiro → promover automaticamente
    if (userProfile.role !== 'owner') {
      await autoPromoteFirstOwner();
    }

    // Atualizar UI
    const adminBtn = document.getElementById('adminNavBtn');
    if (adminBtn) adminBtn.style.display = (userProfile.role === 'owner') ? '' : 'none';
    console.log('[perfil] Role final:', userProfile.role);
  } catch(e) {
    console.warn('[perfil] Exceção:', e);
    userProfile = { role: 'user' };
  }
}

async function autoPromoteFirstOwner() {
  // Estratégia 1: RPC SECURITY DEFINER (ignora RLS, vê todos os perfis)
  const { data: rpcResult, error: rpcError } = await sb.rpc('promover_primeiro_owner');
  if (!rpcError) {
    console.log('[perfil] RPC retornou:', rpcResult);
    if (rpcResult === 'promovido a owner') {
      userProfile.role = 'owner';
      return;
    }
    // 'já existe owner' — verificar se sou eu (pode ter sido promovido em outra sessão)
    if (rpcResult === 'já existe owner') {
      const { data: recheck } = await sb.from('perfis_usuario')
        .select('role')
        .eq('user_id', currentUser.id)
        .maybeSingle();
      if (recheck && recheck.role === 'owner') {
        userProfile.role = 'owner';
        console.log('[perfil] Já sou owner (confirmado via recheck).');
      }
      return;
    }
  }

  // Estratégia 2: promoção direta (se RPC não existe ou falhou)
  console.warn('[perfil] RPC indisponível:', rpcError?.message || 'resposta inesperada');
  const { data: owners } = await sb.from('perfis_usuario')
    .select('user_id')
    .eq('role', 'owner')
    .limit(1);
  if (!owners || owners.length === 0) {
    const { error: upErr } = await sb.from('perfis_usuario')
      .update({ role: 'owner' })
      .eq('user_id', currentUser.id);
    if (!upErr) {
      userProfile.role = 'owner';
      console.log('[perfil] Promovido a owner (fallback direto).');
    } else {
      console.warn('[perfil] Falha ao promover:', upErr.message);
    }
  }
}

function isMetasOwner() {
  return userProfile && userProfile.role === 'owner';
}

function renderMetas() {
  const container = document.getElementById('metasView');
  console.log('[metas] userProfile:', JSON.stringify(userProfile), '| isOwner:', isMetasOwner());

  // Se não é o dono, mostrar empty state com diagnóstico
  if (!isMetasOwner()) {
    const debugRole = userProfile ? userProfile.role : 'null';
    container.innerHTML = `
      <div class="fin-header"><h2>Metas 2026</h2></div>
      <div class="fin-empty">
        <div style="font-size:2.5rem;margin-bottom:0.5rem">🎯</div>
        <strong>Acesso restrito</strong>
        <p>Seu perfil está como <code>${debugRole}</code>. Metas requerem role <code>owner</code>.</p>
        <p style="margin-top:0.5rem;font-size:0.75rem;opacity:0.7">Rode no Supabase SQL Editor:<br>
        <code>UPDATE perfis_usuario SET role = 'owner' WHERE user_id = '${currentUser?.id || '?'}';</code></p>
      </div>`;
    return;
  }

  const currentQ = getCurrentQuarter();

  // Calcular stats de todos os pilares
  const pilarStats = METAS_CONFIG.pilares.map(p => ({
    pilar: p,
    stats: getPilarStats(p)
  }));

  // Progresso geral
  const totalDone = pilarStats.reduce((s, p) => s + p.stats.done, 0);
  const totalAll = pilarStats.reduce((s, p) => s + p.stats.total, 0);
  const totalWeek = pilarStats.reduce((s, p) => s + p.stats.thisWeek, 0);

  // Insights
  const insights = [];
  if (totalWeek > 0) {
    const pilarsAtivos = pilarStats.filter(p => p.stats.thisWeek > 0).map(p => p.pilar.nome);
    insights.push(`Esta semana você avançou em <strong>${pilarsAtivos.length}</strong> de 4 pilares: ${pilarsAtivos.join(', ')}`);
  }
  pilarStats.forEach(p => {
    if (p.stats.thisWeek > 0) {
      insights.push(`<strong>${p.pilar.icon} ${p.pilar.nome}:</strong> ${p.stats.thisWeek} tarefa(s) concluída(s) esta semana`);
    }
  });
  const dormentes = pilarStats.filter(p => p.stats.daysSince > 7 && p.stats.daysSince < 999);
  dormentes.forEach(p => {
    insights.push(`⚠️ <strong>${p.pilar.nome}</strong> está há ${p.stats.daysSince} dias sem atividade concluída`);
  });
  const semAtividade = pilarStats.filter(p => p.stats.total === 0);
  semAtividade.forEach(p => {
    insights.push(`🔴 <strong>${p.pilar.nome}</strong> não tem nenhuma tarefa vinculada ainda`);
  });
  if (insights.length === 0) {
    insights.push('Comece a criar tarefas ligadas aos seus pilares para ver o progresso aqui!');
  }

  // Quarter filter buttons
  const quarters = [
    { key: 'current', label: currentQ + ' (atual)' },
    { key: 'Q1', label: 'Q1' },
    { key: 'Q2', label: 'Q2' },
    { key: 'anual', label: 'Anual' },
    { key: 'all', label: 'Todas' }
  ];

  container.innerHTML = `
    <div class="metas-header">
      <h2>Metas 2026</h2>
      <div class="metas-narrative">${METAS_CONFIG.narrativa}</div>
      <div class="metas-quarter-nav">
        ${quarters.map(q => `<button class="${metasQuarterFilter === q.key ? 'active' : ''}" onclick="metasQuarterFilter='${q.key}';renderMetas()">${q.label}</button>`).join('')}
      </div>
    </div>

    <div class="metas-progress-summary">
      ${pilarStats.map(p => {
        const pct = p.stats.total > 0 ? Math.round(p.stats.done / p.stats.total * 100) : 0;
        return `<div class="metas-pilar-mini" onclick="document.getElementById('pilar-${p.pilar.id}').scrollIntoView({behavior:'smooth',block:'start'})">
          <div class="pilar-icon">${p.pilar.icon}</div>
          <span class="pilar-name">${p.pilar.nome}</span>
          <div class="pilar-pct" style="color:${p.pilar.cor}">${pct}%</div>
          <div class="pilar-bar"><div class="pilar-bar-fill" style="width:${pct}%;background:${p.pilar.cor}"></div></div>
        </div>`;
      }).join('')}
    </div>

    <div class="metas-insights">
      <h3>Insights da semana</h3>
      ${insights.map(i => `<div class="metas-insight-item">${i}</div>`).join('')}
    </div>

    <div class="metas-ai-section">
      <button class="metas-ai-btn" id="metasAiBtn" onclick="callGeminiForMetas()">🧠 Análise IA das Metas</button>
      <div id="metasAiResult"></div>
    </div>

    ${pilarStats.map(p => {
      const pct = p.stats.total > 0 ? Math.round(p.stats.done / p.stats.total * 100) : 0;
      const metas = getMetasForQuarter(p.pilar);
      const recentDone = p.stats.related.filter(t => t.status === 'concluida').slice(0, 5);
      const recentPending = p.stats.pending.slice(0, 5);

      return `<div class="metas-pilar-card" id="pilar-${p.pilar.id}">
        <div class="metas-pilar-card-header">
          <span class="pilar-icon">${p.pilar.icon}</span>
          <span class="pilar-title">${p.pilar.nome}</span>
          <span class="pilar-pct-big" style="color:${p.pilar.cor}">${pct}%</span>
        </div>
        <div class="metas-bar-full"><div class="bar-fill" style="width:${pct}%;background:${p.pilar.cor}"></div></div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:0.6rem">
          ${p.stats.done} concluída(s) · ${p.stats.pending.length} pendente(s) · ${p.stats.thisWeek} esta semana
        </div>

        ${metas.map(m => `<div class="metas-goal">
          <div class="metas-goal-title">${m.titulo} <span style="font-size:0.65rem;color:var(--text-muted);font-weight:400">${m.trimestre}</span></div>
          <div class="metas-goal-desc">${m.descricao}</div>
          <ul class="metas-actions-list">
            ${m.acoes.map(a => `<li>${a}</li>`).join('')}
          </ul>
        </div>`).join('')}

        ${(recentDone.length > 0 || recentPending.length > 0) ? `<div class="metas-related">
          <div class="metas-related-title">Tarefas vinculadas</div>
          ${recentDone.map(t => `<div class="metas-related-item"><span class="done-badge">✓</span> ${escapeHtml(t.titulo)}</div>`).join('')}
          ${recentPending.map(t => `<div class="metas-related-item"><span class="pending-badge">○</span> ${escapeHtml(t.titulo)}</div>`).join('')}
        </div>` : '<div style="font-size:0.72rem;color:var(--text-muted);font-style:italic;margin-top:0.4rem">Nenhuma tarefa vinculada a este pilar ainda</div>'}
      </div>`;
    }).join('')}

    ${pilarStats.some(p => p.stats.daysSince > 7 && p.stats.daysSince < 999) ? `<div class="metas-dormant">
      <h4>Pilares que precisam de atenção</h4>
      ${pilarStats.filter(p => p.stats.daysSince > 7 && p.stats.daysSince < 999).map(p =>
        `<p>${p.pilar.icon} <strong>${p.pilar.nome}</strong> — ${p.stats.daysSince} dias sem atividade concluída</p>`
      ).join('')}
    </div>` : ''}
  `;

  // Auto-carregar análise IA cacheada do dia
  setTimeout(() => {
    const hoje = new Date().toISOString().split('T')[0];
    const cached = localStorage.getItem('metas_ai_' + hoje);
    const resultDiv = document.getElementById('metasAiResult');
    if (cached && resultDiv) {
      resultDiv.innerHTML = renderAiResult(cached, hoje);
    }
  }, 100);
}

// ========== FINANÇAS ==========

async function loadFinancas() {
  const now = new Date();
  const inicio = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-01`;
  const nextMonth = now.getMonth() === 11 ? `${now.getFullYear()+1}-01-01` : `${now.getFullYear()}-${String(now.getMonth()+2).padStart(2,'0')}-01`;

  const headers = await getAuthHeaders();
  const uid = currentUser?.id;
  if (!uid) { finTransacoes = []; finOrcamentos = []; finMetas = []; return; }
  try {
    const [tRes, oRes, mRes] = await Promise.all([
      fetch(`${SUPABASE_URL}/rest/v1/transacoes?user_id=eq.${uid}&data=gte.${inicio}&data=lt.${nextMonth}&order=data.desc,created_at.desc`, { headers }),
      fetch(`${SUPABASE_URL}/rest/v1/orcamento_mensal?user_id=eq.${uid}&mes=eq.${inicio}`, { headers }),
      fetch(`${SUPABASE_URL}/rest/v1/metas_financeiras?user_id=eq.${uid}&status=eq.ativa&order=created_at.asc`, { headers }),
    ]);
    if (tRes.ok) finTransacoes = await tRes.json();
    if (oRes.ok) finOrcamentos = await oRes.json();
    if (mRes.ok) finMetas = await mRes.json();
  } catch(e) { console.error('Erro carregando finanças:', e); }
}

function formatMoney(v) {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getFinWeekRange() {
  const today = new Date(); today.setHours(0,0,0,0);
  const dow = today.getDay();
  const mon = new Date(today); mon.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
  const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
  return { start: mon.toISOString().split('T')[0], end: sun.toISOString().split('T')[0] };
}

function getFinScopedTransacoes() {
  if (finScope === 'week') {
    const w = getFinWeekRange();
    return finTransacoes.filter(t => t.data >= w.start && t.data <= w.end);
  }
  return finTransacoes;
}

async function renderFinancas() {
  const container = document.getElementById('financasView');
  await loadFinancas();

  const now = new Date();
  const mesNome = now.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  const daysInMonth = new Date(now.getFullYear(), now.getMonth()+1, 0).getDate();
  const daysLeft = daysInMonth - now.getDate();
  const scopeLabel = finScope === 'week' ? 'esta semana' : mesNome;

  const scoped = getFinScopedTransacoes();
  const pagas = scoped.filter(t => t.status === 'pago' || !t.status);
  const pendentes = finTransacoes.filter(t => t.status === 'pendente');
  const planejadas = finTransacoes.filter(t => t.status === 'planejado');

  const receitasPagas = pagas.filter(t => t.tipo === 'receita').reduce((s,t) => s + Number(t.valor), 0);
  const despesasPagas = pagas.filter(t => t.tipo === 'despesa').reduce((s,t) => s + Number(t.valor), 0);
  const saldo = receitasPagas - despesasPagas;
  const perDay = daysLeft > 0 && saldo > 0 ? saldo / daysLeft : 0;

  // PF vs PJ
  const recPF = pagas.filter(t => t.tipo === 'receita' && t.pessoa !== 'pj').reduce((s,t) => s + Number(t.valor), 0);
  const recPJ = pagas.filter(t => t.tipo === 'receita' && t.pessoa === 'pj').reduce((s,t) => s + Number(t.valor), 0);

  // Receitas pendentes
  const totalPendente = pendentes.filter(t => t.tipo === 'receita').reduce((s,t) => s + Number(t.valor), 0);
  const totalPlanejado = planejadas.filter(t => t.tipo === 'receita').reduce((s,t) => s + Number(t.valor), 0);

  // Gastos por categoria
  const catGastos = {};
  pagas.filter(t => t.tipo === 'despesa').forEach(t => { catGastos[t.categoria] = (catGastos[t.categoria] || 0) + Number(t.valor); });
  const catSorted = Object.entries(catGastos).sort((a,b) => b[1] - a[1]);
  const maxCatVal = catSorted.length > 0 ? catSorted[0][1] : 1;
  const catCores = { 'Alimentação':'#FF6B6B', 'Transporte':'#4ECDC4', 'Moradia':'#45B7D1', 'Assinaturas':'#96CEB4', 'Lazer':'#DDA0DD', 'Saúde':'#98D8C8', 'Educação':'#F7DC6F', 'Vestuário':'#BB8FCE', 'Outros':'#AEB6BF' };

  if (finTransacoes.length === 0) {
    container.innerHTML = `
      <div class="fin-header"><h2>Finanças</h2><div class="fin-month">${mesNome}</div></div>
      <div class="fin-empty">
        <div style="font-size:2.5rem;margin-bottom:0.5rem">💰</div>
        <strong>Nenhuma transação este mês</strong>
        <p>Use <code>/gasto</code> ou <code>/receita</code> no Telegram para começar!</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="fin-header">
      <h2>Finanças</h2>
      <div class="fin-month">${mesNome}</div>
      <div class="scope-toggle" style="margin-top:0.5rem;max-width:220px;margin-left:auto;margin-right:auto">
        <button class="scope-btn ${finScope==='week'?'active':''}" onclick="finScope='week';renderFinancas()">Semana</button>
        <button class="scope-btn ${finScope==='month'?'active':''}" onclick="finScope='month';renderFinancas()">Mês</button>
      </div>
    </div>

    <div class="fin-saldo-card">
      <div class="fin-saldo-label">Saldo ${scopeLabel}</div>
      <div class="fin-saldo-valor ${saldo >= 0 ? 'positive' : 'negative'}">${formatMoney(saldo)}</div>
      <div class="fin-saldo-detail">
        <span class="receita">▲ ${formatMoney(receitasPagas)}</span>
        <span class="despesa">▼ ${formatMoney(despesasPagas)}</span>
      </div>
      ${perDay > 0 && finScope === 'month' ? `<div class="fin-disponivel">~${formatMoney(perDay)}/dia disponível (${daysLeft} dias restantes)</div>` : ''}
      ${recPF > 0 || recPJ > 0 ? `<div style="display:flex;justify-content:center;gap:1.5rem;margin-top:0.4rem;font-size:0.72rem">
        <span style="color:var(--text-secondary)">👤 PF: ${formatMoney(recPF)}</span>
        <span style="color:var(--text-secondary)">🏢 PJ: ${formatMoney(recPJ)}</span>
      </div>` : ''}
    </div>

    ${(pendentes.length > 0 || planejadas.length > 0) ? `<div class="fin-card" style="margin-bottom:0.8rem;border-color:rgba(185,145,91,0.2)">
      <h3 style="color:var(--amber)">⏳ Receitas a receber</h3>
      ${pendentes.filter(t=>t.tipo==='receita').map(t => {
        const pessoa = t.pessoa === 'pj' ? '🏢' : '👤';
        return `<div class="fin-transacao" style="border-color:rgba(185,145,91,0.1)">
          <div class="fin-transacao-icon">⏳</div>
          <div class="fin-transacao-info">
            <div class="fin-transacao-desc">${escapeHtml(t.descricao)}</div>
            <div class="fin-transacao-meta">${pessoa} ${escapeHtml(t.categoria)}${t.pagador ? ' · 💼 ' + escapeHtml(t.pagador) : ''}${t.data_prevista ? ' · Previsto: ' + new Date(t.data_prevista+'T12:00:00').toLocaleDateString('pt-BR') : ''}</div>
          </div>
          <div style="display:flex;align-items:center;gap:0.4rem">
            <div class="fin-transacao-valor receita">+ ${formatMoney(t.valor)}</div>
            <button onclick="marcarRecebido('${t.id}')" style="background:var(--amber);color:var(--bg-deep);border:none;border-radius:0.4rem;padding:0.25rem 0.5rem;font-size:0.65rem;font-weight:600;cursor:pointer;white-space:nowrap" title="Marcar como recebido">Recebido</button>
          </div>
        </div>`;
      }).join('')}
      ${planejadas.filter(t=>t.tipo==='receita').map(t => {
        const pessoa = t.pessoa === 'pj' ? '🏢' : '👤';
        return `<div class="fin-transacao" style="border-color:rgba(185,145,91,0.1);opacity:0.7">
          <div class="fin-transacao-icon">📋</div>
          <div class="fin-transacao-info">
            <div class="fin-transacao-desc">${escapeHtml(t.descricao)}</div>
            <div class="fin-transacao-meta">${pessoa} ${escapeHtml(t.categoria)}${t.pagador ? ' · 💼 ' + escapeHtml(t.pagador) : ''}</div>
          </div>
          <div class="fin-transacao-valor receita" style="opacity:0.6">+ ${formatMoney(t.valor)}</div>
        </div>`;
      }).join('')}
      <div style="display:flex;justify-content:space-between;padding-top:0.5rem;border-top:1px solid var(--border-subtle);margin-top:0.3rem;font-size:0.78rem">
        <span style="color:var(--text-muted)">Total a receber</span>
        <span style="color:var(--amber);font-weight:600">${formatMoney(totalPendente + totalPlanejado)}</span>
      </div>
    </div>` : ''}

    <div class="fin-grid">
      <div class="fin-card">
        <h3>Gastos por categoria</h3>
        ${catSorted.length === 0 ? '<div style="font-size:0.75rem;color:var(--text-muted)">Sem despesas</div>' :
          catSorted.map(([cat, val]) => {
            const pct = (val / maxCatVal * 100);
            const cor = catCores[cat] || '#AEB6BF';
            const pctTotal = despesasPagas > 0 ? (val/despesasPagas*100).toFixed(0) : 0;
            return `<div class="fin-cat-item">
              <span class="fin-cat-name">${cat}</span>
              <div class="fin-cat-bar"><div class="fin-cat-bar-fill" style="width:${pct}%;background:${cor}"></div></div>
              <span class="fin-cat-val">${formatMoney(val)} (${pctTotal}%)</span>
            </div>`;
          }).join('')}
      </div>

      <div class="fin-card">
        <h3>Orçamento</h3>
        ${finOrcamentos.length === 0 ?
          '<div style="font-size:0.75rem;color:var(--text-muted)">Use <code>/orcamento</code> no Telegram</div>' :
          finOrcamentos.map(orc => {
            const gasto = catGastos[orc.categoria] || 0;
            const limite = Number(orc.limite);
            const pct = limite > 0 ? (gasto/limite*100) : 0;
            const cor = pct < 60 ? '#2ECC71' : (pct < 80 ? '#F39C12' : '#FF6B6B');
            return `<div class="fin-orc-item">
              <div class="fin-orc-header">
                <span class="fin-orc-cat">${escapeHtml(orc.categoria)}</span>
                <span class="fin-orc-val" style="color:${cor}">${formatMoney(gasto)} / ${formatMoney(limite)} (${pct.toFixed(0)}%)</span>
              </div>
              <div class="fin-orc-bar"><div class="fin-orc-bar-fill" style="width:${Math.min(pct,100)}%;background:${cor}"></div></div>
            </div>`;
          }).join('')}
      </div>
    </div>

    ${finMetas.length > 0 ? `<div class="fin-card" style="margin-bottom:0.8rem">
      <h3>Metas Financeiras</h3>
      ${finMetas.map(m => {
        const pct = Number(m.valor_alvo) > 0 ? (Number(m.valor_atual)/Number(m.valor_alvo)*100) : 0;
        return `<div class="fin-orc-item">
          <div class="fin-orc-header">
            <span class="fin-orc-cat">${m.icone || '🎯'} ${escapeHtml(m.titulo)}${m.prazo ? ' · até ' + new Date(m.prazo+'T12:00:00').toLocaleDateString('pt-BR') : ''}</span>
            <span class="fin-orc-val" style="color:var(--amber)">${formatMoney(m.valor_atual)} / ${formatMoney(m.valor_alvo)}</span>
          </div>
          <div class="fin-orc-bar"><div class="fin-orc-bar-fill" style="width:${Math.min(pct,100)}%;background:var(--amber)"></div></div>
        </div>`;
      }).join('')}
    </div>` : ''}

    <div class="fin-card fin-transacoes">
      <h3>Transações ${scopeLabel}</h3>
      ${scoped.length === 0 ? '<div style="font-size:0.75rem;color:var(--text-muted);padding:0.5rem 0">Sem transações neste período</div>' :
      scoped.slice(0, 30).map(t => {
        const isReceita = t.tipo === 'receita';
        const statusIcon = t.status === 'pendente' ? '⏳ ' : (t.status === 'planejado' ? '📋 ' : '');
        const pessoaTag = t.pessoa === 'pj' ? ' · 🏢 PJ' : '';
        return `<div class="fin-transacao">
          <div class="fin-transacao-icon">${statusIcon || (isReceita ? '🟢' : '🔴')}</div>
          <div class="fin-transacao-info">
            <div class="fin-transacao-desc">${escapeHtml(t.descricao)}</div>
            <div class="fin-transacao-meta">${escapeHtml(t.categoria)} · ${new Date(t.data+'T12:00:00').toLocaleDateString('pt-BR')}${pessoaTag}${t.pagador ? ' · ' + escapeHtml(t.pagador) : ''}</div>
          </div>
          <div class="fin-transacao-valor ${isReceita ? 'receita' : 'despesa'}">${isReceita ? '+' : '-'} ${formatMoney(t.valor)}</div>
        </div>`;
      }).join('')}
    </div>
  `;
}

async function marcarRecebido(id) {
  const hoje = new Date().toISOString().split('T')[0];
  const headers = await getAuthHeaders();
  headers['Content-Type'] = 'application/json';
  headers['Prefer'] = 'return=representation';
  const uid = currentUser?.id;
  if (!uid) return;
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/transacoes?id=eq.${id}&user_id=eq.${uid}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ status: 'pago', data: hoje })
    });
    if (res.ok) {
      renderFinancas();
    } else {
      alert('Erro ao marcar como recebido');
    }
  } catch(e) { console.error(e); alert('Erro de conexão'); }
}

// ========== METAS AI COACHING (Gemini 2.5 Flash) ==========

function getGeminiKey() {
  return localStorage.getItem('gemini_api_key') || '';
}

function buildMetasPrompt() {
  const hoje = new Date().toISOString().split('T')[0];
  const week = getWeekRange();

  // Coletar dados de cada pilar
  const pilarData = METAS_CONFIG.pilares.map(p => {
    const stats = getPilarStats(p);
    const recentDone = stats.related.filter(t => t.status === 'concluida').slice(0, 10).map(t => t.titulo);
    const topPending = stats.pending.slice(0, 10).map(t => `${t.titulo}${t.prazo ? ' (prazo: ' + t.prazo + ')' : ''}`);
    return {
      pilar: p.nome,
      metas: p.metas.map(m => m.titulo + ': ' + m.descricao).join('; '),
      concluidas: recentDone,
      pendentes: topPending,
      total: stats.total,
      done: stats.done,
      diasSemAtividade: stats.daysSince,
      progressoSemana: stats.thisWeek
    };
  });

  // Stats gerais
  const totalTasks = tasks.length;
  const totalDone = tasks.filter(t => t.status === 'concluida').length;
  const totalOverdue = tasks.filter(t => isOverdue(t)).length;
  const weekDone = tasks.filter(t => {
    if (t.status !== 'concluida') return false;
    const d = (t.updated_at || t.created_at || '').split('T')[0];
    return d >= week.start && d <= week.end;
  }).length;

  const system = `Você é um coach de alta performance e estrategista pessoal. Seu cliente é Wendel Castro, professor de IA e Banco de Dados, que tem um Planejamento Estratégico Pessoal para 2026 com a narrativa: ${METAS_CONFIG.narrativa}

Seu papel é analisar o progresso real das tarefas vs as metas planejadas e dar um parecer HONESTO, DIRETO e MOTIVADOR. Fale em português do Brasil, tom de coach experiente — nem bajulador nem duro demais. Use dados concretos.

IMPORTANTE:
- Destaque conquistas que ele pode não ter percebido
- Aponte pilares negligenciados com urgência proporcional
- Sugira 2-3 ações concretas para a próxima semana
- Se algum pilar está sem atividade há mais de 7 dias, alerte com firmeza
- Conecte as tarefas do dia a dia com as metas maiores do ano
- Seja conciso mas completo (máximo 400 palavras)
- Use formatação HTML: <h4>, <strong>, <ul><li>, <p>. NÃO use markdown.`;

  const userMsg = `Data de hoje: ${hoje}
Semana: ${week.start} a ${week.end}

RESUMO GERAL:
- Total de tarefas: ${totalTasks} | Concluídas: ${totalDone} | Atrasadas: ${totalOverdue}
- Concluídas esta semana: ${weekDone}

DADOS POR PILAR:
${pilarData.map(p => `
### ${p.pilar}
- Metas: ${p.metas}
- Tarefas totais: ${p.total} | Concluídas: ${p.done} | Esta semana: ${p.progressoSemana}
- Dias sem atividade concluída: ${p.diasSemAtividade === 999 ? 'NUNCA teve atividade' : p.diasSemAtividade}
- Últimas concluídas: ${p.concluidas.length > 0 ? p.concluidas.join(', ') : 'Nenhuma'}
- Pendentes: ${p.pendentes.length > 0 ? p.pendentes.join(', ') : 'Nenhuma'}
`).join('\n')}

Faça sua análise.`;

  return { system, userMsg };
}

async function callGeminiForMetas() {
  const key = getGeminiKey();
  if (!key) {
    showGeminiKeySetup();
    return;
  }

  const btn = document.getElementById('metasAiBtn');
  const resultDiv = document.getElementById('metasAiResult');

  // Check cache (1 analysis per day)
  const hoje = new Date().toISOString().split('T')[0];
  const cacheKey = 'metas_ai_' + hoje;
  const cached = localStorage.getItem(cacheKey);
  if (cached && !btn.dataset.force) {
    resultDiv.innerHTML = renderAiResult(cached, hoje);
    return;
  }

  // Show loading
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Gemini analisando suas metas...';
  resultDiv.innerHTML = '';

  try {
    const { system, userMsg } = buildMetasPrompt();

    const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: system }] },
        contents: [{ role: 'user', parts: [{ text: userMsg }] }],
        generationConfig: { maxOutputTokens: 2048, temperature: 0.4 }
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error?.message || `Erro ${resp.status}`);
    }

    const data = await resp.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';

    if (!text) throw new Error('Resposta vazia do Gemini');

    // Cache for today
    localStorage.setItem(cacheKey, text);
    resultDiv.innerHTML = renderAiResult(text, hoje);
  } catch (e) {
    console.error('Gemini error:', e);
    resultDiv.innerHTML = `<div style="color:var(--pri-alta);font-size:0.8rem;padding:0.5rem">Erro ao consultar Gemini: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.dataset.force = '';
    btn.innerHTML = '🧠 Análise IA das Metas';
  }
}

function renderAiResult(text, date) {
  // Clean markdown artifacts if any
  let html = text
    .replace(/```html?\n?/g, '').replace(/```/g, '')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*$)/gm, '<h4>$1</h4>')
    .replace(/^- (.*$)/gm, '<li>$1</li>');

  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

  const formatted = new Date(date + 'T12:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'long' });

  return `<div class="metas-ai-result">
    <div class="metas-ai-result-header">
      <span>🧠</span>
      <span class="ai-label">Coaching IA — Gemini</span>
      <span class="ai-date">${formatted}</span>
      <button onclick="forceRefreshAi()" style="margin-left:0.3rem;background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:0.75rem" title="Atualizar análise">↻</button>
    </div>
    <div class="metas-ai-body">${html}</div>
  </div>`;
}

function forceRefreshAi() {
  const hoje = new Date().toISOString().split('T')[0];
  localStorage.removeItem('metas_ai_' + hoje);
  const btn = document.getElementById('metasAiBtn');
  if (btn) { btn.dataset.force = '1'; }
  callGeminiForMetas();
}

function showGeminiKeySetup() {
  const resultDiv = document.getElementById('metasAiResult');
  resultDiv.innerHTML = `<div class="metas-ai-key-setup">
    <label>Chave API do Gemini (gratuita — <a href="https://aistudio.google.com/apikey" target="_blank" style="color:var(--amber)">obter aqui</a>)</label>
    <input type="password" id="geminiKeyInput" placeholder="AIzaSy..." value="${getGeminiKey()}">
    <div class="key-actions">
      <button class="metas-ai-key-save" onclick="saveGeminiKey()">Salvar</button>
      <button class="metas-ai-key-cancel" onclick="document.getElementById('metasAiResult').innerHTML=''">Cancelar</button>
    </div>
  </div>`;
}

function saveGeminiKey() {
  const key = document.getElementById('geminiKeyInput').value.trim();
  if (!key) return;
  localStorage.setItem('gemini_api_key', key);
  document.getElementById('metasAiResult').innerHTML = '<div style="color:var(--amber);font-size:0.8rem;padding:0.3rem">Chave salva! Clique em "Análise IA" para gerar.</div>';
}

// ========== PATCH: renderReview to call renderHeatmap365 ==========
const _originalRenderReview = renderReview;
renderReview = function() {
  _originalRenderReview();
  renderHeatmap365();
};

// ========== FEATURE: AI COACHING WIDGET ==========

function generateCoachingInsight() {
  const hoje = new Date().toISOString().split('T')[0];
  const cacheKey = 'coaching_' + hoje;
  const dismissKey = 'coaching_dismiss_' + hoje;

  // Dismissed for today
  if (localStorage.getItem(dismissKey)) return null;

  // Already generated today — use cached
  const cached = localStorage.getItem(cacheKey);
  if (cached) return cached;

  // Analyze tasks to generate insight
  const hojeDate = new Date();
  const startOfWeek = new Date(hojeDate);
  startOfWeek.setDate(hojeDate.getDate() - hojeDate.getDay() + 1); // Monday
  const weekStart = startOfWeek.toISOString().split('T')[0];

  const pendentes = tasks.filter(t => t.status !== 'concluida');
  const overdue = tasks.filter(t => t.prazo && t.prazo < hoje && t.status !== 'concluida');
  const weekTasks = tasks.filter(t => t.created_at >= weekStart || (t.prazo && t.prazo >= weekStart));
  const weekCompleted = weekTasks.filter(t => t.status === 'concluida');
  const weekTotal = weekTasks.length;
  const completionRate = weekTotal > 0 ? Math.round((weekCompleted.length / weekTotal) * 100) : 0;

  // Count categories
  const catCount = {};
  pendentes.forEach(t => { catCount[t.categoria] = (catCount[t.categoria] || 0) + 1; });
  const totalPendentes = pendentes.length;
  let dominantCat = null, dominantPct = 0;
  for (const [cat, count] of Object.entries(catCount)) {
    const pct = Math.round((count / totalPendentes) * 100);
    if (pct > dominantPct) { dominantPct = pct; dominantCat = cat; }
  }

  // Personal tasks this week
  const pessoalWeek = weekTasks.filter(t => t.categoria === 'Pessoal');

  // Evening tasks (after 18h)
  const withTime = pendentes.filter(t => t.horario);
  const eveningTasks = withTime.filter(t => parseInt(t.horario) >= 18);
  const eveningPct = withTime.length > 0 ? Math.round((eveningTasks.length / withTime.length) * 100) : 0;

  // Streak (from gamification bar if available)
  const streakEl = document.querySelector('.streak-num');
  const streak = streakEl ? parseInt(streakEl.textContent) || 0 : 0;

  // Pick the most relevant insight
  let insight = null;

  if (completionRate > 80 && weekCompleted.length >= 3) {
    insight = 'Semana excelente! <strong>' + weekCompleted.length + ' tarefas concluídas</strong>. Continue assim! \uD83D\uDCAA';
  } else if (overdue.length >= 3) {
    insight = 'Você tem <strong>' + overdue.length + ' tarefas atrasadas</strong>. Que tal reservar 30min agora para resolver as mais rápidas?';
  } else if (pessoalWeek.length === 0) {
    insight = 'Essa semana não tem nenhuma tarefa pessoal. <strong>Cuidar de você também é produtividade.</strong>';
  } else if (streak > 3) {
    insight = '\uD83D\uDD25 <strong>' + streak + ' dias consecutivos!</strong> Você está construindo um hábito poderoso.';
  } else if (dominantPct > 70 && dominantCat && totalPendentes >= 4) {
    const outraCat = dominantCat === 'Trabalho' ? 'Pessoal' : (dominantCat === 'Pessoal' ? 'Trabalho' : 'Pessoal');
    insight = 'Suas tarefas estão <strong>' + dominantPct + '% concentradas em ' + dominantCat + '</strong>. Não esqueça de ' + outraCat + '!';
  } else if (eveningPct > 50 && withTime.length >= 3) {
    insight = 'Muitas tarefas à noite. <strong>Tente mover as mais pesadas para a manhã</strong> quando a energia é maior.';
  } else if (completionRate < 50 && weekTotal >= 4) {
    insight = 'Taxa de conclusão baixa (<strong>' + completionRate + '%</strong>). Tente decompor tarefas grandes em menores.';
  } else if (overdue.length > 0) {
    insight = 'Você tem <strong>' + overdue.length + ' tarefa' + (overdue.length > 1 ? 's' : '') + ' atrasada' + (overdue.length > 1 ? 's' : '') + '</strong>. Foca nelas primeiro!';
  }

  if (insight) {
    localStorage.setItem(cacheKey, insight);
  }
  return insight;
}

function renderCoachingCard() {
  const insight = generateCoachingInsight();
  if (!insight) return '';

  return '<div class="coaching-card" id="coachingCard">'
    + '<div class="coaching-header">'
    + '<span class="coaching-icon">\uD83E\uDDE0</span>'
    + '<span class="coaching-label">Coaching IA</span>'
    + '<button class="coaching-dismiss" onclick="dismissCoaching()" title="Dispensar">\u2715</button>'
    + '</div>'
    + '<div class="coaching-text">' + insight + '</div>'
    + '</div>';
}

function dismissCoaching() {
  const hoje = new Date().toISOString().split('T')[0];
  localStorage.setItem('coaching_dismiss_' + hoje, '1');
  const card = document.getElementById('coachingCard');
  if (card) card.remove();
}

