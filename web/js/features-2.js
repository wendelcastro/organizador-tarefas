// ========== FEATURE 3: POMODORO TIMER (Técnica Completa) ==========
//
// Ciclo Pomodoro clássico:
// 1) Trabalho 25min → 2) Pausa curta 5min → 3) Trabalho 25min → 4) Pausa curta 5min
// → 5) Trabalho 25min → 6) Pausa curta 5min → 7) Trabalho 25min → 8) Pausa LONGA 15min
// Total: 4 blocos de trabalho, 3 pausas curtas, 1 pausa longa = ~2h10min
//
const POMODORO_WORK_MIN = 25;
const POMODORO_SHORT_BREAK_MIN = 5;
const POMODORO_LONG_BREAK_MIN = 15;
const POMODORO_CYCLES = 4; // 4 blocos de trabalho antes da pausa longa

// Fases: 'work', 'short_break', 'long_break'
pomodoroState = {
  taskId: null,
  taskName: '',
  running: false,
  paused: false,
  remainingSeconds: POMODORO_WORK_MIN * 60,
  intervalId: null,
  accumulatedByTask: {},
  phase: 'work',        // 'work' | 'short_break' | 'long_break'
  currentCycle: 1,       // 1 a 4 (qual bloco de trabalho)
  completedCycles: 0,    // quantos blocos de trabalho finalizados nesta sessão
};

const PHASE_CONFIG = {
  work:        { label: 'Foco',         color: '#4CAF50', minutes: POMODORO_WORK_MIN,        beepFreq: 880  },
  short_break: { label: 'Pausa curta',  color: '#4FC3F7', minutes: POMODORO_SHORT_BREAK_MIN, beepFreq: 660  },
  long_break:  { label: 'Pausa longa',  color: '#CE93D8', minutes: POMODORO_LONG_BREAK_MIN,  beepFreq: 440  },
};

function startPomodoro(taskId) {
  const task = tasks.find(t => String(t.id) === String(taskId));
  if (!task) return;

  // Pede permissão de notificação logo no início
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }

  if (pomodoroState.intervalId) clearInterval(pomodoroState.intervalId);

  pomodoroState.taskId = taskId;
  pomodoroState.taskName = task.titulo;
  pomodoroState.phase = 'work';
  pomodoroState.currentCycle = 1;
  pomodoroState.completedCycles = 0;
  pomodoroState.remainingSeconds = POMODORO_WORK_MIN * 60;
  pomodoroState.running = true;
  pomodoroState.paused = false;

  const saved = localStorage.getItem('pomodoro_accum');
  if (saved) {
    try { pomodoroState.accumulatedByTask = JSON.parse(saved); } catch(e) {}
  }

  updatePomodoroUI();
  document.getElementById('pomodoroWidget').classList.add('active');
  document.getElementById('pomodoroPlayPause').innerHTML = '&#10074;&#10074;';

  _startPomodoroInterval();
}

function _startPomodoroInterval() {
  if (pomodoroState.intervalId) clearInterval(pomodoroState.intervalId);
  pomodoroState.intervalId = setInterval(() => {
    if (!pomodoroState.running || pomodoroState.paused) return;
    pomodoroState.remainingSeconds--;

    // Acumula tempo de TRABALHO (não de pausa) para a tarefa
    if (pomodoroState.phase === 'work') {
      const tid = pomodoroState.taskId;
      if (!pomodoroState.accumulatedByTask[tid]) pomodoroState.accumulatedByTask[tid] = 0;
      pomodoroState.accumulatedByTask[tid]++;
      if (pomodoroState.remainingSeconds % 30 === 0) {
        localStorage.setItem('pomodoro_accum', JSON.stringify(pomodoroState.accumulatedByTask));
      }
    }

    updatePomodoroUI();

    if (pomodoroState.remainingSeconds <= 0) {
      _pomodoroPhaseComplete();
    }
  }, 1000);
}

function _pomodoroPhaseComplete() {
  clearInterval(pomodoroState.intervalId);
  pomodoroState.intervalId = null;
  pomodoroState.paused = true;

  const cfg = PHASE_CONFIG[pomodoroState.phase];

  // Toca som
  _pomodoroBeep(cfg.beepFreq);

  if (pomodoroState.phase === 'work') {
    pomodoroState.completedCycles++;
    localStorage.setItem('pomodoro_accum', JSON.stringify(pomodoroState.accumulatedByTask));

    // Salvar tempo no Supabase (acumulado até agora)
    _savePomodoroToDatabase();

    if (pomodoroState.completedCycles >= POMODORO_CYCLES) {
      // Após 4 blocos → pausa longa
      _pomodoroTransition('long_break', 'Excelente! 4 Pomodoros completos. Hora da pausa longa de 15 minutos. Descanse de verdade — levante, alongue, hidrate-se.');
    } else {
      // Pausa curta
      _pomodoroTransition('short_break', 'Pomodoro ' + pomodoroState.completedCycles + '/4 concluído! Pausa de 5 minutos. Levante, olhe para longe, respire.');
    }
  } else if (pomodoroState.phase === 'short_break') {
    // Fim da pausa curta → próximo trabalho
    pomodoroState.currentCycle = pomodoroState.completedCycles + 1;
    _pomodoroTransition('work', 'Pausa encerrada! Hora de focar no Pomodoro ' + pomodoroState.currentCycle + '/4.');
  } else if (pomodoroState.phase === 'long_break') {
    // Fim do ciclo completo!
    _pomodoroNotify('Ciclo Pomodoro completo!', 'Você completou 4 Pomodoros de ' + pomodoroState.taskName + '. Parabéns!');
    document.getElementById('pomodoroTime').textContent = 'Completo!';
    document.getElementById('pomodoroPhase').textContent = '🏆 Sessão completa';
    document.getElementById('pomodoroPhase').style.background = 'rgba(0,117,222,0.15)';
    document.getElementById('pomodoroPhase').style.color = '#0075de';
    pomodoroState.running = false;
    setTimeout(() => {
      document.getElementById('pomodoroWidget').classList.remove('active');
      renderTasks();
      renderToday();
    }, 5000);
    return;
  }
}

function _pomodoroTransition(newPhase, message) {
  const cfg = PHASE_CONFIG[newPhase];
  pomodoroState.phase = newPhase;
  pomodoroState.remainingSeconds = cfg.minutes * 60;
  pomodoroState.paused = false;
  pomodoroState.running = true;

  _pomodoroNotify(cfg.label, message);
  updatePomodoroUI();
  document.getElementById('pomodoroPlayPause').innerHTML = '&#10074;&#10074;';
  _startPomodoroInterval();
}

function _pomodoroNotify(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body, icon: '🍅' });
  }
}

function _pomodoroBeep(freq) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = freq;
    gain.gain.value = 0.3;
    osc.start();
    // 3 beeps curtos
    setTimeout(() => { gain.gain.value = 0; }, 200);
    setTimeout(() => { gain.gain.value = 0.3; }, 400);
    setTimeout(() => { gain.gain.value = 0; }, 600);
    setTimeout(() => { gain.gain.value = 0.3; }, 800);
    setTimeout(() => { osc.stop(); ctx.close(); }, 1000);
  } catch(e) {}
}

async function _savePomodoroToDatabase() {
  if (!currentUser || !pomodoroState.taskId) return;
  const tid = pomodoroState.taskId;
  const accumSec = pomodoroState.accumulatedByTask[tid] || 0;
  const accumMin = Math.floor(accumSec / 60);
  if (accumMin <= 0) return;
  try {
    await sb.from('tarefas')
      .update({ tempo_gasto_min: accumMin })
      .eq('id', tid)
      .eq('user_id', currentUser.id);
  } catch(e) {
    console.warn('Erro ao salvar tempo Pomodoro no banco:', e.message);
  }
}

function togglePomodoro() {
  if (!pomodoroState.running) return;
  pomodoroState.paused = !pomodoroState.paused;
  document.getElementById('pomodoroPlayPause').innerHTML = pomodoroState.paused ? '&#9654;' : '&#10074;&#10074;';
}

function stopPomodoro() {
  if (pomodoroState.intervalId) clearInterval(pomodoroState.intervalId);
  localStorage.setItem('pomodoro_accum', JSON.stringify(pomodoroState.accumulatedByTask));
  _savePomodoroToDatabase();
  pomodoroState.running = false;
  pomodoroState.paused = false;
  pomodoroState.intervalId = null;
  pomodoroState.taskId = null;
  pomodoroState.phase = 'work';
  pomodoroState.currentCycle = 1;
  pomodoroState.completedCycles = 0;
  document.getElementById('pomodoroWidget').classList.remove('active');
  renderTasks();
  renderToday();
}

function pomodoroSkipPhase() {
  if (!pomodoroState.running) return;
  if (!confirm('Pular esta fase e ir para a próxima?')) return;
  pomodoroState.remainingSeconds = 0;
  _pomodoroPhaseComplete();
}

function updatePomodoroUI() {
  const min = Math.floor(pomodoroState.remainingSeconds / 60);
  const sec = pomodoroState.remainingSeconds % 60;
  document.getElementById('pomodoroTime').textContent = String(min).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
  document.getElementById('pomodoroTaskName').textContent = pomodoroState.taskName;

  // Badge da fase
  const cfg = PHASE_CONFIG[pomodoroState.phase];
  const phaseEl = document.getElementById('pomodoroPhase');
  const cycleLabel = pomodoroState.phase === 'work'
    ? cfg.label + ' ' + pomodoroState.currentCycle + '/' + POMODORO_CYCLES
    : cfg.label;
  phaseEl.textContent = cycleLabel;
  phaseEl.style.background = cfg.color + '22';
  phaseEl.style.color = cfg.color;

  // Dots de ciclos completos
  const dotsEl = document.getElementById('pomodoroCycleDots');
  let dots = '';
  for (let i = 1; i <= POMODORO_CYCLES; i++) {
    const done = i <= pomodoroState.completedCycles;
    const current = i === pomodoroState.currentCycle && pomodoroState.phase === 'work';
    dots += '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 2px;'
      + 'background:' + (done ? '#4CAF50' : current ? '#0075de' : 'rgba(0,0,0,0.08)') + '"></span>';
  }
  dotsEl.innerHTML = dots;

  // Widget border-color based on phase
  document.getElementById('pomodoroWidget').style.borderColor = cfg.color + '66';

  // Acumulado de trabalho
  const accum = pomodoroState.accumulatedByTask[pomodoroState.taskId] || 0;
  if (accum > 0) {
    const accumMin = Math.floor(accum / 60);
    document.getElementById('pomodoroAccum').textContent = 'Foco total: ' + accumMin + 'min';
  } else {
    document.getElementById('pomodoroAccum').textContent = '';
  }
}

function getPomodoroAccumMinutes(taskId) {
  const saved = localStorage.getItem('pomodoro_accum');
  if (!saved) return 0;
  try {
    const data = JSON.parse(saved);
    return Math.floor((data[taskId] || 0) / 60);
  } catch(e) { return 0; }
}

// Request notification permission early
if ('Notification' in window && Notification.permission === 'default') {
  // Will request on first pomodoro start
}

// ========== FEATURE 4: EISENHOWER MATRIX VIEW (v2 — Drag & Drop) ==========
function suggestQuadrant(t) {
  // Auto-suggestion based on prazo + prioridade (used when quadrante_eisenhower is null)
  const hoje = new Date().toISOString().split('T')[0];
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split('T')[0];
  const urgent = t.prazo ? t.prazo <= tomorrowStr : false;
  const important = t.prioridade === 'alta';
  if (urgent && important) return 'q1';
  if (!urgent && important) return 'q2';
  if (urgent && !important) return 'q3';
  return 'q4';
}

function getTaskQuadrant(t) {
  // Manual override takes priority, otherwise auto-suggest
  return t.quadrante_eisenhower || suggestQuadrant(t);
}

async function saveQuadrant(taskId, quadrant) {
  try {
    const headers = await getAuthHeaders();
    headers['Content-Type'] = 'application/json';
    headers['Prefer'] = 'return=minimal';
    await fetch(`${SUPABASE_URL}/rest/v1/tarefas?id=eq.${taskId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ quadrante_eisenhower: quadrant })
    });
    // Update local cache
    const task = tasks.find(t => t.id === taskId);
    if (task) task.quadrante_eisenhower = quadrant;
  } catch (e) { console.error('Erro ao salvar quadrante:', e); }
}

function renderMatrix() {
  const container = document.getElementById('matrixView');
  if (!container) return;

  const activeTasks = tasks.filter(t => t.status !== 'concluida');

  const quadrants = { q1: [], q2: [], q3: [], q4: [] };
  activeTasks.forEach(t => {
    const q = getTaskQuadrant(t);
    quadrants[q].push(t);
  });

  function renderQuadrantTasks(list) {
    if (list.length === 0) return '<div class="matrix-empty">Arraste tarefas aqui</div>';
    return list.map(t => {
      const catColor = CATEGORY_COLORS[t.categoria] || 'var(--text-muted)';
      const isManual = t.quadrante_eisenhower ? '' : '<span class="matrix-task-badge">auto</span>';
      return '<div class="matrix-task-item" draggable="true" style="--cat-color:' + catColor + '" data-task-id="' + t.id + '">'
        + '<div>' + t.titulo + isManual + '</div>'
        + '<div class="matrix-task-meta">' + (t.prazo ? formatDate(t.prazo) : 'Sem prazo') + ' · ' + t.categoria + '</div>'
        + '</div>';
    }).join('');
  }

  const qMeta = {
    q1: { label: 'Fazer Agora', subtitle: 'Urgente + Importante', icon: '🔴' },
    q2: { label: 'Agendar', subtitle: 'Importante, não urgente', icon: '🔵' },
    q3: { label: 'Delegar', subtitle: 'Urgente, não importante', icon: '🟡' },
    q4: { label: 'Eliminar', subtitle: 'Nem urgente nem importante', icon: '⚪' }
  };

  let gridHTML = '';
  for (const [qKey, meta] of Object.entries(qMeta)) {
    const count = quadrants[qKey].length;
    gridHTML += '<div class="matrix-quadrant ' + qKey + '" data-quadrant="' + qKey + '">'
      + '<div class="matrix-quadrant-header">'
      + '<span class="matrix-quadrant-label">' + meta.icon + ' ' + meta.label + '</span>'
      + '<span class="matrix-quadrant-count">' + count + '</span>'
      + '<span class="matrix-quadrant-subtitle">' + meta.subtitle + '</span>'
      + '</div>'
      + '<div class="matrix-task-list">' + renderQuadrantTasks(quadrants[qKey]) + '</div>'
      + '</div>';
  }

  container.innerHTML = '<h2 style="font-family:\'Inter\',sans-serif;font-weight:700;letter-spacing:-0.02em;font-size:1.3rem;color:var(--text-primary);margin-bottom:0.3rem">Matriz de Eisenhower</h2>'
    + '<div class="matrix-subtitle-info">'
    + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm1 5h-2v6h2zm0 8h-2v2h2z"/></svg>'
    + 'Arraste tarefas entre quadrantes para reclassificar. <span style="color:var(--amber)">Auto</span> = sugestão da IA.'
    + '</div>'
    + '<div class="matrix-grid">' + gridHTML + '</div>';

  // --- Drag & Drop ---
  let draggedId = null;

  container.querySelectorAll('.matrix-task-item[data-task-id]').forEach(el => {
    el.addEventListener('dragstart', (e) => {
      draggedId = el.dataset.taskId;
      el.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', draggedId);
    });
    el.addEventListener('dragend', () => {
      el.classList.remove('dragging');
      container.querySelectorAll('.matrix-quadrant').forEach(q => q.classList.remove('drag-over'));
    });
    // Click to open detail (but not if dragging)
    let clickStart = 0;
    el.addEventListener('mousedown', () => { clickStart = Date.now(); });
    el.addEventListener('click', () => {
      if (Date.now() - clickStart < 200) showTaskDetail(el.dataset.taskId);
    });
  });

  container.querySelectorAll('.matrix-quadrant').forEach(quad => {
    quad.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      quad.classList.add('drag-over');
    });
    quad.addEventListener('dragleave', () => {
      quad.classList.remove('drag-over');
    });
    quad.addEventListener('drop', (e) => {
      e.preventDefault();
      quad.classList.remove('drag-over');
      const taskId = e.dataTransfer.getData('text/plain') || draggedId;
      const newQuadrant = quad.dataset.quadrant;
      if (taskId && newQuadrant) {
        saveQuadrant(taskId, newQuadrant);
        renderMatrix();
        renderTasks();
        renderToday();
      }
    });
  });

  // --- Touch Drag & Drop (mobile) ---
  let touchDragEl = null, touchDragId = null, touchGhost = null;

  container.querySelectorAll('.matrix-task-item[data-task-id]').forEach(el => {
    let touchTimer = null, isTouchDrag = false;

    el.addEventListener('touchstart', (e) => {
      isTouchDrag = false;
      touchTimer = setTimeout(() => {
        isTouchDrag = true;
        touchDragEl = el;
        touchDragId = el.dataset.taskId;
        el.classList.add('dragging');
        // Create ghost
        touchGhost = el.cloneNode(true);
        touchGhost.style.cssText = 'position:fixed;z-index:9999;pointer-events:none;opacity:0.8;width:' + el.offsetWidth + 'px;transform:scale(1.05);';
        document.body.appendChild(touchGhost);
        navigator.vibrate && navigator.vibrate(30);
      }, 400); // long press 400ms
    }, { passive: true });

    el.addEventListener('touchmove', (e) => {
      if (!isTouchDrag) { clearTimeout(touchTimer); return; }
      e.preventDefault();
      const touch = e.touches[0];
      if (touchGhost) {
        touchGhost.style.left = (touch.clientX - 60) + 'px';
        touchGhost.style.top = (touch.clientY - 20) + 'px';
      }
      // Highlight quadrant under finger
      container.querySelectorAll('.matrix-quadrant').forEach(q => q.classList.remove('drag-over'));
      const elUnder = document.elementFromPoint(touch.clientX, touch.clientY);
      if (elUnder) {
        const quad = elUnder.closest('.matrix-quadrant');
        if (quad) quad.classList.add('drag-over');
      }
    }, { passive: false });

    el.addEventListener('touchend', (e) => {
      clearTimeout(touchTimer);
      if (!isTouchDrag) return;
      isTouchDrag = false;
      if (touchGhost) { touchGhost.remove(); touchGhost = null; }
      if (touchDragEl) touchDragEl.classList.remove('dragging');
      container.querySelectorAll('.matrix-quadrant').forEach(q => q.classList.remove('drag-over'));

      const touch = e.changedTouches[0];
      const elUnder = document.elementFromPoint(touch.clientX, touch.clientY);
      if (elUnder) {
        const quad = elUnder.closest('.matrix-quadrant');
        if (quad && touchDragId) {
          const newQuadrant = quad.dataset.quadrant;
          saveQuadrant(touchDragId, newQuadrant);
          renderMatrix();
          renderTasks();
          renderToday();
        }
      }
      touchDragEl = null; touchDragId = null;
    });
  });
}

// ========== FEATURE: ENERGY MAPPING WIDGET ==========

function renderEnergyLogger() {
  const hour = new Date().getHours();
  let currentPeriod = '';
  if (hour >= 6 && hour < 12) currentPeriod = 'manha';
  else if (hour >= 12 && hour < 18) currentPeriod = 'tarde';
  else currentPeriod = 'noite';

  const periods = [
    { key: 'manha', label: 'Manhã', icon: '\u2600\uFE0F' },
    { key: 'tarde', label: 'Tarde', icon: '\uD83C\uDF24\uFE0F' },
    { key: 'noite', label: 'Noite', icon: '\uD83C\uDF19' }
  ];

  const nivelLabels = ['', 'Exausto', 'Cansado', 'Normal', 'Bem', 'Energizado'];

  return '<div class="energy-section">'
    + '<div class="energy-header">'
    + '<span class="energy-title">⚡ Nível de Energia</span>'
    + '<span class="energy-hint">Toque nas bolinhas para registrar como você está</span>'
    + '</div>'
    + '<div class="energy-logger" id="energyLogger">' + periods.map(p => {
    const nivel = energyData[p.key] || 0;
    const isCurrent = p.key === currentPeriod ? ' current-period' : '';
    const label = nivel > 0 ? nivelLabels[nivel] : 'Toque aqui';
    return '<div class="energy-period' + isCurrent + '" data-period="' + p.key + '" data-nivel="' + nivel + '">'
      + '<div class="energy-period-label">' + p.icon + ' ' + p.label + '</div>'
      + '<div class="energy-dots">'
      + [1,2,3,4,5].map(n =>
          '<div class="energy-dot' + (n <= nivel ? ' active' : '') + '" data-level="' + n + '" title="' + nivelLabels[n] + '"></div>'
        ).join('')
      + '</div>'
      + '<div class="energy-level-label" data-period-label="' + p.key + '">' + label + '</div>'
      + '</div>';
  }).join('') + '</div></div>';
}

function initEnergyLogger() {
  const logger = document.getElementById('energyLogger');
  if (!logger) return;

  logger.querySelectorAll('.energy-dot').forEach(dot => {
    dot.addEventListener('click', async function() {
      const period = this.closest('.energy-period');
      const periodKey = period.dataset.period;
      const level = parseInt(this.dataset.level);

      // Toggle: if clicking the same level, reset to 0
      const currentLevel = energyData[periodKey] || 0;
      const newLevel = currentLevel === level ? 0 : level;
      energyData[periodKey] = newLevel;
      period.dataset.nivel = newLevel;

      // Update dots visual
      period.querySelectorAll('.energy-dot').forEach((d, i) => {
        d.classList.toggle('active', (i + 1) <= newLevel);
      });
      // Update level label
      const nivelLabels = ['Toque aqui', 'Exausto', 'Cansado', 'Normal', 'Bem', 'Energizado'];
      const labelEl = period.querySelector('.energy-level-label');
      if (labelEl) labelEl.textContent = nivelLabels[newLevel];

      // Save to Supabase (one row per period)
      const today = new Date().toISOString().split('T')[0];
      try {
        const authHdrs = await getAuthHeaders();
        const uid = currentUser?.id;
        if (!uid) throw new Error('Sem usuário autenticado');
        if (newLevel > 0) {
          await fetch(SUPABASE_URL + '/rest/v1/energia_diaria', {
            method: 'POST',
            headers: {
              ...authHdrs,
              'Content-Type': 'application/json',
              'Prefer': 'resolution=merge-duplicates'
            },
            body: JSON.stringify({
              data: today,
              periodo: periodKey,
              nivel: newLevel,
              user_id: uid
            })
          });
        } else {
          await fetch(SUPABASE_URL + '/rest/v1/energia_diaria?user_id=eq.' + uid + '&data=eq.' + today + '&periodo=eq.' + periodKey, {
            method: 'DELETE',
            headers: authHdrs
          });
        }
      } catch (e) {
        console.warn('Erro ao salvar energia:', e.message);
      }
      localStorage.setItem('energy_' + today, JSON.stringify(energyData));
    });
  });
}

async function loadEnergyData() {
  const today = new Date().toISOString().split('T')[0];
  try {
    const headers = await getAuthHeaders();
    const uid = currentUser?.id;
    if (!uid) throw new Error('sem usuário');
    const res = await fetch(SUPABASE_URL + '/rest/v1/energia_diaria?user_id=eq.' + uid + '&data=eq.' + today + '&select=periodo,nivel', {
      headers
    });
    const data = await res.json();
    if (data && data.length > 0) {
      // Each row is one period: { periodo: 'manha', nivel: 4 }
      data.forEach(row => {
        if (row.periodo && row.nivel) {
          energyData[row.periodo] = row.nivel;
        }
      });
    }
  } catch (e) {
    // Fallback: localStorage
    const saved = localStorage.getItem('energy_' + today);
    if (saved) {
      try { energyData = JSON.parse(saved); } catch (e2) { /* ignore */ }
    }
  }
}

// ========== FEATURE: TIME BLOCKING VIEW ==========

function renderTimeBlocks(dateStr) {
  const container = document.getElementById('timeblockView');
  if (!container) return;

  const today = new Date().toISOString().split('T')[0];
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split('T')[0];

  // Day selector
  let html = '<h2 style="font-family:\'Inter\',sans-serif;font-weight:700;letter-spacing:-0.02em;font-size:1.3rem;color:var(--text-primary);margin-bottom:0.5rem">Blocos de Tempo</h2>';
  html += '<div class="timeblock-day-selector">';
  html += '<button class="timeblock-day-btn' + (dateStr === today ? ' active' : '') + '" onclick="timeblockSelectedDate=\'' + today + '\';renderTimeBlocks(\'' + today + '\')">Hoje</button>';
  html += '<button class="timeblock-day-btn' + (dateStr === tomorrowStr ? ' active' : '') + '" onclick="timeblockSelectedDate=\'' + tomorrowStr + '\';renderTimeBlocks(\'' + tomorrowStr + '\')">Amanhã</button>';
  html += '<input type="date" class="timeblock-day-btn" value="' + dateStr + '" onchange="timeblockSelectedDate=this.value;renderTimeBlocks(this.value)" style="color-scheme:dark;background:var(--bg-glass);min-width:auto">';
  html += '</div>';

  // All-day events banner
  const allDayEvents = calendarEvents.filter(ev => ev.dia === dateStr && ev.all_day);
  if (allDayEvents.length > 0) {
    html += '<div class="allday-events-banner">';
    allDayEvents.forEach(ev => {
      const provider = ev.provider || 'google';
      html += '<span class="allday-event-chip ' + provider + '">';
      html += '<span class="event-badge ' + provider + '" style="margin-left:0">' + (provider === 'microsoft' ? 'Teams' : 'Google') + '</span> ';
      html += escapeHtml(ev.titulo);
      html += '</span>';
    });
    html += '</div>';
  }

  // Filter tasks for this date (hábitos não entram aqui — view "Hoje" lida com eles)
  let dayTasks = tasks.filter(t => !t.eh_habito && t.prazo === dateStr);
  const dayEvents = calendarEvents.filter(ev => ev.dia === dateStr && !ev.all_day);
  // Dedup: se tarefa tem mesmo titulo/horario de um evento do Google, mostra só o evento
  dayTasks = deduplicateTasksAgainstEvents(dayTasks, dayEvents);

  // Group by period
  const periods = [
    { key: 'manha', label: 'Manhã', icon: '\u2600\uFE0F', hours: '6h - 12h', start: 6, end: 12 },
    { key: 'tarde', label: 'Tarde', icon: '\uD83C\uDF24\uFE0F', hours: '12h - 18h', start: 12, end: 18 },
    { key: 'noite', label: 'Noite', icon: '\uD83C\uDF19', hours: '18h - 24h', start: 18, end: 24 },
    { key: 'sem_horario', label: 'Sem horário', icon: '\uD83D\uDCCB', hours: '', start: -1, end: -1 }
  ];

  const grouped = { manha: [], tarde: [], noite: [], sem_horario: [] };
  const groupedEvents = { manha: [], tarde: [], noite: [] };

  dayTasks.forEach(t => {
    if (!t.horario) {
      grouped.sem_horario.push(t);
      return;
    }
    const hour = parseInt(t.horario.split(':')[0], 10);
    if (hour >= 6 && hour < 12) grouped.manha.push(t);
    else if (hour >= 12 && hour < 18) grouped.tarde.push(t);
    else if (hour >= 18 || hour < 6) grouped.noite.push(t);
    else grouped.sem_horario.push(t);
  });

  dayEvents.forEach(ev => {
    const hour = ev.horario_inicio ? parseInt(ev.horario_inicio.split(':')[0], 10) : -1;
    if (hour >= 6 && hour < 12) groupedEvents.manha.push(ev);
    else if (hour >= 12 && hour < 18) groupedEvents.tarde.push(ev);
    else if (hour >= 18 || (hour >= 0 && hour < 6)) groupedEvents.noite.push(ev);
    else groupedEvents.manha.push(ev); // fallback
  });

  // Sort within each period
  ['manha', 'tarde', 'noite'].forEach(k => {
    grouped[k].sort((a, b) => (a.horario || '').localeCompare(b.horario || ''));
    groupedEvents[k].sort((a, b) => (a.horario_inicio || '').localeCompare(b.horario_inicio || ''));
  });

  html += '<div class="timeblock-container">';

  periods.forEach(period => {
    const pTasks = grouped[period.key];
    const pEvents = period.key !== 'sem_horario' ? (groupedEvents[period.key] || []) : [];
    // Skip empty "Sem horario" if no tasks
    if (period.key === 'sem_horario' && pTasks.length === 0) return;

    const hasContent = pTasks.length > 0 || pEvents.length > 0;

    html += '<div class="timeblock-section">';
    html += '<div class="timeblock-section-header">';
    html += '<span class="timeblock-period-icon">' + period.icon + '</span>';
    html += '<span class="timeblock-period-name">' + period.label + '</span>';
    if (period.hours) html += '<span class="timeblock-period-hours">' + period.hours + '</span>';
    html += '</div>';

    if (!hasContent) {
      html += '<div class="timeblock-empty">Nenhuma tarefa neste período</div>';
      html += '<div class="timeblock-free-slot">Horário livre</div>';
    } else {
      html += '<div class="timeblock-tasks">';
      // Events first (blocked time)
      pEvents.forEach(ev => {
        const provider = ev.provider || 'google';
        const badge = '<span class="timeblock-event-badge event-badge ' + provider + '">' + (provider === 'microsoft' ? 'Teams' : 'Google') + '</span>';
        html += '<div class="timeblock-event ' + provider + '">';
        html += '<span class="timeblock-event-time">' + (ev.horario_inicio || '--:--') + ' - ' + (ev.horario_fim || '--:--') + '</span>';
        html += '<span class="timeblock-event-title">' + escapeHtml(ev.titulo) + '</span>';
        html += badge;
        if (ev.meeting_link) {
          const platform = ev.meeting_platform || 'generic';
          html += ' <a href="' + ev.meeting_link + '" target="_blank" class="event-meeting-link ' + platform + '" onclick="event.stopPropagation()" style="font-size:0.55rem;padding:0.08rem 0.3rem">Entrar</a>';
        }
        html += '</div>';
      });
      // Then tasks
      pTasks.forEach(t => {
        const catColor = CATEGORY_COLORS[t.categoria] || 'var(--text-muted)';
        const completedClass = t.status === 'concluida' ? ' completed' : '';
        const duration = t.tempo_estimado_min ? t.tempo_estimado_min + 'min' : '';
        html += '<div class="timeblock-task' + completedClass + '" style="--cat-color:' + catColor + '" data-task-id="' + t.id + '">';
        html += '<span class="timeblock-task-time">' + (t.horario || '--:--') + '</span>';
        html += '<span class="timeblock-task-title">' + t.titulo + '</span>';
        if (duration) html += '<span class="timeblock-task-duration">' + duration + '</span>';
        html += '</div>';
      });
      html += '</div>';
    }
    html += '</div>';
  });

  html += '</div>';
  container.innerHTML = html;

  // Attach click events
  container.querySelectorAll('.timeblock-task[data-task-id]').forEach(el => {
    el.addEventListener('click', () => showTaskDetail(el.dataset.taskId));
  });
}

// ========== FEATURE: KPIs DASHBOARD ==========
function renderKPIs() {
  const container = document.getElementById('kpisView');
  if (!container) return;

  const hoje = new Date().toISOString().split('T')[0];
  const now = new Date();

  // -- Calculate week boundaries (ISO week: Mon-Sun) --
  function getISOWeekStart(d) {
    const dt = new Date(d);
    const day = dt.getDay();
    const diff = dt.getDate() - day + (day === 0 ? -6 : 1);
    dt.setDate(diff);
    dt.setHours(0,0,0,0);
    return dt;
  }

  // Current week stats
  const weekStart = getISOWeekStart(now);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);
  const weekStartStr = weekStart.toISOString().split('T')[0];
  const weekEndStr = weekEnd.toISOString().split('T')[0];

  const thisWeekTasks = tasks.filter(t => t.prazo >= weekStartStr && t.prazo <= weekEndStr);
  const completedThisWeek = thisWeekTasks.filter(t => t.status === 'concluida').length;
  const totalThisWeek = thisWeekTasks.length;
  const productivityScore = totalThisWeek > 0 ? Math.round((completedThisWeek / totalThisWeek) * 100) : 0;

  // Color for productivity score
  const scoreColor = productivityScore >= 70 ? 'var(--amber)' : productivityScore >= 40 ? 'var(--pri-media)' : 'var(--pri-alta)';

  // -- Streak --
  const streak = gamification.streak || 0;
  const streakRecord = gamification.streakRecord || 0;

  // -- Tasks per week (last 8 weeks) --
  const weeklyData = [];
  for (let w = 7; w >= 0; w--) {
    const ws = new Date(now);
    ws.setDate(ws.getDate() - (w * 7));
    const wStart = getISOWeekStart(ws);
    const wEnd = new Date(wStart);
    wEnd.setDate(wEnd.getDate() + 6);
    const wStartStr = wStart.toISOString().split('T')[0];
    const wEndStr = wEnd.toISOString().split('T')[0];
    const count = tasks.filter(t => t.status === 'concluida' && t.prazo >= wStartStr && t.prazo <= wEndStr).length;
    weeklyData.push({ label: 'S' + (8 - w), count });
  }
  const maxWeekly = Math.max(...weeklyData.map(w => w.count), 1);

  // -- Completion rate donut --
  const allActive = tasks.filter(t => t.status !== 'concluida' && t.prazo && t.prazo <= hoje);
  const completed = tasks.filter(t => t.status === 'concluida').length;
  const inProgress = tasks.filter(t => t.status === 'em_andamento').length;
  const pending = tasks.filter(t => t.status === 'pendente').length;
  const overdue = tasks.filter(t => isOverdue(t)).length;
  const totalForDonut = completed + inProgress + pending;

  // Donut segments (stroke-dasharray based)
  const circumference = 2 * Math.PI * 35;
  const segments = [];
  if (totalForDonut > 0) {
    const completedPct = completed / totalForDonut;
    const inProgressPct = inProgress / totalForDonut;
    const overduePct = overdue / totalForDonut;
    const pendingPct = Math.max(0, (pending - overdue) / totalForDonut);
    segments.push({ pct: completedPct, color: 'var(--amber)', label: 'Concluídas', count: completed });
    segments.push({ pct: inProgressPct, color: 'var(--cat-consultoria)', label: 'Em andamento', count: inProgress });
    segments.push({ pct: overduePct, color: 'var(--pri-alta)', label: 'Atrasadas', count: overdue });
    segments.push({ pct: pendingPct, color: 'var(--text-muted)', label: 'Pendentes', count: pending - overdue });
  }

  // -- Category distribution --
  const categories = ['Trabalho', 'Consultoria', 'Grupo Ser', 'Pessoal'];
  const catCounts = {};
  categories.forEach(c => { catCounts[c] = tasks.filter(t => t.categoria === c).length; });
  const maxCat = Math.max(...Object.values(catCounts), 1);

  // -- Weekly trend (completion rate per week, last 8 weeks) --
  const weeklyRates = [];
  for (let w = 7; w >= 0; w--) {
    const ws = new Date(now);
    ws.setDate(ws.getDate() - (w * 7));
    const wStart = getISOWeekStart(ws);
    const wEnd = new Date(wStart);
    wEnd.setDate(wEnd.getDate() + 6);
    const wStartStr = wStart.toISOString().split('T')[0];
    const wEndStr = wEnd.toISOString().split('T')[0];
    const wTasks = tasks.filter(t => t.prazo >= wStartStr && t.prazo <= wEndStr);
    const wDone = wTasks.filter(t => t.status === 'concluida').length;
    const rate = wTasks.length > 0 ? Math.round((wDone / wTasks.length) * 100) : 0;
    weeklyRates.push(rate);
  }

  // Build HTML
  let html = '<h2 style="font-family:\'Inter\',sans-serif;font-weight:700;letter-spacing:-0.02em;font-size:1.3rem;color:var(--text-primary);margin-bottom:0.75rem">KPIs & Métricas</h2>';

  html += '<div class="kpis-grid">';

  // 1. Productivity Score (full width)
  html += '<div class="kpi-card full-width" style="animation-delay:0.05s">';
  html += '<div class="kpi-card-label">Produtividade da Semana</div>';
  html += '<div class="kpi-card-value" style="color:' + scoreColor + '">' + productivityScore + '%</div>';
  html += '<div class="kpi-card-subtitle">' + completedThisWeek + ' de ' + totalThisWeek + ' tarefas concluídas</div>';
  html += '</div>';

  // 2. Streak
  html += '<div class="kpi-card" style="animation-delay:0.1s">';
  html += '<div class="kpi-card-label">Streak Atual</div>';
  html += '<div class="kpi-card-value">' + streak + '</div>';
  html += '<div class="kpi-card-subtitle">Recorde: ' + streakRecord + ' dias</div>';
  html += '</div>';

  // 3. Total concluidas
  html += '<div class="kpi-card" style="animation-delay:0.15s">';
  html += '<div class="kpi-card-label">Total Concluídas</div>';
  html += '<div class="kpi-card-value">' + completed + '</div>';
  html += '<div class="kpi-card-subtitle">De ' + tasks.length + ' tarefas</div>';
  html += '</div>';

  // 4. Tasks Per Week (bar chart, full width)
  html += '<div class="kpi-card full-width" style="animation-delay:0.2s">';
  html += '<div class="kpi-card-label">Tarefas Concluídas por Semana</div>';
  html += '<div class="kpi-bar-chart">';
  weeklyData.forEach(w => {
    const h = maxWeekly > 0 ? Math.max(4, Math.round((w.count / maxWeekly) * 90)) : 4;
    html += '<div class="kpi-bar-wrapper">';
    html += '<div class="kpi-bar-value">' + w.count + '</div>';
    html += '<div class="kpi-bar" style="height:' + h + 'px"></div>';
    html += '<div class="kpi-bar-label">' + w.label + '</div>';
    html += '</div>';
  });
  html += '</div></div>';

  // 5. Completion Rate Donut (full width)
  html += '<div class="kpi-card full-width" style="animation-delay:0.25s">';
  html += '<div class="kpi-card-label">Distribuição de Status</div>';
  html += '<div class="kpi-donut-container">';

  // SVG Donut
  html += '<svg class="kpi-donut" viewBox="0 0 80 80">';
  if (totalForDonut > 0) {
    let offset = 0;
    segments.forEach(seg => {
      if (seg.pct <= 0) return;
      const dash = seg.pct * circumference;
      const gap = circumference - dash;
      html += '<circle cx="40" cy="40" r="35" fill="none" stroke-width="8" '
        + 'stroke="' + seg.color + '" '
        + 'stroke-dasharray="' + dash.toFixed(2) + ' ' + gap.toFixed(2) + '" '
        + 'stroke-dashoffset="' + (-offset).toFixed(2) + '" '
        + 'transform="rotate(-90 40 40)"/>';
      offset += dash;
    });
  } else {
    html += '<circle cx="40" cy="40" r="35" fill="none" stroke-width="8" stroke="var(--border-subtle)"/>';
  }
  html += '</svg>';

  // Legend
  html += '<div class="kpi-donut-legend">';
  segments.forEach(seg => {
    if (seg.count <= 0) return;
    html += '<div class="kpi-legend-item">';
    html += '<div class="kpi-legend-dot" style="background:' + seg.color + '"></div>';
    html += seg.label + ' (' + seg.count + ')';
    html += '</div>';
  });
  html += '</div></div></div>';

  // 6. Category Distribution
  html += '<div class="kpi-card full-width" style="animation-delay:0.3s">';
  html += '<div class="kpi-card-label">Distribuição por Categoria</div>';
  categories.forEach(cat => {
    const count = catCounts[cat];
    const pct = maxCat > 0 ? Math.round((count / maxCat) * 100) : 0;
    html += '<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.4rem">';
    html += '<div style="width:8px;height:8px;border-radius:50%;background:' + CATEGORY_COLORS[cat] + ';flex-shrink:0"></div>';
    html += '<span style="font-size:0.75rem;color:var(--text-secondary);min-width:70px">' + cat + '</span>';
    html += '<div style="flex:1;height:6px;border-radius:3px;background:var(--bg-glass);overflow:hidden">';
    html += '<div style="height:100%;width:' + pct + '%;border-radius:3px;background:' + CATEGORY_COLORS[cat] + ';transition:width 0.6s ease"></div>';
    html += '</div>';
    html += '<span style="font-size:0.7rem;color:var(--text-muted);min-width:24px;text-align:right">' + count + '</span>';
    html += '</div>';
  });
  html += '</div>';

  // 7. Weekly Trend Sparkline (full width)
  html += '<div class="kpi-card full-width" style="animation-delay:0.35s">';
  html += '<div class="kpi-card-label">Tendência Semanal (Taxa de Conclusão)</div>';

  // Build SVG sparkline
  const svgW = 280;
  const svgH = 40;
  const maxRate = Math.max(...weeklyRates, 1);
  const points = weeklyRates.map((r, i) => {
    const x = (i / (weeklyRates.length - 1)) * svgW;
    const y = svgH - (r / 100) * svgH;
    return x.toFixed(1) + ',' + y.toFixed(1);
  });
  const areaPoints = points.join(' ') + ' ' + svgW + ',' + svgH + ' 0,' + svgH;

  html += '<svg class="kpi-sparkline" viewBox="0 0 ' + svgW + ' ' + svgH + '" preserveAspectRatio="none">';
  html += '<defs><linearGradient id="sparklineGrad" x1="0" y1="0" x2="0" y2="1">';
  html += '<stop offset="0%" stop-color="var(--amber)" stop-opacity="0.3"/>';
  html += '<stop offset="100%" stop-color="var(--amber)" stop-opacity="0.02"/>';
  html += '</linearGradient></defs>';
  html += '<polygon class="sparkline-area" points="' + areaPoints + '"/>';
  html += '<polyline points="' + points.join(' ') + '"/>';
  html += '</svg>';

  // Labels below sparkline
  html += '<div style="display:flex;justify-content:space-between;margin-top:0.15rem">';
  weeklyRates.forEach((r, i) => {
    html += '<span style="font-size:0.5rem;color:var(--text-muted)">' + r + '%</span>';
  });
  html += '</div>';

  html += '</div>';

  html += '</div>'; // close kpis-grid

  container.innerHTML = html;
}

// ========== PATCH: switchView to handle 'matrix', 'timeblock', 'kpis', 'metas', 'financas' ==========
const _originalSwitchView = switchView;
switchView = function(view) {
  const extraViews = ['matrixView','timeblockView','kpisView','metasView','financasView','adminView'];
  extraViews.forEach(id => { const el = document.getElementById(id); if(el) { el.classList.remove('active'); el.style.display = 'none'; } });

  const extraKeys = ['matrix','timeblock','kpis','metas','financas','admin'];
  if (extraKeys.includes(view)) {
    document.getElementById('tasksView').classList.add('hidden');
    document.getElementById('todayView').classList.remove('active');
    document.getElementById('calendarView').classList.remove('active');
    document.getElementById('reviewView').style.display = 'none';

    const viewMap = {
      matrix: { id: 'matrixView', fn: () => renderMatrix() },
      timeblock: { id: 'timeblockView', fn: () => renderTimeBlocks(timeblockSelectedDate) },
      kpis: { id: 'kpisView', fn: () => renderKPIs() },
      metas: { id: 'metasView', fn: () => renderMetas() },
      financas: { id: 'financasView', fn: () => renderFinancas() },
      admin: { id: 'adminView', fn: () => renderAdmin() },
    };
    const target = viewMap[view];
    const el = document.getElementById(target.id);
    el.style.display = 'block'; el.classList.add('active');
    target.fn();

    document.querySelectorAll('.view-toggle button').forEach(b => b.classList.toggle('active', b.dataset.view === view));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  } else {
    _originalSwitchView(view);
  }
};

