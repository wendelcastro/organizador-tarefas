// ========================================================================
// Variáveis compartilhadas (declaradas aqui, usadas em todos os módulos)
// ========================================================================
let editingTaskId = null;
let _confirmResolve = null;
let todayViewMode = 'list';
let bulkMode = false;
let selectedTasks = new Set();
let gamification = { xp: 0, level: 1, title: 'Iniciante', streak: 0, streakRecord: 0 };
let gamificationEnabled = true;
let draggedTaskId = null;
let reviewWeekOffset = 0;
let subcategoryFilter = null;
let pomodoroState = null; // inicializado em features-2.js
let energyData = { manha: 0, tarde: 0, noite: 0 };
let timeblockSelectedDate = new Date().toISOString().split('T')[0];
let metasQuarterFilter = 'current';
let userProfile = null;
let finTransacoes = [];
let finOrcamentos = [];
let finMetas = [];
let finScope = 'month';
let subtaskCache = {};
let searchTimeout = null;
let attachmentContentCache = {};
let deferredPrompt = null;
let currentOnboardingStep = 0;
let _onboardingScrollHandler = null;
let _onboardingResizeHandler = null;

// ========== SEGURANCA: escapeHtml ==========
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

// ========== SUPABASE CONNECTION ==========
// A anon key abaixo e PUBLICA por design (Supabase client-side).
// A seguranca real e feita via Row Level Security (RLS) no banco.
// NUNCA coloque a service_role key aqui.
const SUPABASE_URL = 'https://vhfuthaqonzuasgpbcrg.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoZnV0aGFxb256dWFzZ3BiY3JnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2ODk4OTgsImV4cCI6MjA4OTI2NTg5OH0.uJgJL-qrJtPqGUCWMO3e1a1JwudGvfUab4FxNC8SsBM';
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// ========== AUTH SYSTEM ==========
let currentUser = null;
let appInitialized = false;

async function checkAuth() {
  const { data: { session } } = await sb.auth.getSession();
  if (session) {
    currentUser = session.user;
    showApp();
  } else {
    showAuthScreen();
  }
}

sb.auth.onAuthStateChange((event, session) => {
  try {
    if (event === 'PASSWORD_RECOVERY') {
      currentUser = session?.user || null;
      showChangePassword();
      return;
    }
    if (event === 'SIGNED_IN' && session) {
      currentUser = session.user;
      showApp();
    } else if (event === 'TOKEN_REFRESHED' && session) {
      currentUser = session.user;
    } else if (event === 'SIGNED_OUT') {
      currentUser = null;
      showAuthScreen();
    }
  } catch(e) {
    console.error('onAuthStateChange erro:', e);
  }
});

async function showApp() {
  document.getElementById('authScreen').classList.add('hidden');
  document.getElementById('mainApp').classList.remove('auth-hidden');
  // Carregar perfil (role) antes de inicializar o app
  await loadUserProfile();
  if (!appInitialized) {
    appInitialized = true;
    initApp();
  }
}

function showAuthScreen() {
  document.getElementById('mainApp').classList.add('auth-hidden');
  document.getElementById('authScreen').classList.remove('hidden');
}

function _hideAllAuthForms() {
  ['authLogin','authRegister','authConfirm','authForgotPassword','authChangePassword'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

function showAuthLogin() {
  _hideAllAuthForms();
  document.getElementById('authLogin').style.display = 'block';
  document.getElementById('loginError').textContent = '';
}

function showAuthRegister() {
  _hideAllAuthForms();
  document.getElementById('authRegister').style.display = 'block';
  document.getElementById('registerError').textContent = '';
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');
  errEl.textContent = '';
  btn.disabled = true;
  btn.textContent = 'Entrando...';

  try {
    const { error } = await sb.auth.signInWithPassword({ email, password });

    if (error) {
      if (error.message.includes('Email not confirmed')) {
        errEl.textContent = 'Email ainda não confirmado. Verifique sua caixa de entrada.';
      } else if (error.message.includes('Invalid login')) {
        errEl.textContent = 'Email ou senha incorretos.';
      } else {
        errEl.textContent = error.message;
      }
    }
  } catch(ex) {
    console.error('handleLogin erro:', ex);
    errEl.textContent = 'Erro ao conectar. Tente novamente. (' + (ex?.message || '') + ')';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Entrar';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const inviteCode = document.getElementById('registerInviteCode').value.trim().toUpperCase();
  const email = document.getElementById('registerEmail').value;
  const password = document.getElementById('registerPassword').value;
  const confirm = document.getElementById('registerPasswordConfirm').value;
  const errEl = document.getElementById('registerError');
  const btn = document.getElementById('registerBtn');

  if (!inviteCode || inviteCode.length < 4) {
    errEl.textContent = 'Código de convite é obrigatório. Peça ao administrador.';
    return;
  }

  if (password !== confirm) {
    errEl.textContent = 'As senhas não coincidem.';
    return;
  }

  errEl.textContent = '';
  btn.disabled = true;
  btn.textContent = 'Validando convite...';

  // 1) Validar código de convite via RPC (não expõe a lista de convites — ver migration 021)
  try {
    const { data: conviteValido, error: cErr } = await sb
      .rpc('validar_convite', { p_codigo: inviteCode });

    if (cErr || !conviteValido) {
      btn.disabled = false;
      btn.textContent = 'Criar conta';
      errEl.textContent = 'Código de convite inválido, já usado ou expirado. Peça um novo ao administrador.';
      return;
    }

    // 2) Criar conta no Supabase Auth
    btn.textContent = 'Criando conta...';
    const { data, error } = await sb.auth.signUp({ email, password });
    btn.disabled = false;
    btn.textContent = 'Criar conta';

    if (error) {
      if (error.message.includes('already registered') || error.message.includes('already been registered')) {
        errEl.textContent = 'Este email já está cadastrado. Faça login.';
      } else {
        errEl.textContent = error.message;
      }
      return;
    }
    if (data?.user?.identities?.length === 0) {
      errEl.textContent = 'Este email já está cadastrado. Faça login.';
      return;
    }

    // 3) Marcar convite como usado (por código; a policy convites_usar valida ativo/não-usado/prazo)
    if (data?.user?.id) {
      await sb.from('codigos_convite')
        .update({ usado_por: data.user.id, usado_em: new Date().toISOString(), ativo: false })
        .eq('codigo', inviteCode);

      // Salvar o código usado no perfil (o trigger da 016 já criou o perfil)
      await sb.from('perfis_usuario')
        .update({ codigo_convite_usado: inviteCode })
        .eq('user_id', data.user.id);
    }

    document.getElementById('authLogin').style.display = 'none';
    document.getElementById('authRegister').style.display = 'none';
    document.getElementById('authConfirm').style.display = 'block';
  } catch(ex) {
    btn.disabled = false;
    btn.textContent = 'Criar conta';
    errEl.textContent = 'Erro ao validar convite. Tente novamente.';
    console.error('handleRegister:', ex);
  }
}

// ========== ESQUECI MINHA SENHA ==========
function showForgotPassword() {
  _hideAllAuthForms();
  document.getElementById('authForgotPassword').style.display = 'block';
  document.getElementById('forgotError').textContent = '';
  document.getElementById('forgotSuccess').style.display = 'none';
}

async function handleForgotPassword(e) {
  e.preventDefault();
  const email = document.getElementById('forgotEmail').value;
  const errEl = document.getElementById('forgotError');
  const successEl = document.getElementById('forgotSuccess');
  const btn = document.getElementById('forgotBtn');

  errEl.textContent = '';
  successEl.style.display = 'none';
  btn.disabled = true;
  btn.textContent = 'Enviando...';

  const { error } = await sb.auth.resetPasswordForEmail(email, {
    redirectTo: window.location.origin + window.location.pathname
  });

  btn.disabled = false;
  btn.textContent = 'Enviar link de recuperação';

  if (error) {
    errEl.textContent = error.message;
  } else {
    successEl.textContent = 'Email enviado! Verifique sua caixa de entrada e clique no link para redefinir sua senha.';
    successEl.style.display = 'block';
  }
}

// ========== ALTERAR SENHA (logado ou via link de recuperação) ==========
let _changePasswordFromApp = false; // marca se veio do app logado ou do recovery

function showChangePassword() {
  // Se estava logado no app, marca para saber que "cancelar" volta pro app
  _changePasswordFromApp = !!currentUser && appInitialized;

  const authScreen = document.getElementById('authScreen');
  const mainApp = document.getElementById('mainApp');
  authScreen.classList.remove('hidden');
  mainApp.classList.add('auth-hidden');

  _hideAllAuthForms();
  document.getElementById('authChangePassword').style.display = 'block';
  document.getElementById('changePasswordError').textContent = '';
  document.getElementById('changePasswordSuccess').style.display = 'none';
}

function cancelChangePassword() {
  if (_changePasswordFromApp && currentUser) {
    // Voltar para o dashboard
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('auth-hidden');
  } else {
    // Voltar para login
    showAuthLogin();
  }
}

async function handleChangePassword(e) {
  e.preventDefault();
  const newPw = document.getElementById('newPassword').value;
  const confirmPw = document.getElementById('newPasswordConfirm').value;
  const errEl = document.getElementById('changePasswordError');
  const successEl = document.getElementById('changePasswordSuccess');
  const btn = document.getElementById('changePasswordBtn');

  if (newPw !== confirmPw) {
    errEl.textContent = 'As senhas não coincidem.';
    return;
  }

  errEl.textContent = '';
  successEl.style.display = 'none';
  btn.disabled = true;
  btn.textContent = 'Alterando...';

  const { error } = await sb.auth.updateUser({ password: newPw });

  btn.disabled = false;
  btn.textContent = 'Alterar senha';

  if (error) {
    errEl.textContent = error.message;
  } else {
    successEl.textContent = 'Senha alterada com sucesso!';
    successEl.style.display = 'block';
    setTimeout(() => {
      if (currentUser) {
        document.getElementById('authScreen').classList.add('hidden');
        document.getElementById('mainApp').classList.remove('auth-hidden');
      } else {
        showAuthLogin();
      }
    }, 2000);
  }
}

async function handleLogout() {
  if (!confirm('Deseja sair da sua conta?')) return;
  await sb.auth.signOut();
  currentUser = null;
  userProfile = null;
  appInitialized = false;
  tasks = [];
  calendarEvents = [];
  showAuthScreen();
}

// ========== VINCULAR TELEGRAM ==========
async function vincularTelegram() {
  if (!currentUser) { alert('Faça login primeiro.'); return; }

  // Gerar código de 8 caracteres com CSPRNG (M3: Math.random é previsível)
  const _alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sem 0/O/1/I ambíguos
  const _bytes = new Uint8Array(8);
  crypto.getRandomValues(_bytes);
  const codigo = Array.from(_bytes, b => _alfabeto[b % _alfabeto.length]).join('');

  try {
    const headers = await getAuthHeaders();
    headers['Content-Type'] = 'application/json';
    headers['Prefer'] = 'return=representation';

    const res = await fetch(`${SUPABASE_URL}/rest/v1/codigos_vinculacao`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        codigo,
        user_id: currentUser.id,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      alert('Erro ao gerar código: ' + err);
      return;
    }

    // Mostrar modal com o código
    const html = `
      <div style="position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;z-index:9999" onclick="this.remove()">
        <div style="background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius);padding:2rem;max-width:420px;width:90%;text-align:center" onclick="event.stopPropagation()">
          <div style="font-size:2.5rem;margin-bottom:0.5rem">🔗</div>
          <h2 style="font-family:var(--font-display);font-weight:600;letter-spacing:-0.01em;font-size:1.6rem;color:var(--text-primary);margin-bottom:0.5rem">Vincular Telegram</h2>
          <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:1.2rem">Copie o código abaixo e envie no bot do Telegram</p>

          <div style="background:var(--bg-glass);border:1px dashed var(--amber);border-radius:0.75rem;padding:1rem;margin-bottom:1.2rem">
            <div style="font-family:monospace;font-size:2rem;font-weight:700;color:var(--amber);letter-spacing:0.3em">${codigo}</div>
            <div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.3rem">Expira em 15 minutos</div>
          </div>

          <div style="text-align:left;font-size:0.82rem;color:var(--text-secondary);line-height:1.6;margin-bottom:1.2rem">
            <strong style="color:var(--amber)">Passo a passo:</strong><br>
            1. Abra o bot no Telegram<br>
            2. Digite: <code style="background:var(--bg-glass);padding:2px 6px;border-radius:4px;color:var(--amber)">/vincular ${codigo}</code><br>
            3. Pronto! Suas mensagens vão para esta conta
          </div>

          <button onclick="navigator.clipboard.writeText('/vincular ${codigo}');this.textContent='✓ Copiado'" style="background:var(--amber);color:var(--bg-deep);border:none;padding:0.6rem 1.2rem;border-radius:0.6rem;font-family:inherit;font-weight:600;cursor:pointer;margin-right:0.5rem">Copiar comando</button>
          <button onclick="this.closest('[style*=fixed]').remove()" style="background:var(--bg-glass);color:var(--text-secondary);border:1px solid var(--border-subtle);padding:0.6rem 1.2rem;border-radius:0.6rem;font-family:inherit;cursor:pointer">Fechar</button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
  } catch(e) {
    alert('Erro: ' + e.message);
  }
}

// Helper: get auth headers for direct fetch calls
async function getAuthHeaders() {
  const { data: { session } } = await sb.auth.getSession();
  const headers = { 'apikey': SUPABASE_KEY };
  if (session?.access_token) {
    headers['Authorization'] = 'Bearer ' + session.access_token;
  }
  return headers;
}

// ========== CONFIG ==========
const CATEGORY_COLORS = {
  'Trabalho': 'var(--cat-trabalho)',
  'Consultoria': 'var(--cat-consultoria)',
  'Grupo Ser': 'var(--cat-grupo-ser)',
  'Pessoal': 'var(--cat-pessoal)'
};
const CATEGORY_BG = {
  'Trabalho': 'rgba(24,69,96,0.10)',      /* slate-blue */
  'Consultoria': 'rgba(20,108,169,0.10)', /* teal-blue */
  'Grupo Ser': 'rgba(132,46,32,0.10)',    /* burgundy */
  'Pessoal': 'rgba(76,175,80,0.12)'       /* success green */
};
const PRIORITY_COLORS = { 'alta': 'var(--pri-alta)', 'media': 'var(--pri-media)', 'baixa': 'var(--pri-baixa)' };
const PRIORITY_LABELS = { 'alta': 'Alta', 'media': 'Média', 'baixa': 'Baixa' };

// ========== MEETING DETECTION ==========
function detectMeetingPlatform(url) {
  if (!url) return null;
  if (url.includes('zoom.us') || url.includes('zoom.com')) return { type: 'zoom', label: 'Zoom', color: '#2d8cff' };
  if (url.includes('meet.google.com')) return { type: 'meet', label: 'Google Meet', color: '#34a853' };
  if (url.includes('teams.microsoft.com') || url.includes('teams.live.com')) return { type: 'teams', label: 'Teams', color: '#6264a7' };
  if (url.startsWith('http')) return { type: 'generic', label: 'Reunião online', color: '#999' };
  return null;
}

function getMeetingBadgeHTML(url) {
  const platform = detectMeetingPlatform(url);
  if (!platform) return '';
  const icon = '<svg class="meeting-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15.5 10l4.72-3.36a1 1 0 011.78.63v9.46a1 1 0 01-1.78.63L15.5 14"/><rect x="2" y="6" width="13.5" height="12" rx="2"/></svg>';
  return `<a href="${url}" target="_blank" rel="noopener" class="meeting-badge ${platform.type}" onclick="event.stopPropagation()">${icon} ${platform.label}</a>`;
}

// ========== DATA ==========
let tasks = [];
let calendarEvents = [];
let calendarConnections = { google: false, microsoft: false };
let currentFilters = { category: 'all', priority: 'all', status: 'all', _special: null };
let currentSort = 'smart'; // smart | newest | oldest | deadline_asc | deadline_desc | priority
let statsScope = 'week'; // week | all
// Em "Todas", por default mostramos só os últimos 30 dias para não poluir.
// Usuário pode alternar via botão "Ver tudo". Persistido em localStorage.
let tasksRangeDays = Number(localStorage.getItem('tasksRangeDays') || 30); // 30 ou 0 (tudo)

// ========== SUPABASE: CARREGAR EVENTOS DO CALENDARIO ==========
async function loadCalendarEvents() {
  try {
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - start.getDay());
    const end = new Date(start);
    end.setDate(end.getDate() + 21);

    const startStr = start.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];

    const headers = await getAuthHeaders();
    const uid = currentUser?.id;
    if (!uid) { calendarEvents = []; return; }
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/eventos_calendario?user_id=eq.${uid}&dia=gte.${startStr}&dia=lte.${endStr}&order=data_inicio.asc`,
      { headers }
    );
    if (res.ok) {
      calendarEvents = await res.json();
      console.log(`Loaded ${calendarEvents.length} calendar events`);
    }
  } catch (e) {
    console.error('Error loading calendar events:', e);
    calendarEvents = [];
  }
}

async function checkCalendarConnections() {
  try {
    const headers = await getAuthHeaders();
    const uid = currentUser?.id;
    if (!uid) { calendarConnections = { google:false, microsoft:false }; return; }
    // Segurança (H2): trazer só a coluna `chave`, NUNCA o `valor` (que contém
    // os refresh tokens OAuth). O frontend só precisa saber se está conectado.
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/configuracoes?user_id=eq.${uid}&chave=in.(google_calendar_tokens,microsoft_calendar_tokens)&select=chave`,
      { headers }
    );
    if (res.ok) {
      const data = await res.json();
      calendarConnections = {
        google: data.some(d => d.chave === 'google_calendar_tokens'),
        microsoft: data.some(d => d.chave === 'microsoft_calendar_tokens')
      };
    }
  } catch(e) {
    calendarConnections = { google: false, microsoft: false };
  }
}

function renderEventCard(ev, delay) {
  const provider = ev.provider || 'google';
  const timeStr = ev.all_day ? 'Dia todo' : `${ev.horario_inicio || '--:--'} - ${ev.horario_fim || '--:--'}`;
  const badge = `<span class="event-badge ${provider}">${provider === 'microsoft' ? 'Teams' : 'Google'}</span>`;
  let meetLink = '';
  if (ev.meeting_link) {
    const platform = ev.meeting_platform || 'generic';
    meetLink = `<a href="${ev.meeting_link}" target="_blank" class="event-meeting-link ${platform}" onclick="event.stopPropagation()">Entrar na reunião</a>`;
  }
  let meta = `<span>${ev.local_evento || provider.charAt(0).toUpperCase() + provider.slice(1)}</span>`;

  return `<div class="today-event-card ${provider}" style="animation-delay:${delay || 0}s">
    <div class="today-event-time">${timeStr}</div>
    <div class="today-event-info">
      <div class="today-event-title">${escapeHtml(ev.titulo)} ${badge}</div>
      <div class="today-event-meta">${meta}</div>
      ${meetLink}
    </div>
  </div>`;
}

function renderCalendarEvent(ev) {
  const provider = ev.provider || 'google';
  const timeStr = ev.all_day ? 'Dia todo' : (ev.horario_inicio || '');
  const badge = `<span class="event-badge ${provider}" style="font-size:0.45rem">${provider === 'microsoft' ? 'Teams' : 'Google'}</span>`;

  return `<div class="calendar-event ${provider}" data-event-id="${ev.id}">
    <div class="calendar-task-content">
      <span class="calendar-task-title">${escapeHtml(ev.titulo)} ${badge}</span>
      ${timeStr ? '<span class="calendar-task-time">' + timeStr + '</span>' : ''}
    </div>
  </div>`;
}

// ========== SUPABASE: CARREGAR TAREFAS ==========
async function loadTasks() {
  if (!currentUser) { tasks = []; renderTasks(); return; }
  let q = sb
    .from('tarefas')
    .select('*')
    .eq('user_id', currentUser.id)
    .order('created_at', { ascending: false });
  // Filtro de janela de tempo: 30 dias por padrão em "Todas"
  // Inclui: criadas nos últimos N dias OU não concluídas OU concluídas nos últimos N dias
  if (tasksRangeDays && tasksRangeDays > 0) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - tasksRangeDays);
    const cutoffStr = cutoff.toISOString();
    q = q.or(`created_at.gte.${cutoffStr},status.neq.concluida,updated_at.gte.${cutoffStr}`);
  }
  const { data, error } = await q;

  if (error) {
    console.error('Erro ao carregar tarefas:', error);
    document.getElementById('taskList').innerHTML =
      '<div class="empty-state"><p>Erro ao conectar ao banco. Verifique o console.</p></div>';
    return;
  }

  // Converter formato do banco para formato do dashboard
  tasks = (data || []).map(t => ({
    ...t,
    horario: t.horario ? t.horario.substring(0, 5) : '', // "14:00:00" -> "14:00"
  }));

  renderTasks();
  renderCalendar();
  renderToday();
  loadHabitLog();
}

// ========== HÁBITOS (tarefas diárias com log por dia) ==========
// habitLogToday: Set com tarefa_id dos hábitos já concluídos HOJE
// habitStats: { tarefa_id: { streak, feitos30d } }
let habitLogToday = new Set();
let habitStats = {};

function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

async function loadHabitLog() {
  habitLogToday = new Set();
  habitStats = {};
  if (!currentUser) return;
  try {
    const hoje = todayStr();
    // Conclusões de hoje
    const { data: hojeData } = await sb.from('tarefas_diarias_log')
      .select('tarefa_id')
      .eq('user_id', currentUser.id)
      .eq('data', hoje);
    if (hojeData) hojeData.forEach(r => habitLogToday.add(String(r.tarefa_id)));

    // Últimos 30 dias — para calcular streak e feitos30d
    const dataInicio = new Date(); dataInicio.setDate(dataInicio.getDate() - 29);
    const startStr = dataInicio.toISOString().split('T')[0];
    const { data: mes } = await sb.from('tarefas_diarias_log')
      .select('tarefa_id,data')
      .eq('user_id', currentUser.id)
      .gte('data', startStr)
      .order('data', { ascending: false });
    if (mes) {
      const porTarefa = {};
      mes.forEach(r => {
        const k = String(r.tarefa_id);
        if (!porTarefa[k]) porTarefa[k] = new Set();
        porTarefa[k].add(r.data);
      });
      Object.keys(porTarefa).forEach(k => {
        const datas = porTarefa[k];
        // streak: dias consecutivos terminando em hoje ou ontem
        let streak = 0;
        let cursor = new Date();
        // se não tem hoje, começa de ontem
        if (!datas.has(cursor.toISOString().split('T')[0])) {
          cursor.setDate(cursor.getDate() - 1);
        }
        while (datas.has(cursor.toISOString().split('T')[0])) {
          streak++;
          cursor.setDate(cursor.getDate() - 1);
        }
        habitStats[k] = { streak, feitos30d: datas.size };
      });
    }
  } catch(e) {
    console.warn('loadHabitLog erro:', e.message);
  }
}

function isHabitDoneToday(tarefaId) {
  return habitLogToday.has(String(tarefaId));
}

function getHabitStreak(tarefaId) {
  return (habitStats[String(tarefaId)] || {}).streak || 0;
}

async function toggleHabitToday(tarefaId) {
  if (!currentUser) return;
  const key = String(tarefaId);
  const hoje = todayStr();
  const task = tasks.find(t => String(t.id) === key);
  const jaFeito = habitLogToday.has(key);
  // Optimistic UI
  if (jaFeito) {
    habitLogToday.delete(key);
  } else {
    habitLogToday.add(key);
  }
  renderTasks();
  renderToday();

  try {
    if (jaFeito) {
      const { error } = await sb.from('tarefas_diarias_log')
        .delete()
        .eq('user_id', currentUser.id)
        .eq('tarefa_id', key)
        .eq('data', hoje);
      if (error) throw error;
      // Ajusta streak local
      if (habitStats[key]) {
        habitStats[key].streak = Math.max(0, habitStats[key].streak - 1);
        habitStats[key].feitos30d = Math.max(0, habitStats[key].feitos30d - 1);
      }
    } else {
      const { error } = await sb.from('tarefas_diarias_log').insert({
        tarefa_id: key,
        user_id: currentUser.id,
        data: hoje
      });
      if (error) throw error;
      // XP e streak
      if (task) {
        const xp = calculateXPForTask(task);
        await updateGamification(xp);
      }
      if (!habitStats[key]) habitStats[key] = { streak: 0, feitos30d: 0 };
      habitStats[key].streak += 1;
      habitStats[key].feitos30d += 1;
    }
  } catch(e) {
    // Rollback UI
    console.error('toggleHabitToday erro:', e);
    if (jaFeito) habitLogToday.add(key); else habitLogToday.delete(key);
    alert('Erro ao salvar conclusão do hábito.');
  }
  renderTasks();
  renderToday();
  renderCalendar();
  renderProgressRing();
}

// ========== SUPABASE: CRIAR TAREFA ==========
async function createTask(taskData) {
  if (!currentUser) { alert('Sessão expirada. Faça login novamente.'); return null; }
  const { data, error } = await sb
    .from('tarefas')
    .insert({ ...taskData, user_id: currentUser.id })
    .select()
    .single();

  if (error) {
    console.error('Erro ao criar tarefa:', error);
    alert('Erro ao salvar tarefa. Tente novamente.');
    return null;
  }
  return data;
}

// ========== SUPABASE: ATUALIZAR TAREFA ==========
async function updateTask(id, updates) {
  if (!currentUser) return false;
  const { error } = await sb
    .from('tarefas')
    .update(updates)
    .eq('id', id)
    .eq('user_id', currentUser.id);

  if (error) {
    console.error('Erro ao atualizar tarefa:', error);
    return false;
  }
  return true;
}

// ========== SUPABASE: EXCLUIR TAREFA ==========
async function removeTask(id) {
  if (!currentUser) return false;
  try {
    // Primeiro excluir subtarefas e anexos vinculados (caso CASCADE não esteja ativo)
    await sb.from('subtarefas').delete().eq('tarefa_id', id).eq('user_id', currentUser.id);
    await sb.from('anexos').delete().eq('tarefa_id', id).eq('user_id', currentUser.id);

    // Excluir a tarefa
    const { error } = await sb
      .from('tarefas')
      .delete()
      .eq('id', id)
      .eq('user_id', currentUser.id);

    if (error) {
      console.error('Erro ao excluir tarefa:', error.message, error.details, error.hint);
      alert('Erro ao excluir: ' + error.message);
      return false;
    }
    return true;
  } catch (e) {
    console.error('Exceção ao excluir tarefa:', e);
    alert('Erro ao excluir tarefa: ' + e.message);
    return false;
  }
}

// ========== SUPABASE: REALTIME ==========
// Quando QUALQUER coisa muda no banco (ex: bot do Telegram criou tarefa),
// o dashboard atualiza automaticamente — sem recarregar a pagina!
function setupRealtime() {
  sb.channel('tarefas-changes')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'tarefas' }, () => {
      loadTasks(); // Recarrega tudo quando algo muda
    })
    .subscribe();
}

// ========== HELPERS ==========
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  const months = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  return `${d.getDate()} ${months[d.getMonth()]}`;
}

function isOverdue(task) {
  if (task.status === 'concluida' || !task.prazo) return false;
  const today = new Date(); today.setHours(0,0,0,0);
  const prazo = new Date(task.prazo + 'T12:00:00'); prazo.setHours(0,0,0,0);
  return prazo < today;
}

function getWeekDays() {
  const today = new Date();
  const dow = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
  const days = [];
  const names = ['Seg','Ter','Qua','Qui','Sex','Sab','Dom'];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday); d.setDate(monday.getDate() + i);
    days.push({ name: names[i], number: d.getDate(), date: d.toISOString().split('T')[0], isToday: d.toDateString() === today.toDateString() });
  }
  return days;
}

function updateHeaderDate() {
  const now = new Date();
  const f = now.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
  document.getElementById('headerDate').textContent = f.charAt(0).toUpperCase() + f.slice(1);
}

// ========== STATS ==========
// ========== SCOPE (semana/tudo) ==========
function getWeekRange() {
  const today = new Date(); today.setHours(0,0,0,0);
  const dow = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return { start: monday.toISOString().split('T')[0], end: sunday.toISOString().split('T')[0] };
}

function isTaskInWeek(t) {
  const week = getWeekRange();
  // Tarefa com prazo na semana
  if (t.prazo && t.prazo >= week.start && t.prazo <= week.end) return true;
  // Tarefa criada na semana (sem prazo)
  if (!t.prazo && t.created_at) {
    const criada = t.created_at.split('T')[0];
    return criada >= week.start && criada <= week.end;
  }
  return false;
}

function getScopedTasks() {
  if (statsScope === 'all') return tasks;
  return tasks.filter(t => isTaskInWeek(t) || isOverdue(t));
}

function changeScope(scope) {
  statsScope = scope;
  document.querySelectorAll('.scope-btn').forEach(el => el.classList.toggle('active', el.dataset.scope === scope));
  updateStats();
  renderTasks();
}

// Alterna janela de "Todas" entre últimos 30 dias (default) e tudo
async function toggleRangeDays() {
  tasksRangeDays = tasksRangeDays === 0 ? 30 : 0;
  localStorage.setItem('tasksRangeDays', String(tasksRangeDays));
  const lbl = document.getElementById('rangeLabel');
  if (lbl) lbl.textContent = tasksRangeDays === 0 ? '📅 Tudo' : '📅 30 dias';
  await loadTasks();
}

function initRangeLabel() {
  const lbl = document.getElementById('rangeLabel');
  if (lbl) lbl.textContent = tasksRangeDays === 0 ? '📅 Tudo' : '📅 30 dias';
}

function updateStats() {
  const scoped = getScopedTasks();
  const total = scoped.length;
  const pending = scoped.filter(t => t.status !== 'concluida').length;
  const done = scoped.filter(t => t.status === 'concluida').length;
  const overdue = scoped.filter(t => isOverdue(t)).length;
  const meetings = scoped.filter(t => t.meeting_link && t.status !== 'concluida').length;

  document.getElementById('statTotal').textContent = total;
  document.getElementById('statPending').textContent = pending;
  document.getElementById('statDone').textContent = done;
  document.getElementById('statOverdue').textContent = overdue;

  document.getElementById('mStatTotal').textContent = total;
  document.getElementById('mStatPending').textContent = pending;
  document.getElementById('mStatDone').textContent = done;
  document.getElementById('mStatOverdue').textContent = overdue;
  document.getElementById('mStatMeetings').textContent = meetings;

  document.getElementById('countAll').textContent = total;
  document.getElementById('countTrabalho').textContent = scoped.filter(t => t.categoria === 'Trabalho').length;
  document.getElementById('countConsultoria').textContent = scoped.filter(t => t.categoria === 'Consultoria').length;
  document.getElementById('countGrupoSer').textContent = scoped.filter(t => t.categoria === 'Grupo Ser').length;
  document.getElementById('countPessoal').textContent = scoped.filter(t => t.categoria === 'Pessoal').length;

  // Banner de atrasadas
  const banner = document.getElementById('overdueBanner');
  if (overdue > 0) {
    banner.style.display = 'flex';
    document.getElementById('overdueBannerText').textContent =
      `Você tem ${overdue} tarefa${overdue > 1 ? 's' : ''} atrasada${overdue > 1 ? 's' : ''}! Revise seus prazos.`;
  } else {
    banner.style.display = 'none';
  }

  // Badge no botão Hoje (tarefas do dia + hábitos pendentes)
  const hoje = new Date().toISOString().split('T')[0];
  const todayTaskCount = tasks.filter(t => !t.eh_habito && t.prazo === hoje && t.status !== 'concluida').length;
  const todayHabitCount = tasks.filter(t => t.eh_habito && !isHabitDoneToday(t.id)).length;
  const todayCount = todayTaskCount + todayHabitCount;
  document.querySelectorAll('[data-view="today"]').forEach(btn => {
    let badge = btn.querySelector('.nav-badge');
    if (todayCount > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'nav-badge';
        btn.appendChild(badge);
      }
      badge.textContent = todayCount;
    } else if (badge) {
      badge.remove();
    }
  });
}

// ========== FILTERS ==========
function filterCategory(cat) {
  currentFilters.category = cat;
  currentFilters._special = null;
  document.querySelectorAll('.chip[data-category]').forEach(el => el.classList.toggle('active', el.dataset.category === cat));
  document.querySelectorAll('.category-item').forEach(el => el.classList.toggle('active', el.dataset.category === cat));
  document.querySelectorAll('.stat-card').forEach(el => el.classList.remove('stat-active'));
  switchView('tasks');
  renderTasks();
}

function filterPriority(pri) {
  currentFilters.priority = pri;
  currentFilters._special = null;
  document.querySelectorAll('.priority-item').forEach(el => el.classList.toggle('active', el.dataset.priority === pri));
  document.querySelectorAll('.stat-card').forEach(el => el.classList.remove('stat-active'));
  switchView('tasks');
  renderTasks();
}

// ========== SORT ==========
const SORT_LABELS = { smart: 'Inteligente', newest: 'Mais recentes', oldest: 'Mais antigas', deadline_asc: 'Prazo próximo', deadline_desc: 'Prazo distante', priority: 'Prioridade' };

function toggleSortMenu() {
  document.getElementById('sortMenu').classList.toggle('open');
}

function changeSort(sortKey) {
  currentSort = sortKey;
  document.getElementById('sortLabel').textContent = SORT_LABELS[sortKey];
  document.querySelectorAll('.sort-option').forEach(el => el.classList.toggle('active', el.dataset.sort === sortKey));
  document.getElementById('sortMenu').classList.remove('open');
  renderTasks();
}

// Fechar menu ao clicar fora
document.addEventListener('click', function(e) {
  const dd = document.getElementById('sortDropdown');
  if (dd && !dd.contains(e.target)) {
    document.getElementById('sortMenu').classList.remove('open');
  }
});

function filterStatus(status) {
  currentFilters.status = status;
  currentFilters._special = null;
  document.querySelectorAll('.status-tab').forEach(el => el.classList.toggle('active', el.dataset.status === status));
  document.querySelectorAll('.stat-card').forEach(el => el.classList.remove('stat-active'));
  renderTasks();
}

// Filtro rapido via stat cards (Total, Pendentes, Concluidas, Atrasadas, Reunioes)
function filterByStatCard(type) {
  // Resetar filtros
  currentFilters.category = 'all';
  currentFilters.priority = 'all';
  document.querySelectorAll('.chip[data-category]').forEach(el => el.classList.toggle('active', el.dataset.category === 'all'));
  document.querySelectorAll('.category-item').forEach(el => el.classList.toggle('active', el.dataset.category === 'all'));
  document.querySelectorAll('.priority-item').forEach(el => el.classList.toggle('active', el.dataset.priority === 'all'));

  if (type === 'all') {
    currentFilters.status = 'all';
  } else if (type === 'pendente') {
    currentFilters.status = 'pendente';
  } else if (type === 'concluida') {
    currentFilters.status = 'concluida';
  } else if (type === 'overdue' || type === 'meetings') {
    // Filtros especiais — usar status 'all' e filtrar no getFilteredTasks
    currentFilters.status = 'all';
    currentFilters._special = type;
  }

  // Atualizar visual das status tabs
  if (type !== 'overdue' && type !== 'meetings') {
    currentFilters._special = null;
    document.querySelectorAll('.status-tab').forEach(el => el.classList.toggle('active', el.dataset.status === (type === 'all' ? 'all' : type)));
  } else {
    document.querySelectorAll('.status-tab').forEach(el => el.classList.remove('active'));
  }

  // Destacar stat card ativo
  document.querySelectorAll('.stat-card').forEach(el => el.classList.remove('stat-active'));
  if (type === 'all') {
    document.querySelectorAll('.stat-card.total').forEach(el => el.classList.add('stat-active'));
  } else if (type === 'pendente') {
    document.querySelectorAll('.stat-card.pending').forEach(el => el.classList.add('stat-active'));
  } else if (type === 'concluida') {
    document.querySelectorAll('.stat-card.done').forEach(el => el.classList.add('stat-active'));
  } else if (type === 'overdue') {
    document.querySelectorAll('.stat-card.overdue').forEach(el => el.classList.add('stat-active'));
  } else if (type === 'meetings') {
    document.querySelectorAll('.stat-card.meetings').forEach(el => el.classList.add('stat-active'));
  }

  switchView('tasks');
  renderTasks();
}

function getFilteredTasks() {
  const scoped = getScopedTasks();
  return scoped.filter(t => {
    // Hábitos (tarefas diárias) NÃO aparecem em "Todas" — têm view própria
    if (t.eh_habito) return false;
    if (currentFilters.category !== 'all' && t.categoria !== currentFilters.category) return false;
    if (currentFilters.priority !== 'all' && t.prioridade !== currentFilters.priority) return false;
    if (currentFilters.status !== 'all' && t.status !== currentFilters.status) return false;
    // Filtros especiais dos stat cards
    if (currentFilters._special === 'overdue' && !isOverdue(t)) return false;
    if (currentFilters._special === 'meetings' && (!t.meeting_link || t.status === 'concluida')) return false;
    return true;
  });
}
