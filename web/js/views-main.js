// ========== RENDER ==========
function renderTasks() {
  const filtered = getFilteredTasks();
  const container = document.getElementById('taskList');
  const priorityOrder = { 'alta': 0, 'media': 1, 'baixa': 2 };
  const statusOrder = { 'em_andamento': 0, 'pendente': 1, 'concluida': 2 };

  filtered.sort((a, b) => {
    switch (currentSort) {
      case 'newest':
        return (b.created_at || b.criado_em || '').localeCompare(a.created_at || a.criado_em || '');
      case 'oldest':
        return (a.created_at || a.criado_em || '').localeCompare(b.created_at || b.criado_em || '');
      case 'deadline_asc':
        return (a.prazo || '9999').localeCompare(b.prazo || '9999');
      case 'deadline_desc':
        return (b.prazo || '').localeCompare(a.prazo || '');
      case 'priority': {
        if (priorityOrder[a.prioridade] !== priorityOrder[b.prioridade]) return priorityOrder[a.prioridade] - priorityOrder[b.prioridade];
        return (a.prazo || 'z').localeCompare(b.prazo || 'z');
      }
      default: // smart
        if (statusOrder[a.status] !== statusOrder[b.status]) return statusOrder[a.status] - statusOrder[b.status];
        const ao = isOverdue(a) ? 0 : 1, bo = isOverdue(b) ? 0 : 1;
        if (ao !== bo) return ao - bo;
        if (priorityOrder[a.prioridade] !== priorityOrder[b.prioridade]) return priorityOrder[a.prioridade] - priorityOrder[b.prioridade];
        return (a.prazo || 'z').localeCompare(b.prazo || 'z');
    }
  });

  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>Nenhuma tarefa ainda. Toque em + para criar a primeira!</p></div>';
    updateStats();
    return;
  }

  container.innerHTML = filtered.map((task, i) => {
    const catColor = CATEGORY_COLORS[task.categoria] || 'var(--text-muted)';
    const catBg = CATEGORY_BG[task.categoria] || 'rgba(255,255,255,0.05)';
    const priColor = PRIORITY_COLORS[task.prioridade];
    const completed = task.status === 'concluida' ? 'completed' : '';
    const overdueClass = isOverdue(task) ? 'overdue' : '';
    const meetingHTML = getMeetingBadgeHTML(task.meeting_link);
    const timeStr = task.horario || '';

    const inProgressClass = task.status === 'em_andamento' ? 'in-progress' : '';
    const selectedClass = selectedTasks.has(String(task.id)) ? 'selected' : '';

    const subBadge = getSubcategoryBadgeHTML(task);
    const tipoBadge = getTipoBadgeHTML(task);

    return `
      <div class="task-card ${completed} ${inProgressClass} ${selectedClass}" data-task-id="${task.id}" style="--cat-color:${catColor}; animation-delay:${i * 0.04}s" draggable="true" ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)">
        <div class="bulk-check" data-action="bulk-select"></div>
        <div class="task-check" data-action="toggle"></div>
        <div class="task-info" data-action="detail">
          <div class="task-title-row">
            <span class="task-title">${task.titulo}</span>
            <span class="task-category-badge" style="background:${catBg};color:${catColor}">${task.categoria}</span>
            ${subBadge}${tipoBadge}
          </div>
          <div class="task-meta">
            <span class="task-priority"><span class="dot" style="background:${priColor}"></span>${PRIORITY_LABELS[task.prioridade]}</span>
            ${timeStr ? '<span>' + timeStr + '</span>' : ''}
            ${task.tempo_estimado_min ? '<span>⏱' + task.tempo_estimado_min + 'min</span>' : ''}
            ${task.delegado_para ? '<span>👤' + task.delegado_para + '</span>' : ''}
            ${task.recorrencia ? '<span>🔄' + task.recorrencia + '</span>' : ''}
            ${meetingHTML}
          </div>
          ${getSubtaskProgressHTML(task.id)}
        </div>
        <div class="task-right">
          <span class="task-date-badge ${overdueClass}">${task.prazo ? formatDate(task.prazo) : ''}</span>
          <div class="task-actions">
            <button class="task-action-btn" data-action="edit" title="Editar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="task-action-btn delete" data-action="delete" title="Excluir">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>`;
  }).join('');

  updateStats();
  renderProgressRing();
}

// ========== EVENT DELEGATION (resolve problemas de UUID nos onclick) ==========
document.getElementById('taskList').addEventListener('click', function(e) {
  const card = e.target.closest('.task-card');
  if (!card) return;
  const taskId = card.dataset.taskId;
  if (!taskId) return;

  // Shift+Click entra em bulk mode
  if (e.shiftKey && !bulkMode) {
    enterBulkMode();
    toggleBulkSelect(taskId);
    return;
  }

  // Em bulk mode, qualquer clique seleciona
  if (bulkMode) {
    toggleBulkSelect(taskId);
    return;
  }

  const actionEl = e.target.closest('[data-action]');
  if (!actionEl) return;

  const action = actionEl.dataset.action;
  if (action === 'toggle') toggleTask(taskId);
  else if (action === 'delete') deleteTask(taskId);
  else if (action === 'edit') editTask(taskId);
  else if (action === 'detail') showTaskDetail(taskId);
  else if (action === 'bulk-select') { enterBulkMode(); toggleBulkSelect(taskId); }
});

// ========== ACTIONS (agora salvam no Supabase!) ==========

// ========== CONFIRM DIALOG (data diferente) ==========

function showConfirmDialog(icon, title, msg) {
  document.getElementById('confirmIcon').textContent = icon;
  document.getElementById('confirmTitle').textContent = title;
  document.getElementById('confirmMsg').innerHTML = msg;
  document.getElementById('confirmOverlay').classList.add('active');
  return new Promise(resolve => { _confirmResolve = resolve; });
}

function acceptConfirmDialog() {
  document.getElementById('confirmOverlay').classList.remove('active');
  if (_confirmResolve) { _confirmResolve(true); _confirmResolve = null; }
}

function cancelConfirmDialog() {
  document.getElementById('confirmOverlay').classList.remove('active');
  if (_confirmResolve) { _confirmResolve(false); _confirmResolve = null; }
}

function getDateLabel(dateStr) {
  const today = new Date(); today.setHours(0,0,0,0);
  const d = new Date(dateStr + 'T12:00:00'); d.setHours(0,0,0,0);
  const diff = Math.round((d - today) / 86400000);
  const formatted = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  if (diff === -1) return `ontem (${formatted})`;
  if (diff === 1) return `amanhã (${formatted})`;
  if (diff < -1) return `${Math.abs(diff)} dias atrás (${formatted})`;
  if (diff > 1) return `daqui a ${diff} dias (${formatted})`;
  return `hoje (${formatted})`;
}

async function toggleTask(id) {
  const task = tasks.find(t => String(t.id) === String(id));
  if (!task) return;
  // Hábitos usam fluxo próprio: marca/desmarca "feito hoje" sem encerrar a tarefa mãe
  if (task.eh_habito) {
    return toggleHabitToday(id);
  }
  const cycle = { 'pendente': 'em_andamento', 'em_andamento': 'concluida', 'concluida': 'pendente' };
  const oldStatus = task.status;
  const newStatus = cycle[oldStatus] || 'pendente';

  // Confirmar se vai concluir tarefa de outra data
  if (newStatus === 'concluida' && task.prazo) {
    const today = new Date().toISOString().split('T')[0];
    if (task.prazo !== today) {
      const label = getDateLabel(task.prazo);
      const confirmed = await showConfirmDialog(
        '📅',
        'Tarefa de outra data',
        `<strong>"${escapeHtml(task.titulo)}"</strong> está agendada para <strong>${escapeHtml(label)}</strong>.<br><br>Tem certeza que quer concluí-la agora?`
      );
      if (!confirmed) return;
    }
  }

  task.status = newStatus;
  renderTasks();
  renderToday();

  // Award XP when completing
  if (newStatus === 'concluida' && oldStatus !== 'concluida') {
    const xp = calculateXPForTask(task);
    await updateGamification(xp);
  }
  renderProgressRing();

  const ok = await updateTask(id, { status: newStatus });
  if (!ok) {
    task.status = oldStatus;
    renderTasks();
    renderToday();
  }
}

async function deleteTask(id) {
  if (!confirm('Excluir esta tarefa?')) return;

  const backup = [...tasks];
  tasks = tasks.filter(t => String(t.id) !== String(id));
  renderTasks();
  renderCalendar();
  renderToday();

  const ok = await removeTask(id);
  if (!ok) {
    tasks = backup;
    renderTasks();
    renderCalendar();
    renderToday();
  }
}

function editTask(id) {
  const task = tasks.find(t => String(t.id) === String(id));
  if (!task) return;

  editingTaskId = id;
  document.getElementById('inputTitle').value = task.titulo || '';
  document.getElementById('inputCategory').value = task.categoria || 'Trabalho';
  document.getElementById('inputPriority').value = task.prioridade || 'media';
  document.getElementById('inputDate').value = task.prazo || '';
  document.getElementById('inputTime').value = task.horario || '';
  document.getElementById('inputMeetingLink').value = task.meeting_link || '';
  document.getElementById('inputNotes').value = task.notas || '';
  document.getElementById('inputTipo').value = task.tipo || 'tarefa';
  document.getElementById('inputSubcategoria').value = task.subcategoria || '';
  toggleSubcategoryVisibility();

  document.querySelector('.modal h2').textContent = 'Editar tarefa';
  document.querySelector('.btn-save').textContent = 'Atualizar';
  document.getElementById('modalOverlay').classList.add('active');
  setTimeout(() => document.getElementById('inputTitle').focus(), 300);
}

// ========== CALENDAR ==========
// Remove tarefas que já aparecem como evento do Google (mesmo título + horário).
// Normaliza título (lowercase, trim, sem pontuação simples) e compara horário
// em HH:MM. Se houver match, a tarefa local é ocultada — mostramos só o evento.
function _normTitle(s) {
  return (s || '').toString().toLowerCase().trim().replace(/[.,!?;:()\[\]"]/g,'').replace(/\s+/g,' ');
}
function _normTime(s) {
  if (!s) return '';
  const m = String(s).match(/(\d{1,2}):(\d{2})/);
  return m ? (m[1].padStart(2,'0') + ':' + m[2]) : '';
}
function deduplicateTasksAgainstEvents(dayTasks, dayEvents) {
  if (!dayEvents || dayEvents.length === 0) return dayTasks;
  const eventKeys = new Set();
  dayEvents.forEach(ev => {
    const t = _normTitle(ev.titulo);
    const h = _normTime(ev.horario_inicio);
    eventKeys.add(t + '|' + h);
    eventKeys.add(t); // também match por título puro (evento all-day ou sem hora)
  });
  return dayTasks.filter(task => {
    const t = _normTitle(task.titulo);
    const h = _normTime(task.horario);
    if (eventKeys.has(t + '|' + h)) return false;
    if (h === '' && eventKeys.has(t)) return false;
    return true;
  });
}

function renderCalendar() {
  const weekDays = getWeekDays();
  const container = document.getElementById('calendarWeek');
  const MAX_VISIBLE = window.innerWidth >= 1024 ? 8 : 5;

  container.innerHTML = weekDays.map(day => {
    let dayTasks = tasks.filter(t => {
      if (t.eh_habito) return false; // hábitos ficam em seção própria abaixo
      if (t.status === 'concluida') return false;
      // Exact date match (cópias diárias já existem no banco, não expandir aqui)
      if (t.prazo === day.date) return true;
      // Weekly recurring: show on the matching day of week
      if (t.recorrencia === 'semanal' && t.recorrencia_dia != null) {
        const dayOfWeek = new Date(day.date + 'T12:00:00').getDay();
        const mappedDay = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        return mappedDay === t.recorrencia_dia;
      }
      return false;
    });
    // Hábitos: cards individuais só no dia de hoje, badge compacto nos outros dias
    const allHabits = tasks.filter(t => t.eh_habito);
    const dayHabits = day.isToday ? allHabits : [];
    const habitBadgeCount = !day.isToday ? allHabits.length : 0;
    const dayEvents = calendarEvents.filter(ev => ev.dia === day.date);
    // DEDUP: se uma tarefa tem o mesmo titulo+horario de um evento Google,
    // mostra só o evento (evita duplicata quando a tarefa foi sincronizada).
    dayTasks = deduplicateTasksAgainstEvents(dayTasks, dayEvents);
    dayTasks.sort((a, b) => (a.horario || 'zz').localeCompare(b.horario || 'zz'));
    dayEvents.sort((a, b) => (a.horario_inicio || 'zz').localeCompare(b.horario_inicio || 'zz'));
    const todayClass = day.isToday ? 'today' : '';
    const totalItems = dayTasks.length + dayEvents.length + dayHabits.length;
    const emptyClass = totalItems === 0 && habitBadgeCount === 0 ? 'empty-day' : '';

    // Merge events and tasks for display
    const allItems = [];
    dayEvents.forEach(ev => allItems.push({ type: 'event', data: ev, sortKey: ev.all_day ? '00:00' : (ev.horario_inicio || 'zz') }));
    dayTasks.forEach(t => allItems.push({ type: 'task', data: t, sortKey: t.horario || 'zz' }));
    dayHabits.forEach(t => allItems.push({ type: 'habit', data: t, sortKey: 'zzz' }));
    allItems.sort((a, b) => a.sortKey.localeCompare(b.sortKey));

    const visible = allItems.slice(0, MAX_VISIBLE);
    const remaining = totalItems - MAX_VISIBLE;

    return `
      <div class="calendar-day ${todayClass} ${emptyClass}" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleCalendarDrop(event, '${day.date}')">
        <div class="calendar-day-header">
          <span class="calendar-day-name">${day.name}</span>
          <span class="calendar-day-number">${day.number}</span>
        </div>
        <div class="calendar-day-tasks">
          ${visible.length === 0 ? '<div style="flex:1;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.65rem;opacity:0.5">Sem tarefas</div>' : ''}
          ${visible.map(item => {
            if (item.type === 'event') {
              return renderCalendarEvent(item.data);
            }
            if (item.type === 'habit') {
              const h = item.data;
              const done = day.isToday && isHabitDoneToday(h.id);
              return `<div class="calendar-task calendar-habit ${done ? 'habit-done' : ''}" style="--cat-color:#0075de" data-task-id="${h.id}">
                <div class="calendar-task-content">
                  <span class="calendar-task-title">🔁 ${h.titulo}</span>
                </div>
              </div>`;
            }
            const t = item.data;
            const platform = detectMeetingPlatform(t.meeting_link);
            const meetIcon = platform ? '<svg class="meeting-icon" viewBox="0 0 24 24" fill="none" stroke="' + platform.color + '" stroke-width="2"><path d="M15.5 10l4.72-3.36a1 1 0 011.78.63v9.46a1 1 0 01-1.78.63L15.5 14"/><rect x="2" y="6" width="13.5" height="12" rx="2"/></svg>' : '';
            const timeStr = t.horario || '';
            return `<div class="calendar-task" style="--cat-color:${CATEGORY_COLORS[t.categoria]}" data-task-id="${t.id}" draggable="true" ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)">
              <div class="calendar-task-content">
                ${timeStr ? '<span class="calendar-task-time">🕐 ' + timeStr + (platform ? ' ' + meetIcon + ' ' + platform.label : '') + '</span>' : (platform ? '<span class="calendar-task-time">' + meetIcon + ' ' + platform.label + '</span>' : '')}
                <span class="calendar-task-title">${t.titulo}</span>
                <span class="calendar-task-cat">${t.categoria}${t.recorrencia ? ' · 🔄 ' + t.recorrencia : ''}</span>
              </div>
            </div>`;
          }).join('')}
          ${remaining > 0 ? '<div class="calendar-task-count">+' + remaining + ' mais</div>' : ''}
          ${habitBadgeCount > 0 ? '<div class="calendar-task-count" style="color:var(--accent);opacity:0.7">🔁 ' + habitBadgeCount + ' hábito' + (habitBadgeCount > 1 ? 's' : '') + '</div>' : ''}
        </div>
      </div>`;
  }).join('');

  // Add "no date" tasks section
  const noDateTasks = tasks.filter(t => !t.prazo && t.status !== 'concluida');
  if (noDateTasks.length > 0) {
    container.innerHTML += `
      <div class="calendar-day no-date-column" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleCalendarDrop(event, '')">
        <div class="calendar-day-header">
          <span class="calendar-day-name">📌</span>
          <span class="calendar-day-number">Sem data</span>
        </div>
        <div class="calendar-day-tasks">
          ${noDateTasks.slice(0, 6).map(t => {
            return '<div class="calendar-task" style="--cat-color:' + (CATEGORY_COLORS[t.categoria] || 'var(--text-muted)') + '" data-task-id="' + t.id + '" draggable="true" ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)">' +
              '<div class="calendar-task-content">' +
              '<span class="calendar-task-title">' + t.titulo + '</span>' +
              '</div></div>';
          }).join('')}
          ${noDateTasks.length > 6 ? '<div class="calendar-task-count">+' + (noDateTasks.length - 6) + ' mais</div>' : ''}
        </div>
      </div>`;

    // Re-register click handlers for no-date column
    container.querySelectorAll('.no-date-column .calendar-task[data-task-id]').forEach(el => {
      el.addEventListener('click', () => showTaskDetail(el.dataset.taskId));
    });
  }

  // Clique nas tarefas do calendario
  container.querySelectorAll('.calendar-day:not(.no-date-column) .calendar-task[data-task-id]').forEach(el => {
    el.addEventListener('click', () => showTaskDetail(el.dataset.taskId));
  });

  // Clique nos eventos do calendario (agenda)
  container.querySelectorAll('.calendar-event[data-event-id]').forEach(el => {
    el.addEventListener('click', () => showEventDetail(el.dataset.eventId));
  });
}

// ========== TASK DETAIL (modal de detalhes) ==========
function showTaskDetail(id) {
  const task = tasks.find(t => String(t.id) === String(id));
  if (!task) return;

  const catColor = CATEGORY_COLORS[task.categoria] || 'var(--text-muted)';
  const catBg = CATEGORY_BG[task.categoria] || 'rgba(255,255,255,0.05)';
  const priColor = PRIORITY_COLORS[task.prioridade];
  const platform = detectMeetingPlatform(task.meeting_link);
  const statusLabels = { 'pendente': 'Pendente', 'em_andamento': 'Em andamento', 'concluida': 'Concluída' };

  let html = `
    <span class="detail-category" style="background:${catBg};color:${catColor}">${task.categoria}</span>
    <h2 class="detail-title">${task.titulo}</h2>
    <div class="detail-grid">
      <div>
        <div class="detail-field-label">Status</div>
        <div class="detail-field-value">${statusLabels[task.status] || task.status}</div>
      </div>
      <div>
        <div class="detail-field-label">Prioridade</div>
        <div class="detail-field-value" style="color:${priColor}">${PRIORITY_LABELS[task.prioridade]}</div>
      </div>
      <div>
        <div class="detail-field-label">Prazo</div>
        <div class="detail-field-value">${task.prazo ? formatDate(task.prazo) : 'Sem prazo'}</div>
      </div>
      <div>
        <div class="detail-field-label">Horário</div>
        <div class="detail-field-value">${task.horario || 'Sem horário'}</div>
      </div>
      ${task.tempo_estimado_min ? `<div>
        <div class="detail-field-label">Tempo estimado</div>
        <div class="detail-field-value">⏱ ${task.tempo_estimado_min}min</div>
      </div>` : ''}
      ${task.delegado_para ? `<div>
        <div class="detail-field-label">Delegado para</div>
        <div class="detail-field-value">👤 ${task.delegado_para}</div>
      </div>` : ''}
      ${task.recorrencia ? `<div>
        <div class="detail-field-label">Recorrência</div>
        <div class="detail-field-value">🔄 ${task.recorrencia}</div>
      </div>` : ''}
    </div>`;

  if (platform) {
    html += `<div style="margin-bottom:1rem">
      <a href="${task.meeting_link}" target="_blank" rel="noopener" class="meeting-badge ${platform.type}" style="font-size:0.75rem;padding:0.3rem 0.7rem">
        <svg class="meeting-icon" style="width:12px;height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15.5 10l4.72-3.36a1 1 0 011.78.63v9.46a1 1 0 01-1.78.63L15.5 14"/><rect x="2" y="6" width="13.5" height="12" rx="2"/></svg>
        ${platform.label}
      </a>
    </div>`;
  }

  if (task.notas) {
    html += `<div class="detail-notes">${task.notas}</div>`;
  }

  // Placeholder for subtasks — will be loaded async
  html += '<div id="detailSubtasksContainer"></div>';

  // Placeholder for attachments — will be loaded async
  html += '<div id="detailAttachmentsContainer"></div>';

  // Pomodoro section (only for non-completed tasks)
  if (task.status !== 'concluida') {
    const accumMin = getPomodoroAccumMinutes(task.id);
    html += `
    <div style="margin:1rem 0;padding:0.75rem;background:var(--bg-glass);border:1px solid var(--border-subtle);border-radius:var(--radius-sm)">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem">
        <div>
          <div style="font-size:0.75rem;font-weight:600;color:var(--text-primary);margin-bottom:0.2rem">🍅 Pomodoro</div>
          <div style="font-size:0.65rem;color:var(--text-secondary);line-height:1.4">Timer de 25 min de foco total. Ajuda a manter a concentração em uma tarefa por vez. O tempo é registrado automaticamente.</div>
          ${accumMin > 0 ? '<div style="font-size:0.65rem;color:var(--amber);margin-top:0.3rem">⏱ ' + accumMin + ' min acumulados nesta tarefa</div>' : ''}
        </div>
        <button onclick="closeDetail();startPomodoro('${task.id}')" style="flex-shrink:0;padding:0.4rem 0.8rem;background:rgba(0,117,222,0.08);border:1px solid var(--amber);border-radius:50px;color:var(--amber);font-size:0.7rem;font-family:inherit;cursor:pointer;display:flex;align-items:center;gap:0.3rem;transition:var(--transition)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Iniciar
        </button>
      </div>
    </div>`;
  }

  html += `
    <div class="detail-actions">
      <button class="detail-btn detail-btn-edit" onclick="closeDetail();editTask('${task.id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        Editar
      </button>
      <button class="detail-btn detail-btn-delete" onclick="closeDetail();deleteTask('${task.id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        Excluir
      </button>
      <button class="detail-btn detail-btn-close" onclick="closeDetail()">Fechar</button>
    </div>`;

  document.getElementById('detailContent').innerHTML = html;
  document.getElementById('detailOverlay').classList.add('active');

  // Load subtasks asynchronously
  loadSubtasksForTask(task.id).then(subtasks => {
    const container = document.getElementById('detailSubtasksContainer');
    if (container) {
      container.innerHTML = renderSubtasksSection(task.id, subtasks);
    }
  });

  // Load attachments asynchronously
  loadAttachments(task.id).then(attachments => {
    const container = document.getElementById('detailAttachmentsContainer');
    if (container) {
      container.innerHTML = renderAttachmentsSection(task.id, attachments);
    }
  });
}

function showEventDetail(id) {
  const ev = calendarEvents.find(e => String(e.id) === String(id));
  if (!ev) return;

  const provider = ev.provider || 'google';
  const providerLabel = provider === 'microsoft' ? 'Microsoft Teams/Outlook' : 'Google Calendar';
  const providerColor = provider === 'microsoft' ? 'hsl(215, 70%, 55%)' : 'hsl(142, 52%, 45%)';
  const timeStr = ev.all_day ? 'Dia todo' : ((ev.horario_inicio || '') + (ev.horario_fim ? ' — ' + ev.horario_fim : ''));

  let html = `
    <span class="detail-category" style="background:rgba(255,255,255,0.05);color:${providerColor}">${providerLabel}</span>
    <h2 class="detail-title">${escapeHtml(ev.titulo)}</h2>
    <div class="detail-grid">
      <div>
        <div class="detail-field-label">Data</div>
        <div class="detail-field-value">${ev.dia ? formatDate(ev.dia) : 'Sem data'}</div>
      </div>
      <div>
        <div class="detail-field-label">Horário</div>
        <div class="detail-field-value">${timeStr || 'Sem horário'}</div>
      </div>
      ${ev.local ? `<div>
        <div class="detail-field-label">Local</div>
        <div class="detail-field-value">📍 ${ev.local}</div>
      </div>` : ''}
    </div>`;

  if (ev.descricao) {
    html += `<div class="detail-notes">${escapeHtml(ev.descricao)}</div>`;
  }

  if (ev.meeting_link) {
    html += `<div style="margin:1rem 0">
      <a href="${ev.meeting_link}" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:0.4rem;padding:0.5rem 1rem;background:${providerColor};color:white;border-radius:8px;text-decoration:none;font-size:0.8rem;font-weight:500">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M15.5 10l4.72-3.36a1 1 0 011.78.63v9.46a1 1 0 01-1.78.63L15.5 14"/><rect x="2" y="6" width="13.5" height="12" rx="2"/></svg>
        Entrar na reunião
      </a>
    </div>`;
  }

  html += `
    <div class="detail-actions">
      <button class="detail-btn detail-btn-close" onclick="closeDetail()">Fechar</button>
    </div>`;

  document.getElementById('detailContent').innerHTML = html;
  document.getElementById('detailOverlay').classList.add('active');
}

function closeDetail(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('detailOverlay').classList.remove('active');
}

// ========== TODAY VIEW ==========

function renderToday() {
  const hoje = new Date().toISOString().split('T')[0];
  // Tarefas normais (não hábitos) agendadas para hoje
  const todayTasks = tasks.filter(t => !t.eh_habito && t.prazo === hoje && t.status !== 'concluida');
  const todayDone = tasks.filter(t => !t.eh_habito && t.prazo === hoje && t.status === 'concluida');
  const overdue = tasks.filter(t => !t.eh_habito && t.prazo && t.prazo < hoje && t.status !== 'concluida');
  // Hábitos pendentes de hoje (ainda não marcados)
  const habitsPending = tasks.filter(t => t.eh_habito && !isHabitDoneToday(t.id));
  const habitsDone = tasks.filter(t => t.eh_habito && isHabitDoneToday(t.id));
  const todayEvents = calendarEvents.filter(ev => ev.dia === hoje);

  todayTasks.sort((a, b) => (a.horario || 'zz').localeCompare(b.horario || 'zz'));

  const header = document.getElementById('todayHeader');
  const totalHabitos = habitsPending.length + habitsDone.length;
  const total = todayTasks.length + overdue.length + totalHabitos;
  let headerHTML = `📅 Hoje — ${todayTasks.length} tarefa${todayTasks.length !== 1 ? 's' : ''}`;
  if (totalHabitos) headerHTML += ` · ${totalHabitos} hábito${totalHabitos !== 1 ? 's' : ''} (${habitsDone.length}/${totalHabitos})`;
  if (todayEvents.length) headerHTML += ` · ${todayEvents.length} evento${todayEvents.length !== 1 ? 's' : ''}`;
  headerHTML += (todayDone.length ? ` · ${todayDone.length} concluída${todayDone.length !== 1 ? 's' : ''}` : '');
  headerHTML += (overdue.length ? ` · <span style="color:var(--pri-alta)">${overdue.length} atrasada${overdue.length !== 1 ? 's' : ''}</span>` : '');
  headerHTML += ` <span class="today-count">${total}</span>`;
  headerHTML += `<div class="today-view-toggle">
        <button class="${todayViewMode === 'list' ? 'active' : ''}" onclick="todayViewMode='list';renderToday()">Lista</button>
        <button class="${todayViewMode === 'timeline' ? 'active' : ''}" onclick="todayViewMode='timeline';renderToday()">Timeline</button>
      </div>`;

  // Integration status chips
  if (calendarConnections.google || calendarConnections.microsoft) {
    headerHTML += '<div class="integrations-status">';
    if (calendarConnections.google) headerHTML += '<span class="integration-chip connected"><span class="integration-dot"></span>Google</span>';
    if (calendarConnections.microsoft) headerHTML += '<span class="integration-chip connected"><span class="integration-dot"></span>Microsoft</span>';
    headerHTML += '</div>';
  }

  header.innerHTML = headerHTML;

  const container = document.getElementById('todayTaskList');
  // Hábitos no topo, depois atrasadas, depois hoje pendentes, depois hábitos feitos, depois concluídas hoje
  const allTasks = [...habitsPending, ...overdue, ...todayTasks, ...habitsDone, ...todayDone];

  if (allTasks.length === 0 && todayEvents.length === 0) {
    container.innerHTML = '<div class="today-empty"><p>Nenhuma tarefa para hoje! Aproveite o dia.</p></div>';
    return;
  }

  if (todayViewMode === 'timeline') {
    container.innerHTML = renderTimeline(allTasks, hoje, todayEvents);
    container.querySelectorAll('.timeline-item[data-task-id]').forEach(el => {
      el.addEventListener('click', () => showTaskDetail(el.dataset.taskId));
    });
    return;
  }

  // Merge tasks and events into unified timeline
  const timeline = [];
  allTasks.forEach(t => {
    timeline.push({ type: 'task', data: t, sortKey: t.horario || 'zz' });
  });
  todayEvents.forEach(ev => {
    timeline.push({ type: 'event', data: ev, sortKey: ev.all_day ? '00:00' : (ev.horario_inicio || 'zz') });
  });
  timeline.sort((a, b) => a.sortKey.localeCompare(b.sortKey));

  let idx = 0;
  container.innerHTML = timeline.map(item => {
    if (item.type === 'event') {
      return renderEventCard(item.data, idx++ * 0.04);
    }
    const task = item.data;
    const catColor = CATEGORY_COLORS[task.categoria] || 'var(--text-muted)';
    const catBg = CATEGORY_BG[task.categoria] || 'rgba(255,255,255,0.05)';
    const priColor = PRIORITY_COLORS[task.prioridade];
    const isHabit = !!task.eh_habito;
    const habitDone = isHabit && isHabitDoneToday(task.id);
    const overdueClass = (!isHabit && isOverdue(task)) ? 'overdue' : '';
    const meetingHTML = getMeetingBadgeHTML(task.meeting_link);
    const timeStr = task.horario || '';
    const isLate = !isHabit && task.prazo < hoje;
    const inProgressClass = task.status === 'em_andamento' ? 'in-progress' : '';
    const completedClass = (habitDone || task.status === 'concluida') ? 'completed' : '';
    const selectedClass = selectedTasks.has(String(task.id)) ? 'selected' : '';
    const streak = isHabit ? getHabitStreak(task.id) : 0;
    const i = idx++;

    return `
      <div class="task-card ${inProgressClass} ${completedClass} ${selectedClass}" data-task-id="${task.id}" style="--cat-color:${catColor}; animation-delay:${i * 0.04}s">
        <div class="bulk-check" data-action="bulk-select"></div>
        <div class="task-check" data-action="toggle"></div>
        <div class="task-info" data-action="detail">
          <div class="task-title-row">
            <span class="task-title">${task.titulo}</span>
            <span class="task-category-badge" style="background:${catBg};color:${catColor}">${task.categoria}</span>
            ${isHabit ? '<span class="task-category-badge" style="background:rgba(0,117,222,0.1);color:#0075de">🔁 Hábito</span>' : ''}
          </div>
          <div class="task-meta">
            <span class="task-priority"><span class="dot" style="background:${priColor}"></span>${PRIORITY_LABELS[task.prioridade]}</span>
            ${timeStr ? '<span>🕐 ' + timeStr + '</span>' : ''}
            ${isLate ? '<span style="color:var(--pri-alta)">⚠️ Atrasada</span>' : ''}
            ${isHabit && streak > 0 ? '<span>🔥 ' + streak + ' ' + (streak === 1 ? 'dia' : 'dias') + '</span>' : ''}
            ${meetingHTML}
          </div>
          ${!isHabit ? getSubtaskProgressHTML(task.id) : ''}
        </div>
        <div class="task-right">
          <span class="task-date-badge ${overdueClass}">${task.prazo ? formatDate(task.prazo) : ''}</span>
          <div class="task-actions">
            <button class="task-action-btn" data-action="edit" title="Editar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="task-action-btn delete" data-action="delete" title="Excluir">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>`;
  }).join('');
}

// Event delegation para todayTaskList tambem
document.getElementById('todayTaskList').addEventListener('click', function(e) {
  const card = e.target.closest('.task-card');
  if (!card) return;
  const taskId = card.dataset.taskId;
  if (!taskId) return;

  if (e.shiftKey && !bulkMode) { enterBulkMode(); toggleBulkSelect(taskId); return; }
  if (bulkMode) { toggleBulkSelect(taskId); return; }

  const actionEl = e.target.closest('[data-action]');
  if (!actionEl) return;
  const action = actionEl.dataset.action;
  if (action === 'toggle') toggleTask(taskId);
  else if (action === 'delete') deleteTask(taskId);
  else if (action === 'edit') editTask(taskId);
  else if (action === 'detail') showTaskDetail(taskId);
  else if (action === 'bulk-select') { enterBulkMode(); toggleBulkSelect(taskId); }
});

// ========== VIEW SWITCH ==========
function switchView(view) {
  if (bulkMode) exitBulkMode();
  document.querySelectorAll('.view-toggle button').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));

  const tv = document.getElementById('tasksView');
  const todayV = document.getElementById('todayView');
  const cv = document.getElementById('calendarView');
  const rv = document.getElementById('reviewView');

  tv.classList.add('hidden');
  todayV.classList.remove('active');
  cv.classList.remove('active');
  rv.style.display = 'none';

  if (view === 'tasks') {
    tv.classList.remove('hidden');
  } else if (view === 'today') {
    todayV.classList.add('active');
    renderToday();
  } else if (view === 'review') {
    rv.style.display = 'block';
    renderReview();
  } else {
    cv.classList.add('active');
    renderCalendar();
  }
}

// ========== MODAL ==========
function openModal() {
  editingTaskId = null;
  document.querySelector('.modal h2').textContent = 'Nova tarefa';
  document.querySelector('.btn-save').textContent = 'Salvar';
  document.getElementById('modalOverlay').classList.add('active');
  setTimeout(() => document.getElementById('inputTitle').focus(), 300);
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('inputDate').value = tomorrow.toISOString().split('T')[0];
  document.getElementById('inputTipo').value = 'tarefa';
  document.getElementById('inputSubcategoria').value = '';
  toggleSubcategoryVisibility();
}

function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('modalOverlay').classList.remove('active');
  document.getElementById('taskForm').reset();
  editingTaskId = null;
  document.querySelector('.modal h2').textContent = 'Nova tarefa';
  document.querySelector('.btn-save').textContent = 'Salvar';
}

async function saveTask(event) {
  event.preventDefault();

  const meetingLink = document.getElementById('inputMeetingLink').value || '';
  const platform = detectMeetingPlatform(meetingLink);

  const categoria = document.getElementById('inputCategory').value;
  const tipo = document.getElementById('inputTipo').value || 'tarefa';
  const taskData = {
    titulo: document.getElementById('inputTitle').value,
    categoria: categoria,
    prioridade: document.getElementById('inputPriority').value,
    prazo: document.getElementById('inputDate').value || null,
    horario: document.getElementById('inputTime').value || null,
    meeting_link: meetingLink,
    meeting_platform: platform ? platform.type : null,
    notas: document.getElementById('inputNotes').value,
    tipo: tipo,
    subcategoria: categoria === 'Pessoal' ? (document.getElementById('inputSubcategoria').value || null) : null,
    eh_habito: (tipo === 'habito' || tipo === 'rotina') ? true : false,
  };

  closeModal();

  if (editingTaskId) {
    // EDITANDO tarefa existente
    const ok = await updateTask(editingTaskId, taskData);
    if (ok) {
      const task = tasks.find(t => String(t.id) === String(editingTaskId));
      if (task) {
        Object.assign(task, taskData);
        task.horario = taskData.horario ? taskData.horario.substring(0, 5) : '';
      }
      renderTasks();
      renderCalendar();
      renderToday();
    }
    editingTaskId = null;
  } else {
    // CRIANDO nova tarefa
    taskData.status = 'pendente';
    taskData.origem = 'dashboard';
    const created = await createTask(taskData);
    if (created) {
      tasks.unshift({ ...created, horario: created.horario ? created.horario.substring(0, 5) : '' });
      renderTasks();
      renderCalendar();
      renderToday();
    }
  }
}

// ========== TIMELINE ==========
function renderTimeline(allTasks, hoje, todayEvents) {
  // Merge tasks and events into timeline items
  const timelineItems = [];

  allTasks.filter(t => t.horario).forEach(t => {
    timelineItems.push({ type: 'task', data: t, time: t.horario });
  });

  (todayEvents || []).filter(ev => !ev.all_day && ev.horario_inicio).forEach(ev => {
    timelineItems.push({ type: 'event', data: ev, time: ev.horario_inicio });
  });

  timelineItems.sort((a, b) => a.time.localeCompare(b.time));

  const withoutTime = allTasks.filter(t => !t.horario);
  const allDayEvents = (todayEvents || []).filter(ev => ev.all_day);

  const now = new Date();
  const nowStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  let nowInserted = false;

  let html = '<div class="timeline">';

  // All-day events at the top
  if (allDayEvents.length > 0) {
    html += '<div class="allday-events-banner" style="margin-bottom:0.75rem">';
    allDayEvents.forEach(ev => {
      const provider = ev.provider || 'google';
      html += '<span class="allday-event-chip ' + provider + '">';
      html += '<span class="event-badge ' + provider + '" style="margin-left:0">' + (provider === 'microsoft' ? 'Teams' : 'Google') + '</span> ';
      html += escapeHtml(ev.titulo);
      html += '</span>';
    });
    html += '</div>';
  }

  timelineItems.forEach(item => {
    // Insert "now" indicator before the first item after current time
    if (!nowInserted && item.time > nowStr) {
      html += `<div class="timeline-now">Agora — ${nowStr}</div>`;
      nowInserted = true;
    }

    if (item.type === 'event') {
      const ev = item.data;
      const provider = ev.provider || 'google';
      const badge = `<span class="event-badge ${provider}">${provider === 'microsoft' ? 'Teams' : 'Google'}</span>`;
      let meetLink = '';
      if (ev.meeting_link) {
        const platform = ev.meeting_platform || 'generic';
        meetLink = ` <a href="${ev.meeting_link}" target="_blank" class="event-meeting-link ${platform}" onclick="event.stopPropagation()" style="font-size:0.55rem">Entrar</a>`;
      }
      html += `<div class="timeline-item" style="--cat-color:${provider === 'microsoft' ? 'hsl(215,70%,55%)' : 'hsl(142,52%,45%)'}">
        <span class="timeline-time">${ev.horario_inicio} - ${ev.horario_fim || ''}</span>
        <div class="timeline-title">${escapeHtml(ev.titulo)} ${badge}</div>
        <div class="timeline-meta">
          <span>${ev.local_evento || provider.charAt(0).toUpperCase() + provider.slice(1)}</span>
          ${meetLink}
        </div>
      </div>`;
    } else {
      const task = item.data;
      const catColor = CATEGORY_COLORS[task.categoria] || 'var(--text-muted)';
      html += `<div class="timeline-item" data-task-id="${task.id}" style="--cat-color:${catColor}">
        <span class="timeline-time">${task.horario}</span>
        <div class="timeline-title">${task.titulo}</div>
        <div class="timeline-meta">
          <span style="color:${catColor}">${task.categoria}</span>
          ${task.tempo_estimado_min ? '<span>⏱ ' + task.tempo_estimado_min + 'min</span>' : ''}
          ${task.prazo < hoje ? '<span style="color:var(--pri-alta)">Atrasada</span>' : ''}
        </div>
      </div>`;
    }
  });

  // If "now" hasn't been inserted yet (all items are before current time)
  if (!nowInserted && timelineItems.length > 0) {
    html += `<div class="timeline-now">Agora — ${nowStr}</div>`;
  }

  if (withoutTime.length > 0) {
    html += `<div style="margin-top:1rem;padding:0.5rem 0;font-size:0.75rem;color:var(--text-muted);border-top:1px solid var(--border-subtle)">Sem horário definido</div>`;
    withoutTime.forEach(task => {
      const catColor = CATEGORY_COLORS[task.categoria] || 'var(--text-muted)';
      html += `<div class="timeline-item" data-task-id="${task.id}" style="--cat-color:${catColor}">
        <div class="timeline-title">${task.titulo}</div>
        <div class="timeline-meta">
          <span style="color:${catColor}">${task.categoria}</span>
          ${task.tempo_estimado_min ? '<span>⏱ ' + task.tempo_estimado_min + 'min</span>' : ''}
          ${task.prazo < hoje ? '<span style="color:var(--pri-alta)">Atrasada</span>' : ''}
        </div>
      </div>`;
    });
  }

  // If no items with time, and now indicator needed
  if (timelineItems.length === 0) {
    html += `<div class="timeline-now">Agora — ${nowStr}</div>`;
  }

  html += '</div>';
  return html;
}

// ========== BULK MODE ==========

function toggleBulkMode() {
  if (bulkMode) {
    exitBulkMode();
  } else {
    enterBulkMode();
  }
}

function enterBulkMode() {
  bulkMode = true;
  document.querySelector('.main').classList.add('bulk-mode');
  document.getElementById('bulkBar').classList.add('active');
  const btn = document.getElementById('bulkToggleBtn');
  if (btn) btn.classList.add('active');
  updateBulkCount();
}

function exitBulkMode() {
  bulkMode = false;
  selectedTasks.clear();
  document.querySelector('.main').classList.remove('bulk-mode');
  document.getElementById('bulkBar').classList.remove('active');
  document.querySelectorAll('.task-card.selected').forEach(c => c.classList.remove('selected'));
  const btn = document.getElementById('bulkToggleBtn');
  if (btn) btn.classList.remove('active');
  updateBulkCount();
}

function toggleBulkSelect(taskId) {
  const id = String(taskId);
  if (selectedTasks.has(id)) {
    selectedTasks.delete(id);
  } else {
    selectedTasks.add(id);
  }
  // Update card visual
  document.querySelectorAll(`.task-card[data-task-id="${taskId}"]`).forEach(c => {
    c.classList.toggle('selected', selectedTasks.has(id));
  });
  updateBulkCount();
  if (selectedTasks.size === 0) exitBulkMode();
}

function updateBulkCount() {
  document.getElementById('bulkCount').textContent = selectedTasks.size;
}

async function bulkComplete() {
  const ids = [...selectedTasks];
  for (const id of ids) {
    const task = tasks.find(t => String(t.id) === id);
    if (task) {
      task.status = 'concluida';
      await updateTask(id, { status: 'concluida' });
    }
  }
  exitBulkMode();
  renderTasks();
  renderToday();
  renderCalendar();
}

async function bulkDelete() {
  if (!confirm(`Excluir ${selectedTasks.size} tarefa(s)?`)) return;
  const ids = [...selectedTasks];
  for (const id of ids) {
    await removeTask(id);
    tasks = tasks.filter(t => String(t.id) !== id);
  }
  exitBulkMode();
  renderTasks();
  renderToday();
  renderCalendar();
}

// ========== REVIEW VIEW ==========
function renderReview() {
  const weekDays = getWeekDaysForOffset(reviewWeekOffset);
  const weekStart = weekDays[0].date;
  const weekEnd = weekDays[6].date;

  document.getElementById('reviewPeriod').textContent = `${formatDate(weekStart)} — ${formatDate(weekEnd)}`;

  // Update history nav label
  const navLabel = document.getElementById('historyNavLabel');
  if (navLabel) {
    navLabel.textContent = reviewWeekOffset === 0 ? 'Semana atual' : (reviewWeekOffset === -1 ? 'Semana passada' : formatDate(weekStart) + ' — ' + formatDate(weekEnd));
  }

  // Load annotation for this week
  loadWeekAnnotation(weekStart).then(text => {
    const ann = document.getElementById('weekAnnotation');
    if (ann) ann.value = text;
  });

  // Load history list
  loadWeekHistoryList();

  // Render habit tracker
  renderHabitTracker();

  const weekTasks = tasks.filter(t => t.prazo >= weekStart && t.prazo <= weekEnd);
  const totalWeek = weekTasks.length;
  const completedWeek = weekTasks.filter(t => t.status === 'concluida').length;
  const pendingWeek = weekTasks.filter(t => t.status === 'pendente').length;
  const inProgressWeek = weekTasks.filter(t => t.status === 'em_andamento').length;
  const overdueWeek = weekTasks.filter(t => isOverdue(t)).length;
  const completionRate = totalWeek > 0 ? Math.round((completedWeek / totalWeek) * 100) : 0;

  // Category distribution
  const categories = ['Trabalho', 'Consultoria', 'Grupo Ser', 'Pessoal'];
  const catCounts = {};
  categories.forEach(c => { catCounts[c] = weekTasks.filter(t => t.categoria === c).length; });
  const maxCatCount = Math.max(...Object.values(catCounts), 1);

  // Priority distribution
  const priCounts = { 'alta': 0, 'media': 0, 'baixa': 0 };
  weekTasks.forEach(t => { if (priCounts[t.prioridade] !== undefined) priCounts[t.prioridade]++; });

  // Heatmap (last 7 days completed)
  const heatmapData = weekDays.map(day => {
    return tasks.filter(t => t.prazo === day.date && t.status === 'concluida').length;
  });
  const maxHeat = Math.max(...heatmapData, 1);

  // Average estimated time
  const tasksWithTime = weekTasks.filter(t => t.tempo_estimado_min);
  const avgTime = tasksWithTime.length > 0 ? Math.round(tasksWithTime.reduce((s, t) => s + t.tempo_estimado_min, 0) / tasksWithTime.length) : 0;

  // Personal time check
  const personalTasks = weekTasks.filter(t => t.categoria === 'Pessoal');
  const personalKeywords = ['ingles', 'leitura', 'academia', 'exercicio', 'estudo', 'saude'];
  const personalHighlights = personalTasks.filter(t => personalKeywords.some(k => (t.titulo || '').toLowerCase().includes(k)));

  let html = `
    <div class="review-grid">
      <div class="review-card">
        <h3>Total da semana</h3>
        <div class="review-big-number">${totalWeek}</div>
      </div>
      <div class="review-card">
        <h3>Concluídas</h3>
        <div class="review-big-number" style="color:var(--cat-pessoal)">${completedWeek}</div>
      </div>
      <div class="review-card">
        <h3>Pendentes</h3>
        <div class="review-big-number" style="color:var(--pri-media)">${pendingWeek + inProgressWeek}</div>
      </div>
      <div class="review-card">
        <h3>Atrasadas</h3>
        <div class="review-big-number" style="color:var(--pri-alta)">${overdueWeek}</div>
      </div>
    </div>

    <div class="review-card" style="margin-bottom:0.75rem">
      <h3>Taxa de conclusão</h3>
      <div class="review-big-number">${completionRate}%</div>
      <div class="review-bar">
        <div class="review-bar-fill" style="width:${completionRate}%;background:var(--cat-pessoal)"></div>
      </div>
    </div>

    <div class="review-card" style="margin-bottom:0.75rem">
      <h3>Por categoria</h3>
      ${categories.map(cat => {
        const count = catCounts[cat];
        const pct = maxCatCount > 0 ? Math.round((count / maxCatCount) * 100) : 0;
        return `<div class="review-category-row">
          <div style="width:8px;height:8px;border-radius:50%;background:${CATEGORY_COLORS[cat]};flex-shrink:0"></div>
          <span class="review-category-name">${cat}</span>
          <div class="review-category-bar">
            <div class="review-bar"><div class="review-bar-fill" style="width:${pct}%;background:${CATEGORY_COLORS[cat]}"></div></div>
          </div>
          <span class="review-category-count">${count}</span>
        </div>`;
      }).join('')}
    </div>

    <div class="review-card" style="margin-bottom:0.75rem">
      <h3>Por prioridade</h3>
      ${['alta', 'media', 'baixa'].map(pri => {
        const count = priCounts[pri];
        const pct = totalWeek > 0 ? Math.round((count / totalWeek) * 100) : 0;
        return `<div class="review-category-row">
          <div style="width:8px;height:8px;border-radius:50%;background:${PRIORITY_COLORS[pri]};flex-shrink:0"></div>
          <span class="review-category-name">${PRIORITY_LABELS[pri]}</span>
          <div class="review-category-bar">
            <div class="review-bar"><div class="review-bar-fill" style="width:${pct}%;background:${PRIORITY_COLORS[pri]}"></div></div>
          </div>
          <span class="review-category-count">${count}</span>
        </div>`;
      }).join('')}
    </div>

    <div class="review-card" style="margin-bottom:0.75rem">
      <h3>Heatmap da semana</h3>
      <div class="heatmap">
        ${weekDays.map((day, i) => {
          const count = heatmapData[i];
          let level = 0;
          if (count > 0) level = Math.min(4, Math.ceil((count / maxHeat) * 4));
          return `<div class="heatmap-cell level-${level}" title="${day.name}: ${count} concluída(s)"></div>`;
        }).join('')}
      </div>
      <div class="heatmap" style="gap:3px">
        ${weekDays.map(day => `<div class="heatmap-label">${day.name}</div>`).join('')}
      </div>
    </div>

    <div class="review-grid">
      <div class="review-card">
        <h3>Tempo médio estimado</h3>
        <div class="review-big-number">${avgTime}<span style="font-size:0.8rem;color:var(--text-secondary)">min</span></div>
      </div>
      <div class="review-card">
        <h3>Tempo pessoal</h3>
        <div class="review-big-number">${personalHighlights.length}</div>
        <div style="font-size:0.7rem;color:var(--text-secondary);margin-top:0.25rem">
          ${personalHighlights.length > 0 ? personalHighlights.map(t => t.titulo).join(', ') : 'Nenhuma atividade pessoal registrada'}
        </div>
      </div>
    </div>`;

  document.getElementById('reviewContent').innerHTML = html;
}

// ========== THEME TOGGLE ==========
function toggleTheme() {
  document.body.classList.toggle('dark-mode');
  const isDark = document.body.classList.contains('dark-mode');
  document.getElementById('themeIcon').textContent = isDark ? '☀️' : '🌙';
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// ========== KEYBOARD ==========
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeModal(); closeDetail(); }
  if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) openModal();
});

