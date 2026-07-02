// ========== GAMIFICATION SYSTEM ==========
const LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6000, 10000];
const LEVEL_TITLES = [
  'Iniciante Organizado', 'Aprendiz Focado', 'Executor Consistente',
  'Gerente do Caos', 'Estrategista Digital', 'Mestre do Tempo',
  'Líder Produtivo', 'Arquiteto da Rotina', 'Guru da Organização', 'Professor Nível S'
];
gamification.title = LEVEL_TITLES[0];


function getLevelForXP(xp) {
  let lvl = 1;
  for (let i = LEVEL_THRESHOLDS.length - 1; i >= 0; i--) {
    if (xp >= LEVEL_THRESHOLDS[i]) { lvl = i + 1; break; }
  }
  return Math.min(lvl, 10);
}

function getXPForNextLevel(level) {
  if (level >= 10) return LEVEL_THRESHOLDS[9];
  return LEVEL_THRESHOLDS[level]; // level is 1-based, threshold index for next = level
}

function getXPForCurrentLevel(level) {
  return LEVEL_THRESHOLDS[Math.max(0, level - 1)];
}

async function loadGamification() {
  try {
    if (!currentUser) return;
    const { data, error } = await sb.from('gamificacao')
      .select('*')
      .eq('user_id', currentUser.id)
      .limit(1)
      .maybeSingle();
    if (error) throw error;
    if (data) {
      gamification.xp = data.xp_total || 0;
      gamification.streak = data.streak_atual || 0;
      gamification.streakRecord = data.streak_recorde || 0;
      gamification.level = getLevelForXP(gamification.xp);
      gamification.title = LEVEL_TITLES[gamification.level - 1];
    }
  } catch (e) {
    console.warn('Gamificacao: tabela nao encontrada ou erro. Usando localStorage fallback.', e.message);
    gamificationEnabled = false;
    const saved = localStorage.getItem('gamification');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        gamification = { ...gamification, ...parsed };
        gamification.level = getLevelForXP(gamification.xp);
        gamification.title = LEVEL_TITLES[gamification.level - 1];
      } catch (e2) { /* ignore */ }
    }
  }
  renderGamificationUI();
}

async function updateGamification(xpGained) {
  gamification.xp += xpGained;
  const oldLevel = gamification.level;
  gamification.level = getLevelForXP(gamification.xp);
  gamification.title = LEVEL_TITLES[gamification.level - 1];

  // Check streak
  await checkStreak();

  // Save
  if (gamificationEnabled && currentUser) {
    try {
      const { data: existing } = await sb.from('gamificacao')
        .select('id')
        .eq('user_id', currentUser.id)
        .limit(1)
        .maybeSingle();
      if (existing) {
        await sb.from('gamificacao').update({
          xp_total: gamification.xp, streak_atual: gamification.streak,
          streak_recorde: gamification.streakRecord, nivel: gamification.level,
          titulo: gamification.title, updated_at: new Date().toISOString()
        }).eq('id', existing.id).eq('user_id', currentUser.id);
      } else {
        await sb.from('gamificacao').insert({
          xp_total: gamification.xp, streak_atual: gamification.streak,
          streak_recorde: gamification.streakRecord, nivel: gamification.level,
          titulo: gamification.title, user_id: currentUser.id
        });
      }
    } catch (e) { console.warn('Erro ao salvar gamificacao no Supabase:', e.message); }
  }

  // Always save to localStorage as backup
  localStorage.setItem('gamification', JSON.stringify(gamification));

  // Show XP popup
  showXPPopup(xpGained);

  // Level up notification
  if (gamification.level > oldLevel) {
    setTimeout(() => alert('Nível ' + gamification.level + '! ' + gamification.title), 500);
  }

  renderGamificationUI();
}

function calculateDailyProgress() {
  const hoje = new Date().toISOString().split('T')[0];
  const todayTasks = tasks.filter(t => !t.eh_habito && t.prazo === hoje);
  const todayHabits = tasks.filter(t => t.eh_habito);
  const totalItems = todayTasks.length + todayHabits.length;
  if (totalItems === 0) return 0;
  const tasksDone = todayTasks.filter(t => t.status === 'concluida').length;
  const habitsDone = todayHabits.filter(t => isHabitDoneToday(t.id)).length;
  return Math.round(((tasksDone + habitsDone) / totalItems) * 100);
}

function renderProgressRing() {
  const pct = calculateDailyProgress();
  const circumference = 2 * Math.PI * 20; // r=20
  const offset = circumference - (pct / 100) * circumference;
  const fill = document.getElementById('progressRingFill');
  const text = document.getElementById('progressRingText');
  if (fill) fill.style.strokeDashoffset = offset;
  if (text) text.textContent = pct + '%';
}

function renderGamificationUI() {
  renderProgressRing();

  const streakEl = document.getElementById('streakCount');
  if (streakEl) streakEl.textContent = gamification.streak;

  const levelNum = document.getElementById('levelBadgeNum');
  const levelTitle = document.getElementById('levelBadgeTitle');
  if (levelNum) levelNum.textContent = gamification.level;
  if (levelTitle) levelTitle.textContent = gamification.title.split(' ').slice(0, 2).join(' ');

  const currentLevelXP = getXPForCurrentLevel(gamification.level);
  const nextLevelXP = getXPForNextLevel(gamification.level);
  const xpInLevel = gamification.xp - currentLevelXP;
  const xpNeeded = nextLevelXP - currentLevelXP;
  const pct = xpNeeded > 0 ? Math.min(100, Math.round((xpInLevel / xpNeeded) * 100)) : 100;

  const xpLabel = document.getElementById('xpLabel');
  const xpLevelLabel = document.getElementById('xpLevelLabel');
  const xpBarFill = document.getElementById('xpBarFill');
  if (xpLabel) xpLabel.textContent = gamification.xp + ' / ' + nextLevelXP + ' XP';
  if (xpLevelLabel) xpLevelLabel.textContent = 'Nível ' + gamification.level;
  if (xpBarFill) xpBarFill.style.width = pct + '%';
}

async function checkStreak() {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split('T')[0];
  const yesterdayTasks = tasks.filter(t => t.prazo === yesterdayStr);
  if (yesterdayTasks.length === 0) return; // no tasks yesterday, keep streak

  const done = yesterdayTasks.filter(t => t.status === 'concluida').length;
  const rate = done / yesterdayTasks.length;

  if (rate >= 0.7) {
    // Check if we already counted today
    const lastStreakDate = localStorage.getItem('lastStreakDate');
    const hoje = new Date().toISOString().split('T')[0];
    if (lastStreakDate !== hoje) {
      gamification.streak++;
      if (gamification.streak > gamification.streakRecord) {
        gamification.streakRecord = gamification.streak;
      }
      localStorage.setItem('lastStreakDate', hoje);
    }
  } else {
    gamification.streak = 0;
  }
}

function showXPPopup(xp) {
  const popup = document.createElement('div');
  popup.className = 'xp-popup';
  popup.textContent = '+' + xp + ' XP';
  popup.style.left = (window.innerWidth / 2 - 40) + 'px';
  popup.style.top = '120px';
  document.body.appendChild(popup);
  setTimeout(() => popup.remove(), 1600);
}

function calculateXPForTask(task) {
  let base = task.tempo_estimado_min || 30;
  // Bonus: completed before deadline
  if (task.prazo) {
    const hoje = new Date().toISOString().split('T')[0];
    if (hoje <= task.prazo) base = Math.round(base * 1.5);
  }
  // Bonus: alta prioridade
  if (task.prioridade === 'alta') base = Math.round(base * 1.25);
  return Math.max(5, Math.round(base));
}

// ========== DRAG & DROP ==========

function setupDragAndDrop() {
  // Status tabs as drop zones
  document.querySelectorAll('.status-tab').forEach(tab => {
    tab.addEventListener('dragover', handleDragOver);
    tab.addEventListener('dragleave', handleDragLeave);
    tab.addEventListener('drop', handleStatusDrop);
  });
}

function handleDragStart(e) {
  draggedTaskId = e.target.closest('.task-card')?.dataset.taskId || e.target.closest('.calendar-task')?.dataset.taskId || e.target.dataset.taskId;
  if (!draggedTaskId) return;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', draggedTaskId);
  setTimeout(() => {
    const card = e.target.closest('.task-card') || e.target.closest('.calendar-task') || e.target;
    card.classList.add('dragging');
  }, 0);
}

function handleDragEnd(e) {
  const card = e.target.closest('.task-card') || e.target.closest('.calendar-task') || e.target;
  card.classList.remove('dragging');
  draggedTaskId = null;
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

async function handleStatusDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const taskId = e.dataTransfer.getData('text/plain');
  if (!taskId) return;

  const statusMap = { 'all': null, 'pendente': 'pendente', 'em_andamento': 'em_andamento', 'concluida': 'concluida' };
  const newStatus = statusMap[e.currentTarget.dataset.status];
  if (!newStatus) return;

  const task = tasks.find(t => String(t.id) === String(taskId));
  if (!task || task.status === newStatus) return;

  const oldStatus = task.status;
  task.status = newStatus;
  renderTasks();
  renderToday();

  // Award XP if moved to concluida
  if (newStatus === 'concluida' && oldStatus !== 'concluida') {
    const xp = calculateXPForTask(task);
    await updateGamification(xp);
  }

  const ok = await updateTask(taskId, { status: newStatus });
  if (!ok) {
    task.status = oldStatus;
    renderTasks();
    renderToday();
  }
}

async function handleCalendarDrop(e, newDate) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const taskId = e.dataTransfer.getData('text/plain');
  if (!taskId) return;

  const task = tasks.find(t => String(t.id) === String(taskId));
  if (!task) return;

  const oldDate = task.prazo;
  task.prazo = newDate;
  renderCalendar();
  renderTasks();
  renderToday();

  const ok = await updateTask(taskId, { prazo: newDate });
  if (!ok) {
    task.prazo = oldDate;
    renderCalendar();
    renderTasks();
    renderToday();
  }
}

// ========== WEEK HISTORY ==========

function getWeekDaysForOffset(offset) {
  const today = new Date();
  today.setDate(today.getDate() + (offset * 7));
  const dow = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
  const days = [];
  const names = ['Seg','Ter','Qua','Qui','Sex','Sab','Dom'];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday); d.setDate(monday.getDate() + i);
    days.push({ name: names[i], number: d.getDate(), date: d.toISOString().split('T')[0], isToday: d.toDateString() === new Date().toDateString() });
  }
  return days;
}

function navigateWeek(dir) {
  reviewWeekOffset += dir;
  if (reviewWeekOffset > 0) reviewWeekOffset = 0; // don't go to future
  renderReview();
}

async function saveWeekSnapshot() {
  const weekDays = getWeekDaysForOffset(reviewWeekOffset);
  const weekStart = weekDays[0].date;
  const weekEnd = weekDays[6].date;
  const weekTasks = tasks.filter(t => t.prazo >= weekStart && t.prazo <= weekEnd);
  const total = weekTasks.length;
  const completed = weekTasks.filter(t => t.status === 'concluida').length;
  const rate = total > 0 ? Math.round((completed / total) * 100) : 0;
  const annotation = document.getElementById('weekAnnotation')?.value || '';

  const snapshot = {
    semana_inicio: weekStart, semana_fim: weekEnd,
    total_tarefas: total, concluidas: completed,
    taxa_conclusao: rate, anotacao: annotation,
    user_id: currentUser?.id
  };

  try {
    if (!currentUser) throw new Error('Usuário não autenticado');
    // Check if snapshot already exists for this week (do usuário atual)
    const { data: existing } = await sb.from('historico_semanal')
      .select('id')
      .eq('user_id', currentUser.id)
      .eq('semana_inicio', weekStart)
      .maybeSingle();
    if (existing) {
      await sb.from('historico_semanal').update(snapshot)
        .eq('id', existing.id)
        .eq('user_id', currentUser.id);
    } else {
      await sb.from('historico_semanal').insert(snapshot);
    }
    alert('Semana salva com sucesso!');
  } catch (e) {
    console.warn('Erro ao salvar snapshot semanal (tabela pode nao existir):', e.message);
    // Fallback: save to localStorage
    const key = 'weekSnapshot_' + weekStart;
    localStorage.setItem(key, JSON.stringify(snapshot));
    // Also save to history index
    const historyIndex = JSON.parse(localStorage.getItem('weekHistoryIndex') || '[]');
    if (!historyIndex.includes(weekStart)) {
      historyIndex.push(weekStart);
      historyIndex.sort().reverse();
      localStorage.setItem('weekHistoryIndex', JSON.stringify(historyIndex));
    }
    alert('Semana salva localmente!');
  }
  loadWeekHistoryList();
}

async function saveAnnotation(weekStart, text) {
  try {
    if (!currentUser) throw new Error('no user');
    const { data: existing } = await sb.from('historico_semanal')
      .select('id')
      .eq('user_id', currentUser.id)
      .eq('semana_inicio', weekStart)
      .maybeSingle();
    if (existing) {
      await sb.from('historico_semanal').update({ anotacao: text })
        .eq('id', existing.id)
        .eq('user_id', currentUser.id);
    }
  } catch (e) {
    const key = 'weekSnapshot_' + weekStart;
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      parsed.annotation = text;
      localStorage.setItem(key, JSON.stringify(parsed));
    }
  }
}

function saveCurrentWeek() {
  saveWeekSnapshot();
}

async function loadWeekAnnotation(weekStart) {
  try {
    if (!currentUser) throw new Error('no user');
    const { data } = await sb.from('historico_semanal')
      .select('anotacao')
      .eq('user_id', currentUser.id)
      .eq('semana_inicio', weekStart)
      .maybeSingle();
    if (data) return data.anotacao || '';
  } catch (e) {
    const key = 'weekSnapshot_' + weekStart;
    const saved = localStorage.getItem(key);
    if (saved) {
      try { return JSON.parse(saved).annotation || ''; } catch (e2) { /* ignore */ }
    }
  }
  return '';
}

async function loadWeekHistoryList() {
  let histories = [];
  try {
    if (!currentUser) throw new Error('no user');
    const { data, error } = await sb.from('historico_semanal')
      .select('*')
      .eq('user_id', currentUser.id)
      .order('semana_inicio', { ascending: false })
      .limit(10);
    if (!error && data) histories = data;
  } catch (e) {
    // Fallback: localStorage
    const historyIndex = JSON.parse(localStorage.getItem('weekHistoryIndex') || '[]');
    histories = historyIndex.map(ws => {
      const saved = localStorage.getItem('weekSnapshot_' + ws);
      return saved ? JSON.parse(saved) : null;
    }).filter(Boolean);
  }

  const container = document.getElementById('weekHistoryList');
  if (!container) return;
  if (histories.length === 0) {
    container.innerHTML = '<div style="font-size:0.75rem;color:var(--text-muted);padding:0.5rem 0">Nenhuma semana salva ainda.</div>';
    return;
  }

  container.innerHTML = '<h3 style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem">Histórico de semanas</h3>' +
    histories.map(h => {
      const rate = h.taxa_conclusao || 0;
      const rateColor = rate >= 70 ? 'var(--cat-pessoal)' : rate >= 40 ? 'var(--pri-media)' : 'var(--pri-alta)';
      return `<div class="history-card" onclick="navigateToWeek('${h.semana_inicio}')">
        <div class="history-card-header">
          <span class="history-card-period">${formatDate(h.semana_inicio)} — ${formatDate(h.semana_fim)}</span>
          <span class="history-card-rate" style="color:${rateColor}">${rate}%</span>
        </div>
        <div style="font-size:0.72rem;color:var(--text-secondary)">${h.concluidas || 0}/${h.total_tarefas || 0} concluídas</div>
        ${h.anotacao ? '<div class="history-card-note">' + escapeHtml(h.anotacao) + '</div>' : ''}
      </div>`;
    }).join('');
}

function navigateToWeek(weekStartDate) {
  // Calculate offset from current week
  const today = new Date();
  const dow = today.getDay();
  const currentMonday = new Date(today);
  currentMonday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1));
  currentMonday.setHours(0,0,0,0);
  const targetDate = new Date(weekStartDate + 'T00:00:00');
  const diffMs = targetDate.getTime() - currentMonday.getTime();
  const diffWeeks = Math.round(diffMs / (7 * 24 * 60 * 60 * 1000));
  reviewWeekOffset = diffWeeks;
  if (reviewWeekOffset > 0) reviewWeekOffset = 0;
  switchView('review');
  // Close search results if open
  var results = document.getElementById('searchResults');
  if (results) results.classList.remove('active');
  var searchInput = document.getElementById('globalSearch');
  if (searchInput) searchInput.value = '';
}

function highlightSearchTerm(text, query) {
  if (!text || !query) return text || '';
  var regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  return text.replace(regex, '<mark style="background:rgba(185,145,91,0.2);color:var(--amber);padding:0 2px;border-radius:2px">$1</mark>');
}

// ========== HABITS & SUBCATEGORIES ==========
const SUBCATEGORY_LABELS = {
  'academia': 'Academia', 'leitura': 'Leitura', 'corrida': 'Corrida',
  'beach_tennis': 'Beach Tennis', 'estudo': 'Estudo',
  'meditacao': 'Meditação', 'ingles': 'Inglês'
};

const SUBCATEGORY_ICONS = {
  'academia': '\uD83C\uDFCB', 'leitura': '\uD83D\uDCDA', 'corrida': '\uD83C\uDFC3',
  'beach_tennis': '\uD83C\uDFBE', 'estudo': '\uD83D\uDCDD',
  'meditacao': '\uD83E\uDDD8', 'ingles': '\uD83C\uDDFA\uD83C\uDDF8'
};


function toggleSubcategoryVisibility() {
  const catSelect = document.getElementById('inputCategory');
  const subField = document.getElementById('subcategoryField');
  if (catSelect && subField) {
    subField.classList.toggle('visible', catSelect.value === 'Pessoal');
  }
}

function getSubcategoryBadgeHTML(task) {
  if (!task.subcategoria) return '';
  const label = SUBCATEGORY_LABELS[task.subcategoria] || task.subcategoria;
  const icon = SUBCATEGORY_ICONS[task.subcategoria] || '';
  return '<span class="subcategory-badge">' + (icon ? icon + ' ' : '') + label + '</span>';
}

function getTipoBadgeHTML(task) {
  if (!task.tipo || task.tipo === 'tarefa') return '';
  if (task.tipo === 'rotina') return '<span class="routine-badge">&#128260; Rotina</span>';
  if (task.tipo === 'habito') return '<span class="habit-indicator">&#9889; Hábito</span>';
  return '';
}

async function renderHabitTracker() {
  const container = document.getElementById('habitTrackerSection');
  if (!container) return;

  const weekDays = getWeekDaysForOffset(reviewWeekOffset);
  const weekStart = weekDays[0].date;
  const weekEnd = weekDays[6].date;

  let hasData = false;
  let html = '<div class="review-card" style="margin-top:0.75rem"><h3>Rastreador de hábitos</h3>';

  // ======== Seção 1: hábitos de verdade (eh_habito=true) via log diário ========
  const habitos = tasks.filter(t => t.eh_habito);
  if (habitos.length > 0 && currentUser) {
    hasData = true;
    // Busca log da semana
    let logSemana = [];
    try {
      const { data } = await sb.from('tarefas_diarias_log')
        .select('tarefa_id,data')
        .eq('user_id', currentUser.id)
        .gte('data', weekStart)
        .lte('data', weekEnd);
      if (data) logSemana = data;
    } catch(e) { console.warn('habit tracker log:', e.message); }

    const logSet = new Set(logSemana.map(r => String(r.tarefa_id) + '|' + r.data));

    html += '<div class="habit-grid">';
    html += '<div></div>';
    weekDays.forEach(d => { html += '<div class="habit-grid-day-label">' + d.name + '</div>'; });

    habitos.forEach(h => {
      const tituloCurto = (h.titulo || '').slice(0, 24);
      html += '<div class="habit-grid-label">🔁 ' + escapeHtml(tituloCurto) + '</div>';
      weekDays.forEach(day => {
        const key = String(h.id) + '|' + day.date;
        if (logSet.has(key)) {
          html += '<div class="habit-grid-cell completed">&#10003;</div>';
        } else {
          html += '<div class="habit-grid-cell"></div>';
        }
      });
    });
    html += '</div>';
  }

  // ======== Seção 2: subcategorias Pessoais antigas (compatibilidade) ========
  const habitSubcats = Object.keys(SUBCATEGORY_LABELS);
  const subHtml = [];
  habitSubcats.forEach(sub => {
    const subTasks = tasks.filter(t =>
      !t.eh_habito && t.subcategoria === sub && t.prazo >= weekStart && t.prazo <= weekEnd
    );
    if (subTasks.length === 0) return;
    hasData = true;
    const icon = SUBCATEGORY_ICONS[sub] || '';
    let row = '<div class="habit-grid-label">' + icon + ' ' + SUBCATEGORY_LABELS[sub] + '</div>';
    weekDays.forEach(day => {
      const dayTask = subTasks.find(t => t.prazo === day.date);
      if (dayTask) {
        const completed = dayTask.status === 'concluida';
        row += '<div class="habit-grid-cell ' + (completed ? 'completed' : 'partial') + '">' + (completed ? '&#10003;' : '&#9711;') + '</div>';
      } else {
        row += '<div class="habit-grid-cell"></div>';
      }
    });
    subHtml.push(row);
  });
  if (subHtml.length > 0) {
    html += '<div class="habit-grid" style="margin-top:0.75rem">';
    html += '<div></div>';
    weekDays.forEach(d => { html += '<div class="habit-grid-day-label">' + d.name + '</div>'; });
    html += subHtml.join('');
    html += '</div>';
  }

  html += '</div>';
  container.innerHTML = hasData ? html : '';
}

// ========== MODIFY EXISTING FUNCTIONS ==========

// Patch: category select toggles subcategory visibility
document.addEventListener('change', function(e) {
  if (e.target && e.target.id === 'inputCategory') {
    toggleSubcategoryVisibility();
  }
});

// ========== FEATURE 1: HEATMAP 365 (GitHub-style) ==========
async function renderHeatmap365() {
  const container = document.getElementById('heatmap365Section');
  if (!container) return;

  // Fetch completed tasks for last 365 days
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(endDate.getDate() - 364);
  const startStr = startDate.toISOString().split('T')[0];

  let completedDates = [];
  if (!currentUser) { container.innerHTML = ''; return; }
  try {
    const { data, error } = await sb
      .from('tarefas')
      .select('prazo')
      .eq('user_id', currentUser.id)
      .eq('status', 'concluida')
      .gte('prazo', startStr);
    if (!error && data) {
      completedDates = data.map(t => t.prazo).filter(Boolean);
    }
  } catch (e) {
    // fallback: use local tasks array
    completedDates = tasks
      .filter(t => t.status === 'concluida' && t.prazo && t.prazo >= startStr)
      .map(t => t.prazo);
  }

  // Count per date
  const countByDate = {};
  completedDates.forEach(d => { countByDate[d] = (countByDate[d] || 0) + 1; });
  const maxCount = Math.max(...Object.values(countByDate), 1);

  // Build 365 days array starting from startDate (aligned to Sunday start for columns)
  const days = [];
  const d = new Date(startDate);
  // Align to start of week (Sunday)
  while (d.getDay() !== 0) { d.setDate(d.getDate() - 1); }
  const alignedStart = new Date(d);
  while (d <= endDate) {
    days.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }
  // Fill remaining week
  while (days.length % 7 !== 0) {
    days.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }

  const totalWeeks = Math.ceil(days.length / 7);

  // Month labels
  const monthNames = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  let monthsHTML = '<div class="heatmap365-months">';
  let lastMonth = -1;
  for (let w = 0; w < totalWeeks; w++) {
    const firstDayOfWeek = days[w * 7];
    const m = firstDayOfWeek.getMonth();
    if (m !== lastMonth) {
      monthsHTML += '<span class="heatmap365-month-label" style="width:13px;min-width:13px">' + monthNames[m] + '</span>';
      lastMonth = m;
    } else {
      monthsHTML += '<span style="width:13px;min-width:13px"></span>';
    }
  }
  monthsHTML += '</div>';

  // Cells
  let cellsHTML = '';
  days.forEach(day => {
    const dateStr = day.toISOString().split('T')[0];
    const count = countByDate[dateStr] || 0;
    let level = 0;
    if (count > 0) {
      const ratio = count / maxCount;
      if (ratio <= 0.25) level = 1;
      else if (ratio <= 0.5) level = 2;
      else if (ratio <= 0.75) level = 3;
      else level = 4;
    }
    const isBeforeStart = day < startDate;
    const isAfterEnd = day > endDate;
    const opacity = (isBeforeStart || isAfterEnd) ? 'opacity:0.2;' : '';
    const dayLabel = day.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' });
    cellsHTML += '<div class="heatmap365-cell h-level-' + level + '" style="' + opacity + '">'
      + '<span class="heatmap365-tooltip">' + dayLabel + ': ' + count + ' concluída(s)</span></div>';
  });

  const legendHTML = '<div class="heatmap365-legend">Menos '
    + '<div class="heatmap365-legend-cell" style="background:var(--bg-glass)"></div>'
    + '<div class="heatmap365-legend-cell" style="background:rgba(185,145,91,0.15)"></div>'
    + '<div class="heatmap365-legend-cell" style="background:rgba(185,145,91,0.3)"></div>'
    + '<div class="heatmap365-legend-cell" style="background:rgba(185,145,91,0.5)"></div>'
    + '<div class="heatmap365-legend-cell" style="background:rgba(185,145,91,0.75)"></div>'
    + ' Mais</div>';

  container.innerHTML = '<div class="review-card" style="margin-top:0.75rem">'
    + '<h3 style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem">Atividade (365 dias)</h3>'
    + '<div class="heatmap365-container">' + monthsHTML
    + '<div class="heatmap365-grid">' + cellsHTML + '</div></div>'
    + legendHTML + '</div>';
}

// ========== FEATURE 2: SWIPE GESTURES (mobile) ==========
let swipeState = { startX: 0, startY: 0, currentX: 0, swiping: false, card: null, wrapper: null };
const SWIPE_THRESHOLD = 80;
const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

function setupSwipeGestures() {
  if (!isTouchDevice) return;

  document.addEventListener('touchstart', handleSwipeStart, { passive: true });
  document.addEventListener('touchmove', handleSwipeMove, { passive: false });
  document.addEventListener('touchend', handleSwipeEnd, { passive: true });
}

function handleSwipeStart(e) {
  const card = e.target.closest('.task-card');
  if (!card || !card.dataset.taskId) return;
  // Ignore if inside action buttons
  if (e.target.closest('.task-action-btn') || e.target.closest('.task-check') || e.target.closest('.bulk-check')) return;

  const touch = e.touches[0];
  swipeState.startX = touch.clientX;
  swipeState.startY = touch.clientY;
  swipeState.card = card;
  swipeState.swiping = false;
  swipeState.dirLocked = false;
}

function handleSwipeMove(e) {
  if (!swipeState.card) return;
  const touch = e.touches[0];
  const dx = touch.clientX - swipeState.startX;
  const dy = touch.clientY - swipeState.startY;

  // Lock direction on first significant move
  if (!swipeState.dirLocked) {
    if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
    swipeState.dirLocked = true;
    // If scrolling vertically, cancel swipe
    if (Math.abs(dy) > Math.abs(dx)) {
      swipeState.card = null;
      return;
    }
  }

  e.preventDefault();
  swipeState.swiping = true;
  swipeState.currentX = dx;

  const card = swipeState.card;
  card.classList.add('swiping');
  card.style.transform = 'translateX(' + dx + 'px)';

  // Show swipe backgrounds
  let wrapper = card.closest('.task-card-swipe-wrapper');
  if (!wrapper) {
    // Dynamically wrap
    wrapper = document.createElement('div');
    wrapper.className = 'task-card-swipe-wrapper';
    card.parentNode.insertBefore(wrapper, card);
    wrapper.appendChild(card);

    const bgRight = document.createElement('div');
    bgRight.className = 'swipe-bg swipe-bg-right';
    bgRight.textContent = 'Concluir';
    wrapper.insertBefore(bgRight, card);

    const bgLeft = document.createElement('div');
    bgLeft.className = 'swipe-bg swipe-bg-left';
    bgLeft.textContent = 'Adiar';
    wrapper.insertBefore(bgLeft, card);
  }
  swipeState.wrapper = wrapper;

  const bgRight = wrapper.querySelector('.swipe-bg-right');
  const bgLeft = wrapper.querySelector('.swipe-bg-left');
  if (dx > 30) {
    bgRight.classList.add('visible');
    bgLeft.classList.remove('visible');
  } else if (dx < -30) {
    bgLeft.classList.add('visible');
    bgRight.classList.remove('visible');
  } else {
    bgRight.classList.remove('visible');
    bgLeft.classList.remove('visible');
  }
}

function handleSwipeEnd(e) {
  if (!swipeState.card || !swipeState.swiping) {
    swipeState.card = null;
    return;
  }

  const card = swipeState.card;
  const dx = swipeState.currentX;
  const taskId = card.dataset.taskId;

  if (dx > SWIPE_THRESHOLD) {
    // Swipe right -> complete
    card.classList.remove('swiping');
    card.classList.add('swipe-completing');
    setTimeout(() => {
      const task = tasks.find(t => String(t.id) === String(taskId));
      if (task && task.status !== 'concluida') {
        toggleTask(taskId);
      }
    }, 300);
  } else if (dx < -SWIPE_THRESHOLD) {
    // Swipe left -> postpone to tomorrow
    card.classList.remove('swiping');
    card.classList.add('swipe-postponing');
    setTimeout(() => {
      postponeTask(taskId);
    }, 300);
  } else {
    // Snap back
    card.classList.remove('swiping');
    card.style.transform = '';
    if (swipeState.wrapper) {
      const bgs = swipeState.wrapper.querySelectorAll('.swipe-bg');
      bgs.forEach(bg => bg.classList.remove('visible'));
    }
  }

  swipeState.card = null;
  swipeState.swiping = false;
  swipeState.currentX = 0;
}

async function postponeTask(id) {
  const task = tasks.find(t => String(t.id) === String(id));
  if (!task) return;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const newDate = tomorrow.toISOString().split('T')[0];
  const oldDate = task.prazo;
  task.prazo = newDate;
  renderTasks();
  renderToday();
  renderCalendar();
  const ok = await updateTask(id, { prazo: newDate });
  if (!ok) {
    task.prazo = oldDate;
    renderTasks();
    renderToday();
    renderCalendar();
  }
}

