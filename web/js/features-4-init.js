// ========== FEATURE: SUBTAREFAS (SUBTASKS) ==========


async function loadSubtaskCounts() {
  try {
    const { data, error } = await sb
      .from('subtarefas')
      .select('tarefa_id,concluida');

    if (error) {
      console.warn('Erro ao carregar subtarefas:', error);
      return;
    }

    subtaskCache = {};
    (data || []).forEach(s => {
      if (!subtaskCache[s.tarefa_id]) {
        subtaskCache[s.tarefa_id] = { total: 0, done: 0 };
      }
      subtaskCache[s.tarefa_id].total++;
      if (s.concluida) subtaskCache[s.tarefa_id].done++;
    });
  } catch (e) {
    console.warn('Erro ao carregar contagem de subtarefas:', e);
  }
}

function getSubtaskProgressHTML(taskId) {
  const info = subtaskCache[taskId];
  if (!info || info.total === 0) return '';
  const pct = Math.round((info.done / info.total) * 100);
  return '<div class="subtask-progress">'
    + '<div class="subtask-bar"><div class="subtask-bar-fill" style="width:' + pct + '%"></div></div>'
    + '<span class="subtask-count">' + info.done + '/' + info.total + '</span>'
    + '</div>';
}

async function loadSubtasksForTask(taskId) {
  try {
    const { data, error } = await sb
      .from('subtarefas')
      .select('*')
      .eq('tarefa_id', taskId)
      .order('ordem', { ascending: true });

    if (error) {
      console.warn('Erro ao carregar subtarefas da tarefa:', error);
      return [];
    }
    return data || [];
  } catch (e) {
    console.warn('Erro ao carregar subtarefas:', e);
    return [];
  }
}

function renderSubtasksSection(taskId, subtasks) {
  let html = '<div class="detail-subtasks">'
    + '<div class="detail-subtasks-header">'
    + '<span class="detail-subtasks-title">Subtarefas</span>'
    + '<button class="detail-subtask-add" onclick="showSubtaskInput(\'' + taskId + '\')">+ Adicionar</button>'
    + '</div>'
    + '<div id="subtaskList">';

  subtasks.forEach(s => {
    const doneClass = s.concluida ? ' done' : '';
    const checkDone = s.concluida ? ' done' : '';
    html += '<div class="subtask-item' + doneClass + '" data-subtask-id="' + s.id + '">'
      + '<div class="subtask-check' + checkDone + '" onclick="toggleSubtask(\'' + s.id + '\',' + !s.concluida + ',\'' + taskId + '\')"></div>'
      + '<span class="subtask-text">' + s.titulo + '</span>'
      + '<button class="subtask-delete" onclick="deleteSubtask(\'' + s.id + '\',\'' + taskId + '\')">\u2715</button>'
      + '</div>';
  });

  html += '</div>'
    + '<div id="subtaskInputContainer"></div>'
    + '</div>';
  return html;
}

function showSubtaskInput(taskId) {
  const container = document.getElementById('subtaskInputContainer');
  if (!container || container.querySelector('.subtask-input')) return;

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'subtask-input';
  input.placeholder = 'Nova subtarefa...';
  input.addEventListener('keydown', async function(e) {
    if (e.key === 'Enter' && this.value.trim()) {
      const titulo = this.value.trim();
      this.disabled = true;
      await addSubtask(taskId, titulo);
      this.remove();
    } else if (e.key === 'Escape') {
      this.remove();
    }
  });
  container.appendChild(input);
  input.focus();
}

async function addSubtask(taskId, titulo) {
  const subtasks = await loadSubtasksForTask(taskId);
  const ordem = subtasks.length;

  try {
    const { error } = await sb
      .from('subtarefas')
      .insert({ tarefa_id: taskId, titulo: titulo, ordem: ordem });

    if (error) {
      console.error('Erro ao adicionar subtarefa:', error);
      return;
    }
  } catch (e) {
    console.error('Erro ao adicionar subtarefa:', e);
    return;
  }

  // Refresh
  await loadSubtaskCounts();
  const updated = await loadSubtasksForTask(taskId);
  const listEl = document.getElementById('subtaskList');
  if (listEl) {
    listEl.parentElement.outerHTML = renderSubtasksSection(taskId, updated);
  }
  renderTasks();
  renderToday();
}

async function toggleSubtask(subtaskId, newValue, taskId) {
  try {
    const { error } = await sb
      .from('subtarefas')
      .update({ concluida: newValue })
      .eq('id', subtaskId);

    if (error) {
      console.error('Erro ao atualizar subtarefa:', error);
      return;
    }
  } catch (e) {
    console.error('Erro ao atualizar subtarefa:', e);
    return;
  }

  // Refresh
  await loadSubtaskCounts();
  const updated = await loadSubtasksForTask(taskId);
  const listEl = document.getElementById('subtaskList');
  if (listEl) {
    listEl.parentElement.outerHTML = renderSubtasksSection(taskId, updated);
  }
  renderTasks();
  renderToday();
}

async function deleteSubtask(subtaskId, taskId) {
  try {
    const { error } = await sb
      .from('subtarefas')
      .delete()
      .eq('id', subtaskId);

    if (error) {
      console.error('Erro ao excluir subtarefa:', error);
      return;
    }
  } catch (e) {
    console.error('Erro ao excluir subtarefa:', e);
    return;
  }

  // Refresh
  await loadSubtaskCounts();
  const updated = await loadSubtasksForTask(taskId);
  const listEl = document.getElementById('subtaskList');
  if (listEl) {
    listEl.parentElement.outerHTML = renderSubtasksSection(taskId, updated);
  }
  renderTasks();
  renderToday();
}

// ========== PATCH: renderToday to include energy logger + coaching + annotation preview ==========
const _originalRenderToday = renderToday;
renderToday = function() {
  _originalRenderToday();
  const todayTaskList = document.getElementById('todayTaskList');
  // Insert annotation preview before everything else
  if (todayTaskList && !document.getElementById('weekAnnotationPreview')) {
    loadWeekAnnotation(getWeekDaysForOffset(0)[0].date).then(function(annotation) {
      // Update nav badge
      var navDot = document.getElementById('navAnnotationDot');
      if (navDot) navDot.style.display = annotation ? 'inline-block' : 'none';
      // Show preview card if annotation exists
      if (annotation && !document.getElementById('weekAnnotationPreview')) {
        var previewHTML = '<div class="week-annotation-preview" id="weekAnnotationPreview" onclick="switchView(\'review\')">'
          + '<div class="week-annotation-preview-header">'
          + '<span class="week-annotation-preview-label">Anotação da semana</span>'
          + '<span class="week-annotation-preview-action">Ver/Editar</span>'
          + '</div>'
          + '<div class="week-annotation-preview-text">' + annotation + '</div>'
          + '</div>';
        todayTaskList.insertAdjacentHTML('beforebegin', previewHTML);
      }
    });
  }
  // Insert energy logger after the header and before the task list
  if (todayTaskList && !document.getElementById('energyLogger')) {
    todayTaskList.insertAdjacentHTML('beforebegin', renderEnergyLogger());
    initEnergyLogger();
  }
  // Insert coaching card after energy logger and before the task list
  if (todayTaskList && !document.getElementById('coachingCard')) {
    const coachingHTML = renderCoachingCard();
    if (coachingHTML) {
      todayTaskList.insertAdjacentHTML('beforebegin', coachingHTML);
    }
  }
  // Add pomodoro buttons to today task cards
  if (todayTaskList) {
    todayTaskList.querySelectorAll('.task-actions').forEach(actionsDiv => {
      const card = actionsDiv.closest('.task-card');
      if (!card || card.classList.contains('completed')) return;
      const taskId = card.dataset.taskId;
      const accumMin = getPomodoroAccumMinutes(taskId);
      if (accumMin > 0) {
        const meta = card.querySelector('.task-meta');
        if (meta && !meta.querySelector('.task-pomo-time')) {
          const span = document.createElement('span');
          span.className = 'task-pomo-time';
          span.innerHTML = '&#127813; ' + accumMin + 'min';
          meta.appendChild(span);
        }
      }
      if (actionsDiv.querySelector('.pomo-start-btn')) return;
      const btn = document.createElement('button');
      btn.className = 'task-action-btn pomo-start-btn';
      btn.title = 'Iniciar Pomodoro — timer de 25 min de foco nesta tarefa';
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        startPomodoro(taskId);
        if ('Notification' in window && Notification.permission === 'default') {
          Notification.requestPermission();
        }
      });
      actionsDiv.insertBefore(btn, actionsDiv.firstChild);
    });
  }
};

// ========== PATCH: renderTasks to include pomodoro button & accum time ==========
const _originalRenderTasks = renderTasks;
renderTasks = function() {
  _originalRenderTasks();
  // Add pomodoro buttons to task actions (Todas + Hoje)
  document.querySelectorAll('#taskList .task-actions, #todayTaskList .task-actions').forEach(actionsDiv => {
    const card = actionsDiv.closest('.task-card');
    if (!card || card.classList.contains('completed')) return;
    const taskId = card.dataset.taskId;

    // Add accumulated time display
    const accumMin = getPomodoroAccumMinutes(taskId);
    if (accumMin > 0) {
      const meta = card.querySelector('.task-meta');
      if (meta && !meta.querySelector('.task-pomo-time')) {
        const span = document.createElement('span');
        span.className = 'task-pomo-time';
        span.innerHTML = '&#127813; ' + accumMin + 'min';
        meta.appendChild(span);
      }
    }

    // Add play button if not already there
    if (actionsDiv.querySelector('.pomo-start-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'task-action-btn pomo-start-btn';
    btn.title = 'Iniciar Pomodoro — timer de 25 min de foco nesta tarefa';
    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      startPomodoro(taskId);
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    });
    actionsDiv.insertBefore(btn, actionsDiv.firstChild);
  });
};

// ========== SMART SEARCH ==========

function initSearch() {
  const input = document.getElementById('globalSearch');
  const results = document.getElementById('searchResults');
  if (!input) return;

  input.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    if (query.length < 2) { results.classList.remove('active'); return; }
    searchTimeout = setTimeout(() => performSearch(query), 300);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 2) results.classList.add('active');
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) results.classList.remove('active');
  });
}

async function performSearch(query) {
  const results = document.getElementById('searchResults');
  const q = query.toLowerCase();
  let items = [];

  // Search tasks (in-memory)
  tasks.filter(t => t.titulo.toLowerCase().includes(q) || (t.notas||'').toLowerCase().includes(q))
    .slice(0, 5)
    .forEach(t => items.push({
      type: 'Tarefa', icon: '\ud83d\udccb',
      title: t.titulo,
      meta: (t.categoria || '') + ' \u00b7 ' + (t.prazo || 'sem data') + ' \u00b7 ' + t.status,
      onclick: "showTaskDetail('" + t.id + "')"
    }));

  // Search events (in-memory)
  calendarEvents.filter(ev => ev.titulo.toLowerCase().includes(q) || (ev.descricao||'').toLowerCase().includes(q))
    .slice(0, 5)
    .forEach(ev => items.push({
      type: 'Evento', icon: '\ud83d\udcc5',
      title: ev.titulo,
      meta: (ev.dia || '') + ' ' + (ev.horario_inicio || '') + ' \u00b7 ' + (ev.provider || ''),
      onclick: ''
    }));

  // Search weekly annotations (from Supabase)
  try {
    const { data: weeks } = await sb
      .from('historico_semanal')
      .select('*')
      .ilike('anotacao', '%' + query + '%')
      .order('semana_inicio', { ascending: false })
      .limit(3);
    if (weeks) {
      weeks.forEach(w => items.push({
        type: 'Anotação semanal', icon: '\ud83d\udcdd',
        title: 'Semana de ' + formatDate(w.semana_inicio),
        meta: (w.concluidas || 0) + '/' + (w.total_tarefas || 0) + ' tarefas \u00b7 ' + (w.taxa_conclusao || 0) + '%',
        preview: (w.anotacao || '').substring(0, 80),
        onclick: "navigateToWeek('" + w.semana_inicio + "')"
      }));
    }
  } catch(e) { console.warn('Search annotations error:', e); }

  // Search attachments
  try {
    const { data: anexos } = await sb
      .from('anexos')
      .select('*')
      .or('titulo.ilike.%' + query + '%,conteudo.ilike.%' + query + '%')
      .order('created_at', { ascending: false })
      .limit(5);
    if (anexos) {
      var icons = { texto: '\ud83d\udcc4', transcricao: '\ud83c\udf99\ufe0f', link: '\ud83d\udd17', arquivo: '\ud83d\udcce', documento: '\ud83d\udccb' };
      var typeLabels = { texto: 'Texto', transcricao: 'Transcrição', link: 'Link', arquivo: 'Arquivo', documento: 'Documento' };
      anexos.forEach(a => {
        var taskName = '';
        if (a.tarefa_id) {
          var parentTask = tasks.find(function(t) { return t.id === a.tarefa_id; });
          if (parentTask) taskName = parentTask.titulo;
        }
        items.push({
          type: (typeLabels[a.tipo] || 'Anexo'), icon: icons[a.tipo] || '\ud83d\udcc4',
          title: a.titulo || 'Sem título',
          meta: taskName ? 'Tarefa: ' + taskName : '',
          preview: (a.conteudo || '').substring(0, 80),
          onclick: a.tarefa_id ? "showTaskDetail('" + a.tarefa_id + "')" : ''
        });
      });
    }
  } catch(e) { console.warn('Search attachments error:', e); }

  // Render results
  if (items.length === 0) {
    results.innerHTML = '<div class="search-result-item"><div class="search-result-title" style="color:var(--text-muted)">Nenhum resultado</div></div>';
  } else {
    results.innerHTML = items.map(function(item) {
      return '<div class="search-result-item" ' + (item.onclick ? 'onclick="' + item.onclick + '"' : '') + ' style="' + (item.onclick ? 'cursor:pointer' : '') + '">'
        + '<div class="search-result-type">' + item.icon + ' ' + item.type + '</div>'
        + '<div class="search-result-title">' + highlightSearchTerm(item.title, query) + '</div>'
        + (item.meta ? '<div class="search-result-meta">' + highlightSearchTerm(item.meta, query) + '</div>' : '')
        + (item.preview ? '<div class="search-result-preview">' + highlightSearchTerm(item.preview, query) + '...</div>' : '')
        + '</div>';
    }).join('');
  }
  results.classList.add('active');
}

// ========== ATTACHMENTS ==========

async function loadAttachments(taskId) {
  try {
    const { data, error } = await sb
      .from('anexos')
      .select('*')
      .eq('tarefa_id', taskId)
      .order('created_at', { ascending: false });
    if (error) { console.error('Erro ao carregar anexos:', error); return []; }
    return data || [];
  } catch(e) { console.error('Erro ao carregar anexos:', e); return []; }
}

function renderAttachmentsSection(taskId, attachments) {
  var icons = { texto: '\ud83d\udcc4', transcricao: '\ud83c\udf99\ufe0f', link: '\ud83d\udd17', arquivo: '\ud83d\udcce', documento: '\ud83d\udccb' };
  var html = '<div class="detail-attachments">'
    + '<div class="detail-attachments-header">'
    + '<span class="detail-attachments-title">Anexos (' + attachments.length + ')</span>'
    + '<button class="attachment-add-btn" onclick="showAttachmentInput(\'' + taskId + '\')">+ Adicionar</button>'
    + '</div>'
    + '<div id="attachmentList">';

  attachments.forEach(function(a) {
    var icon = icons[a.tipo] || '\ud83d\udcc4';
    var preview = (a.conteudo || '').substring(0, 100);
    var dateStr = a.created_at ? new Date(a.created_at).toLocaleDateString('pt-BR') : '';
    html += '<div class="attachment-item" onclick="expandAttachment(\'' + a.id + '\')">'
      + '<span class="attachment-icon">' + icon + '</span>'
      + '<div class="attachment-info">'
      + '<div class="attachment-title">' + (a.titulo || 'Sem título') + '</div>'
      + '<div class="attachment-preview">' + preview + '</div>'
      + '<div class="attachment-date">' + dateStr + '</div>'
      + '</div>'
      + '<button class="attachment-delete" onclick="event.stopPropagation();deleteAttachment(\'' + a.id + '\',\'' + taskId + '\')">\u2715</button>'
      + '</div>';
  });

  html += '</div>'
    + '<div id="attachmentInputContainer"></div>'
    + '</div>';
  return html;
}

function showAttachmentInput(taskId) {
  var container = document.getElementById('attachmentInputContainer');
  if (!container || container.querySelector('.attachment-title-input')) return;

  var area = document.createElement('div');
  area.className = 'attachment-input-area visible';
  area.innerHTML = '<div class="attachment-type-selector">'
    + '<button class="att-type-btn active" data-type="texto" onclick="selectAttType(this)">Texto</button>'
    + '<button class="att-type-btn" data-type="transcricao" onclick="selectAttType(this)">Transcrição</button>'
    + '<button class="att-type-btn" data-type="documento" onclick="selectAttType(this)">Documento</button>'
    + '<button class="att-type-btn" data-type="link" onclick="selectAttType(this)">Link</button>'
    + '</div>'
    + '<div class="attachment-file-drop" onclick="this.querySelector(\'input\').click()" ondragover="event.preventDefault();this.classList.add(\'dragover\')" ondragleave="this.classList.remove(\'dragover\')" ondrop="handleFileDrop(event,\'' + taskId + '\')">'
    + '<input type="file" accept=".txt,.md,.pdf,.docx,.doc,.csv" style="display:none" onchange="handleFileSelect(event,\'' + taskId + '\')">'
    + '<span class="file-drop-icon">+</span>'
    + '<span class="file-drop-text">Arraste um arquivo ou clique para selecionar</span>'
    + '<span class="file-drop-hint">.txt, .md, .csv, .docx</span>'
    + '</div>'
    + '<input type="text" class="attachment-title-input" placeholder="Título do anexo...">'
    + '<textarea class="attachment-content-input" placeholder="Conteúdo (texto, notas, transcrições, links...)"></textarea>'
    + '<div class="attachment-input-actions">'
    + '<button class="attachment-cancel-btn" onclick="this.closest(\'.attachment-input-area\').remove()">Cancelar</button>'
    + '<button class="attachment-save-btn" onclick="saveNewAttachment(\'' + taskId + '\')">Salvar anexo</button>'
    + '</div>';
  container.appendChild(area);
  area.querySelector('.attachment-title-input').focus();
}

function selectAttType(btn) {
  btn.parentElement.querySelectorAll('.att-type-btn').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
}

function handleFileSelect(event, taskId) {
  var file = event.target.files[0];
  if (!file) return;
  processAttachmentFile(file, taskId);
}

function handleFileDrop(event, taskId) {
  event.preventDefault();
  event.currentTarget.classList.remove('dragover');
  var file = event.dataTransfer.files[0];
  if (!file) return;
  processAttachmentFile(file, taskId);
}

function processAttachmentFile(file, taskId) {
  var container = document.getElementById('attachmentInputContainer');
  var titleInput = container.querySelector('.attachment-title-input');
  var contentInput = container.querySelector('.attachment-content-input');
  var dropZone = container.querySelector('.attachment-file-drop');

  // Set title to filename
  titleInput.value = file.name;

  // Auto-select document type
  var docBtn = container.querySelector('[data-type="documento"]');
  if (docBtn) selectAttType(docBtn);

  // Read file content
  var reader = new FileReader();
  reader.onload = function(e) {
    contentInput.value = e.target.result;
    dropZone.querySelector('.file-drop-text').textContent = file.name + ' carregado';
    dropZone.classList.add('file-loaded');
  };
  reader.onerror = function() {
    contentInput.value = '[Erro ao ler arquivo: ' + file.name + ']';
  };
  reader.readAsText(file);
}

async function saveNewAttachment(taskId) {
  var container = document.getElementById('attachmentInputContainer');
  var titleInput = container.querySelector('.attachment-title-input');
  var contentInput = container.querySelector('.attachment-content-input');
  var titulo = titleInput.value.trim();
  var conteudo = contentInput.value.trim();

  // Get selected type
  var activeType = container.querySelector('.att-type-btn.active');
  var tipo = activeType ? activeType.dataset.type : 'texto';

  if (!titulo && !conteudo) return;
  if (!titulo) titulo = 'Sem título';

  try {
    const { error } = await sb
      .from('anexos')
      .insert({ tarefa_id: taskId, tipo: tipo, titulo: titulo, conteudo: conteudo });
    if (error) {
      console.error('Erro ao salvar anexo:', error);
      return;
    }
  } catch(e) {
    console.error('Erro ao salvar anexo:', e);
    return;
  }

  // Refresh
  var updated = await loadAttachments(taskId);
  var listEl = document.getElementById('attachmentList');
  if (listEl) {
    listEl.parentElement.outerHTML = renderAttachmentsSection(taskId, updated);
  }
}

async function deleteAttachment(attachmentId, taskId) {
  if (!confirm('Excluir este anexo?')) return;
  try {
    const { error } = await sb
      .from('anexos')
      .delete()
      .eq('id', attachmentId);
    if (error) {
      console.error('Erro ao excluir anexo:', error);
      return;
    }
  } catch(e) {
    console.error('Erro ao excluir anexo:', e);
    return;
  }

  // Refresh
  var updated = await loadAttachments(taskId);
  var listEl = document.getElementById('attachmentList');
  if (listEl) {
    listEl.parentElement.outerHTML = renderAttachmentsSection(taskId, updated);
  }
}

// Cache for attachment content (to avoid re-fetching)

async function expandAttachment(attachmentId) {
  var attachment = null;
  // Try cache first
  if (attachmentContentCache[attachmentId]) {
    attachment = attachmentContentCache[attachmentId];
  } else {
    try {
      const { data } = await sb.from('anexos').select('*').eq('id', attachmentId).single();
      if (data) {
        attachment = data;
        attachmentContentCache[attachmentId] = data;
      }
    } catch(e) { console.error('Erro ao carregar anexo:', e); return; }
  }
  if (!attachment) return;

  var overlay = document.createElement('div');
  overlay.className = 'attachment-expanded';
  overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = '<div class="attachment-expanded-content">'
    + '<div class="attachment-expanded-title">' + (attachment.titulo || 'Sem título') + '</div>'
    + '<div class="attachment-expanded-text">' + (attachment.conteudo || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>'
    + '</div>'
    + '<button class="attachment-expanded-close" onclick="this.parentElement.remove()">\u2715</button>';
  document.body.appendChild(overlay);
}

// ========== INIT ==========
// Restore theme from localStorage (before auth check — visual only)
// Light e o padrao — dark mode e opt-in
if (localStorage.getItem('theme') === 'dark') {
  document.body.classList.add('dark-mode');
  const themeIcon = document.getElementById('themeIcon');
  if (themeIcon) themeIcon.textContent = '☀️';
}

// App initialization — called only after successful auth
function initApp() {
  updateHeaderDate();
  initRangeLabel();
  loadEnergyData();
  loadTasks().then(() => {
    loadGamification();
    renderProgressRing();
    loadSubtaskCounts().then(() => {
      renderTasks();
      renderToday();
    });
  });
  checkCalendarConnections();
  loadCalendarEvents().then(() => {
    const currentView = document.querySelector('.view-toggle button.active');
    if (currentView) {
      const view = currentView.dataset.view;
      if (view === 'today') renderToday();
      else if (view === 'calendar') renderCalendar();
    }
  });
  setInterval(() => {
    loadCalendarEvents().then(() => {
      const currentView = document.querySelector('.view-toggle button.active');
      if (currentView) {
        const view = currentView.dataset.view;
        if (view === 'today') renderToday();
        else if (view === 'calendar') renderCalendar();
      }
    });
  }, 300000);
  setupRealtime();
  setupDragAndDrop();
  setupSwipeGestures();
  initSearch();
}

// Start: check auth first, then load app if authenticated
checkAuth();

// ========== PWA: Service Worker + Install Prompt ==========
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js')
    .then(reg => console.log('SW registered:', reg.scope))
    .catch(err => console.log('SW registration failed:', err));
}


window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  showInstallBanner();
});

function showInstallBanner() {
  if (localStorage.getItem('pwa-dismiss')) return;
  const banner = document.createElement('div');
  banner.className = 'pwa-install-banner';
  banner.innerHTML = `
    <span class="pwa-install-text">Instalar como app</span>
    <button class="pwa-install-btn" onclick="installPWA()">Instalar</button>
    <button class="pwa-install-close" onclick="this.parentElement.remove();localStorage.setItem('pwa-dismiss','1')">&times;</button>
  `;
  document.body.appendChild(banner);
}

function installPWA() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  deferredPrompt.userChoice.then(result => {
    deferredPrompt = null;
    document.querySelector('.pwa-install-banner')?.remove();
  });
}

// ========== CLEANUP PANEL (Anti-Duplicatas) ==========

function openCleanupPanel() {
  document.getElementById('cleanupOverlay').classList.add('active');
  runCleanupAnalysis();
}

function closeCleanupPanel(event) {
  if (event && event.target !== event.currentTarget && !event.target.closest('.cleanup-close')) return;
  document.getElementById('cleanupOverlay').classList.remove('active');
}

async function runCleanupAnalysis() {
  const body = document.getElementById('cleanupBody');
  const actions = document.getElementById('cleanupActions');
  body.innerHTML = '<div class="cleanup-status"><div class="spinner"></div><div>Analisando suas tarefas...</div></div>';
  actions.style.display = 'none';

  // Get all non-completed tasks
  if (!currentUser) { body.innerHTML = '<div class="cleanup-status">Sessão expirada.</div>'; return; }
  const { data: allTasks, error } = await sb
    .from('tarefas')
    .select('id,titulo,categoria,prioridade,prazo,horario,status,created_at')
    .eq('user_id', currentUser.id)
    .neq('status', 'concluida')
    .order('titulo', { ascending: true });

  if (error || !allTasks || allTasks.length === 0) {
    body.innerHTML = '<div class="cleanup-status">✅ Nenhuma tarefa pendente para analisar.</div>';
    return;
  }

  // Find duplicate groups using fuzzy matching
  const groups = [];
  const used = new Set();

  for (let i = 0; i < allTasks.length; i++) {
    if (used.has(i)) continue;
    const t1 = allTasks[i];
    const title1 = (t1.titulo || '').toLowerCase().trim();
    if (title1.length < 3) continue;

    const group = [{ task: t1, similarity: 100 }];

    for (let j = i + 1; j < allTasks.length; j++) {
      if (used.has(j)) continue;
      const t2 = allTasks[j];
      const title2 = (t2.titulo || '').toLowerCase().trim();
      if (title2.length < 3) continue;

      const sim = stringSimilarity(title1, title2);
      const contained = (title1.length > 5 && title2.includes(title1)) ||
                        (title2.length > 5 && title1.includes(title2));

      if (sim >= 0.7 || contained) {
        group.push({ task: t2, similarity: Math.round(Math.max(sim, contained ? 0.85 : 0) * 100) });
        used.add(j);
      }
    }

    if (group.length > 1) {
      used.add(i);
      groups.push(group);
    }
  }

  // Also find tasks with same day + similar time (possible conflicts)
  const conflicts = [];
  for (let i = 0; i < allTasks.length; i++) {
    const t1 = allTasks[i];
    if (!t1.prazo || !t1.horario) continue;
    for (let j = i + 1; j < allTasks.length; j++) {
      const t2 = allTasks[j];
      if (!t2.prazo || !t2.horario) continue;
      if (t1.prazo === t2.prazo && t1.horario === t2.horario && t1.titulo !== t2.titulo) {
        // Same day, same time, different tasks
        const alreadyGrouped = groups.some(g => g.some(item => item.task.id === t1.id || item.task.id === t2.id));
        if (!alreadyGrouped) {
          conflicts.push({ task1: t1, task2: t2 });
        }
      }
    }
  }

  const totalDuplicatas = groups.reduce((sum, g) => sum + g.length - 1, 0);

  if (groups.length === 0 && conflicts.length === 0) {
    body.innerHTML = '<div class="cleanup-status">✅ Tudo limpo! Nenhuma duplicata ou conflito encontrado.</div>';
    return;
  }

  // Render results
  let html = '<div class="cleanup-summary">';
  html += '<div class="cleanup-summary-card"><div class="cleanup-summary-number">' + groups.length + '</div><div class="cleanup-summary-label">Grupos similares</div></div>';
  html += '<div class="cleanup-summary-card"><div class="cleanup-summary-number">' + totalDuplicatas + '</div><div class="cleanup-summary-label">Possíveis duplicatas</div></div>';
  html += '<div class="cleanup-summary-card"><div class="cleanup-summary-number">' + conflicts.length + '</div><div class="cleanup-summary-label">Conflitos de horário</div></div>';
  html += '</div>';

  // Duplicate groups
  groups.forEach(function(group, gIdx) {
    html += '<div class="cleanup-group">';
    html += '<div class="cleanup-group-header">';
    html += '<span class="cleanup-group-title">Grupo ' + (gIdx + 1) + ' — "' + (group[0].task.titulo || '').substring(0, 40) + '"</span>';
    html += '<span class="cleanup-group-badge">' + group.length + ' tarefas</span>';
    html += '</div>';

    group.forEach(function(item, tIdx) {
      var t = item.task;
      var prazoStr = t.prazo ? new Date(t.prazo + 'T12:00:00').toLocaleDateString('pt-BR', {day:'2-digit',month:'short'}) : 'sem data';
      var catColors = {'Trabalho':'var(--cat-trabalho)','Consultoria':'var(--cat-consultoria)','Grupo Ser':'var(--cat-grupo-ser)','Pessoal':'var(--cat-pessoal)'};
      var catColor = catColors[t.categoria] || 'var(--text-muted)';

      html += '<div class="cleanup-task">';
      html += '<input type="checkbox" class="cleanup-check" data-task-id="' + t.id + '" onchange="updateCleanupCount()"' + (tIdx > 0 ? ' checked' : '') + '>';
      html += '<div class="cleanup-task-info">';
      html += '<div class="cleanup-task-title">' + (t.titulo || '') + '</div>';
      html += '<div class="cleanup-task-meta"><span style="color:' + catColor + '">' + (t.categoria || '') + '</span> · ' + prazoStr + (t.horario ? ' · ' + t.horario.substring(0,5) : '') + ' · ' + (t.status || '') + '</div>';
      html += '</div>';
      if (tIdx > 0) {
        html += '<span class="cleanup-task-similarity">' + item.similarity + '%</span>';
      } else {
        html += '<span class="cleanup-task-similarity" style="background:hsla(142,52%,45%,0.15);color:hsl(142,52%,45%)">original</span>';
      }
      html += '<div class="cleanup-task-actions">';
      html += '<button class="cleanup-task-btn" onclick="showTaskDetail(\'' + t.id + '\');closeCleanupPanel()">✏️</button>';
      html += '</div>';
      html += '</div>';
    });

    html += '</div>';
  });

  // Conflicts
  if (conflicts.length > 0) {
    html += '<div class="cleanup-group">';
    html += '<div class="cleanup-group-header">';
    html += '<span class="cleanup-group-title">⚠️ Conflitos de horário</span>';
    html += '<span class="cleanup-group-badge" style="background:rgba(0,117,222,0.1);color:var(--amber)">' + conflicts.length + ' conflitos</span>';
    html += '</div>';

    conflicts.forEach(function(c) {
      var prazoStr = c.task1.prazo ? new Date(c.task1.prazo + 'T12:00:00').toLocaleDateString('pt-BR', {day:'2-digit',month:'short'}) : '';
      html += '<div class="cleanup-task">';
      html += '<input type="checkbox" class="cleanup-check" data-task-id="' + c.task2.id + '" onchange="updateCleanupCount()">';
      html += '<div class="cleanup-task-info">';
      html += '<div class="cleanup-task-title">' + c.task1.titulo + ' <span style="color:var(--text-muted)">×</span> ' + c.task2.titulo + '</div>';
      html += '<div class="cleanup-task-meta">Mesmo horário: ' + prazoStr + ' às ' + (c.task1.horario || '').substring(0,5) + '</div>';
      html += '</div>';
      html += '<div class="cleanup-task-actions">';
      html += '<button class="cleanup-task-btn" onclick="showTaskDetail(\'' + c.task1.id + '\');closeCleanupPanel()">✏️ 1ª</button>';
      html += '<button class="cleanup-task-btn" onclick="showTaskDetail(\'' + c.task2.id + '\');closeCleanupPanel()">✏️ 2ª</button>';
      html += '</div>';
      html += '</div>';
    });

    html += '</div>';
  }

  body.innerHTML = html;
  actions.style.display = 'flex';
  updateCleanupCount();
}

// Simple string similarity (Dice coefficient — fast approximation)
function stringSimilarity(a, b) {
  if (a === b) return 1;
  if (a.length < 2 || b.length < 2) return 0;
  var bigrams1 = new Map();
  for (var i = 0; i < a.length - 1; i++) {
    var bigram = a.substring(i, i + 2);
    bigrams1.set(bigram, (bigrams1.get(bigram) || 0) + 1);
  }
  var intersection = 0;
  for (var j = 0; j < b.length - 1; j++) {
    var bg = b.substring(j, j + 2);
    var count = bigrams1.get(bg) || 0;
    if (count > 0) {
      intersection++;
      bigrams1.set(bg, count - 1);
    }
  }
  return (2 * intersection) / (a.length + b.length - 2);
}

function updateCleanupCount() {
  var checks = document.querySelectorAll('.cleanup-check:checked');
  var btn = document.getElementById('cleanupDeleteBtn');
  btn.textContent = '🗑️ Excluir selecionados (' + checks.length + ')';
  btn.disabled = checks.length === 0;
}

function selectAllCleanup() {
  var checks = document.querySelectorAll('.cleanup-check');
  var allChecked = Array.from(checks).every(function(c) { return c.checked; });
  checks.forEach(function(c) { c.checked = !allChecked; });
  updateCleanupCount();
}

async function deleteSelectedCleanup() {
  var checks = document.querySelectorAll('.cleanup-check:checked');
  var ids = Array.from(checks).map(function(c) { return c.dataset.taskId; });

  if (ids.length === 0) return;
  if (!confirm('Excluir ' + ids.length + ' tarefa(s) selecionada(s)? Essa ação não pode ser desfeita.')) return;

  var deleted = 0;
  for (var i = 0; i < ids.length; i++) {
    var ok = await removeTask(ids[i]);
    if (ok) deleted++;
  }

  // Refresh tasks and re-run analysis
  await loadTasks();
  renderTasks();

  if (deleted === ids.length) {
    alert(deleted + ' tarefa(s) excluída(s) com sucesso!');
  } else {
    alert(deleted + ' de ' + ids.length + ' excluída(s). Algumas falharam.');
  }

  runCleanupAnalysis();
}

// ========== HELP SYSTEM ==========

// --- Help Tooltips ---
const helpTooltipData = {
  'statsBar': { title: 'Estatísticas', text: 'Clique em qualquer card para filtrar tarefas por status. Os números atualizam em tempo real.' },
  'filterBar': { title: 'Filtros por Categoria', text: 'Selecione uma categoria para filtrar. Combine com filtros de status e prioridade para refinar.' },
  'taskList': { title: 'Lista de Tarefas', text: 'Suas tarefas organizadas. Clique no círculo para concluir. Segure para seleção em massa. Clique no card para ver detalhes.' },
  'gamificationBar': { title: 'Gamificação', text: 'Acompanhe seu progresso diário, streak de dias consecutivos e nível de XP. Conclua tarefas para ganhar pontos!' }
};

function initHelpTooltips() {
  Object.entries(helpTooltipData).forEach(([targetId, data]) => {
    const target = document.getElementById(targetId);
    if (!target) return;
    const wrapper = target.parentElement;
    if (!wrapper) return;

    // Check if already added
    if (target.querySelector('.help-tooltip-btn')) return;

    const btn = document.createElement('button');
    btn.className = 'help-tooltip-btn';
    btn.textContent = '?';
    btn.setAttribute('aria-label', 'Ajuda: ' + data.title);
    btn.style.position = 'absolute';
    btn.style.right = '8px';
    btn.style.top = '8px';

    const card = document.createElement('div');
    card.className = 'help-tooltip-card';
    card.innerHTML = '<h4>' + data.title + '</h4><p>' + data.text + '</p>';

    // Position target relatively if not already
    const pos = getComputedStyle(target).position;
    if (pos === 'static') target.style.position = 'relative';

    target.appendChild(btn);
    document.body.appendChild(card);

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close all other tooltips
      document.querySelectorAll('.help-tooltip-card.visible').forEach(c => {
        if (c !== card) c.classList.remove('visible');
      });

      if (card.classList.contains('visible')) {
        card.classList.remove('visible');
        return;
      }

      // Use fixed positioning based on button's viewport rect
      const btnRect = btn.getBoundingClientRect();
      const cardWidth = 280;
      const cardHeight = 160; // approximate
      const gap = 10;

      // Calculate left position (align right edge with button right edge)
      let left = btnRect.right - cardWidth;
      if (left < 10) left = 10;
      if (left + cardWidth > window.innerWidth - 10) left = window.innerWidth - cardWidth - 10;

      // Check if tooltip fits below the button
      const spaceBelow = window.innerHeight - btnRect.bottom - gap;
      const spaceAbove = btnRect.top - gap;

      card.classList.remove('arrow-up', 'arrow-down');

      if (spaceBelow >= cardHeight) {
        // Show below
        card.style.top = (btnRect.bottom + gap) + 'px';
        card.style.bottom = 'auto';
        card.classList.add('arrow-up');
      } else if (spaceAbove >= cardHeight) {
        // Show above
        card.style.top = 'auto';
        card.style.bottom = (window.innerHeight - btnRect.top + gap) + 'px';
        card.classList.add('arrow-down');
      } else {
        // Fallback: show below anyway
        card.style.top = (btnRect.bottom + gap) + 'px';
        card.style.bottom = 'auto';
        card.classList.add('arrow-up');
      }

      card.style.left = left + 'px';
      card.style.right = 'auto';
      card.classList.add('visible');
    });
  });
}

// Close tooltips on outside click
document.addEventListener('click', (e) => {
  if (!e.target.closest('.help-tooltip-btn') && !e.target.closest('.help-tooltip-card')) {
    document.querySelectorAll('.help-tooltip-card.visible').forEach(c => c.classList.remove('visible'));
  }
});

// --- Help Center ---
function openHelpCenter() {
  document.getElementById('helpCenterOverlay').classList.add('active');
}

function closeHelpCenter(event) {
  if (event && event.target !== event.currentTarget && !event.target.closest('.help-center-close')) return;
  document.getElementById('helpCenterOverlay').classList.remove('active');
}

function toggleHelpAccordion(id) {
  const acc = document.getElementById(id);
  if (!acc) return;
  acc.classList.toggle('open');
}

// --- Onboarding Tour ---
const onboardingSteps = [
  {
    target: '#statsBar',
    title: '📊 Estatísticas Rápidas',
    desc: 'Veja o resumo das suas tarefas de relance. Clique em qualquer card para filtrar — Total, Pendentes, Concluídas, Atrasadas ou Reuniões.',
    position: 'bottom'
  },
  {
    target: '.task-list',
    title: '📋 Seus Cards de Tarefa',
    desc: 'Cada tarefa mostra título, categoria, prioridade e prazo. Clique no círculo para concluir, ou no card para ver detalhes e editar.',
    position: 'top'
  },
  {
    target: '#filterBar',
    title: '🔍 Filtros Inteligentes',
    desc: 'Filtre por categoria (Trabalho, Consultoria, Grupo Ser, Pessoal). Na sidebar do desktop, filtre também por prioridade.',
    position: 'bottom'
  },
  {
    target: '.bottom-nav',
    title: '🧭 Navegação por Visões',
    desc: 'Alterne entre visões: Todas, Hoje, Blocos de Tempo, KPIs, Semana, Revisão e Matriz de Eisenhower. Cada uma oferece uma perspectiva diferente.',
    position: 'top'
  },
  {
    target: '.search-container',
    fallbackTarget: '.header-right',
    title: '🔎 Busca Global',
    desc: 'Pesquise tarefas por título, notas ou categoria. Os resultados aparecem instantaneamente enquanto você digita.',
    position: 'bottom'
  },
  {
    target: 'button[onclick="vincularTelegram()"]',
    fallbackTarget: '.header-right',
    title: '✈️ Vincule seu Telegram',
    desc: 'Este botão azul abre o fluxo para conectar o bot do Telegram à sua conta. É por ali que você cria tarefas por voz ou texto, registra gastos, e recebe lembretes. <strong>Sem isso, o bot não sabe quem você é</strong>. Clique aqui depois de fechar o tour e siga o passo a passo.',
    position: 'bottom'
  },
  {
    target: '.btn-help-center',
    title: '❓ Central de Ajuda',
    desc: 'Acesse a qualquer momento para ver comandos do Telegram, guias de funcionalidades e dicas. Você também pode refazer este tour por lá!',
    position: 'bottom'
  }
];


function startOnboarding() {
  currentOnboardingStep = 0;
  const backdrop = document.getElementById('onboardingBackdrop');
  backdrop.classList.add('active');
  showOnboardingStep(0);

  // Add scroll/resize listeners to reposition
  _onboardingScrollHandler = () => _repositionOnboarding();
  _onboardingResizeHandler = () => _repositionOnboarding();
  window.addEventListener('scroll', _onboardingScrollHandler, true);
  window.addEventListener('resize', _onboardingResizeHandler);
}

function _repositionOnboarding() {
  const step = onboardingSteps[currentOnboardingStep];
  if (!step) return;
  let targetEl = document.querySelector(step.target);
  if (!targetEl && step.fallbackTarget) targetEl = document.querySelector(step.fallbackTarget);
  if (!targetEl) return;

  const highlight = document.getElementById('onboardingHighlight');
  const popup = document.getElementById('onboardingPopup');
  const rect = targetEl.getBoundingClientRect();
  const pad = 8;
  const maxHighlightH = window.innerHeight * 0.4;

  let highlightTop = rect.top - pad;
  let highlightHeight = rect.height + pad * 2;
  if (highlightHeight > maxHighlightH) {
    const visibleCenter = Math.max(rect.top, 0) + Math.min(rect.height, window.innerHeight) / 2;
    highlightTop = visibleCenter - maxHighlightH / 2;
    highlightHeight = maxHighlightH;
  }

  highlight.style.top = highlightTop + 'px';
  highlight.style.left = (rect.left - pad) + 'px';
  highlight.style.width = (rect.width + pad * 2) + 'px';
  highlight.style.height = highlightHeight + 'px';

  const cappedRect = {
    top: highlightTop,
    bottom: highlightTop + highlightHeight,
    left: rect.left - pad,
    right: rect.right + pad,
    width: rect.width + pad * 2,
    height: highlightHeight
  };
  _positionOnboardingPopup(cappedRect, step.position, popup);
}

function _positionOnboardingPopup(rect, position, popup) {
  const popupWidth = Math.min(320, window.innerWidth - 20);
  const popupHeight = popup.offsetHeight || 200;
  const gap = 16;
  const safeMargin = 10;

  let popupTop, popupLeft;
  popup.classList.remove('arrow-up', 'arrow-down');

  const spaceBelow = window.innerHeight - rect.bottom - gap;
  const spaceAbove = rect.top - gap;

  if (position === 'bottom' && spaceBelow >= popupHeight) {
    popupTop = rect.bottom + gap;
    popup.classList.add('arrow-up');
  } else if (position === 'top' && spaceAbove >= popupHeight) {
    popupTop = rect.top - popupHeight - gap;
    popup.classList.add('arrow-down');
  } else if (spaceBelow >= spaceAbove) {
    popupTop = rect.bottom + gap;
    popup.classList.add('arrow-up');
  } else {
    popupTop = rect.top - popupHeight - gap;
    popup.classList.add('arrow-down');
  }

  // Clamp popup vertically within viewport
  popupTop = Math.max(safeMargin, Math.min(popupTop, window.innerHeight - popupHeight - safeMargin));

  popupLeft = Math.max(safeMargin, Math.min(rect.left, window.innerWidth - popupWidth - safeMargin));

  popup.style.top = popupTop + 'px';
  popup.style.left = popupLeft + 'px';
  popup.style.transform = 'none';
}

function showOnboardingStep(index) {
  if (index >= onboardingSteps.length) {
    endOnboarding();
    return;
  }

  currentOnboardingStep = index;
  const step = onboardingSteps[index];
  let targetEl = document.querySelector(step.target);
  if (!targetEl && step.fallbackTarget) targetEl = document.querySelector(step.fallbackTarget);

  // Update step indicators
  const stepsContainer = document.getElementById('onboardingSteps');
  stepsContainer.innerHTML = onboardingSteps.map((_, i) =>
    '<div class="onboarding-step-dot' + (i === index ? ' active' : '') + '"></div>'
  ).join('');

  // Update content
  document.getElementById('onboardingTitle').textContent = step.title;
  document.getElementById('onboardingDesc').textContent = step.desc;

  const nextBtn = document.getElementById('onboardingNextBtn');
  nextBtn.textContent = index === onboardingSteps.length - 1 ? 'Concluir' : 'Próximo';

  // Position highlight
  const highlight = document.getElementById('onboardingHighlight');
  const popup = document.getElementById('onboardingPopup');

  if (targetEl) {
    // Scroll element into view first, then position after scroll completes
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Wait for scroll to complete, then position
    setTimeout(() => {
      const rect = targetEl.getBoundingClientRect();
      const pad = 8;
      const maxHighlightH = window.innerHeight * 0.4;

      // Cap highlight height for large elements (e.g. task-list on mobile)
      let highlightTop = rect.top - pad;
      let highlightHeight = rect.height + pad * 2;
      if (highlightHeight > maxHighlightH) {
        // Center the capped highlight on the visible portion
        const visibleCenter = Math.max(rect.top, 0) + Math.min(rect.height, window.innerHeight) / 2;
        highlightTop = visibleCenter - maxHighlightH / 2;
        highlightHeight = maxHighlightH;
      }

      highlight.style.display = 'block';
      highlight.style.top = highlightTop + 'px';
      highlight.style.left = (rect.left - pad) + 'px';
      highlight.style.width = (rect.width + pad * 2) + 'px';
      highlight.style.height = highlightHeight + 'px';

      // Use the capped rect for popup positioning
      const cappedRect = {
        top: highlightTop,
        bottom: highlightTop + highlightHeight,
        left: rect.left - pad,
        right: rect.right + pad,
        width: rect.width + pad * 2,
        height: highlightHeight
      };
      _positionOnboardingPopup(cappedRect, step.position, popup);
    }, 400);
  } else {
    highlight.style.display = 'none';
    popup.classList.remove('arrow-up', 'arrow-down');
    popup.style.top = '50%';
    popup.style.left = '50%';
    popup.style.transform = 'translate(-50%, -50%)';
  }
}

function nextOnboardingStep() {
  if (currentOnboardingStep >= onboardingSteps.length - 1) {
    endOnboarding();
  } else {
    showOnboardingStep(currentOnboardingStep + 1);
  }
}

function endOnboarding() {
  document.getElementById('onboardingBackdrop').classList.remove('active');
  localStorage.setItem('onboarding_done', '1');

  // Clean up scroll/resize listeners
  if (_onboardingScrollHandler) {
    window.removeEventListener('scroll', _onboardingScrollHandler, true);
    _onboardingScrollHandler = null;
  }
  if (_onboardingResizeHandler) {
    window.removeEventListener('resize', _onboardingResizeHandler);
    _onboardingResizeHandler = null;
  }
}

// --- Contextual View Hints ---
const viewHints = {
  tasks: { icon: '&#128203;', text: 'Visão geral de todas as suas tarefas. Use as abas de status acima para filtrar entre Pendentes, Em andamento e Concluídas.' },
  today: { icon: '&#9200;', text: 'Foco no dia de hoje. Mostra apenas tarefas com prazo para hoje, organizadas por horário. Ideal para começar o dia.' },
  calendar: { icon: '&#128197;', text: 'Visão semanal com suas tarefas distribuídas por dia. Conecte Google Calendar ou Microsoft 365 para ver eventos externos.' },
  matrix: { icon: '&#127919;', text: 'Matriz de Eisenhower: organize tarefas por urgência e importância. Arraste entre quadrantes para repriorizar.' },
  timeblock: { icon: '&#128338;', text: 'Blocos de tempo: veja sua agenda visual do dia com tarefas e reuniões alocadas nos horários.' },
  kpis: { icon: '&#128200;', text: 'Métricas de produtividade: taxa de conclusão, distribuição por categoria, performance por dia da semana.' },
  review: { icon: '&#128214;', text: 'Revisão semanal: heatmap de atividade, hábitos, anotações e histórico. Navegue entre semanas com as setas.' }
};

function showViewHint(viewName) {
  const hint = viewHints[viewName];
  if (!hint) return;

  // Check if dismissed
  const dismissKey = 'hint_dismissed_' + viewName;
  if (localStorage.getItem(dismissKey)) return;

  // Remove existing hints
  document.querySelectorAll('.view-hint').forEach(h => h.remove());

  const mainEl = document.querySelector('.main');
  if (!mainEl) return;

  const hintEl = document.createElement('div');
  hintEl.className = 'view-hint';
  hintEl.innerHTML =
    '<span class="view-hint-icon">' + hint.icon + '</span>' +
    '<span class="view-hint-text">' + hint.text + '</span>' +
    '<button class="view-hint-close" onclick="dismissViewHint(\'' + viewName + '\', this)" aria-label="Fechar dica">&times;</button>';

  mainEl.insertBefore(hintEl, mainEl.firstChild);
}

function dismissViewHint(viewName, btn) {
  localStorage.setItem('hint_dismissed_' + viewName, '1');
  const hint = btn.closest('.view-hint');
  if (hint) {
    hint.style.opacity = '0';
    hint.style.transform = 'translateY(-10px)';
    hint.style.transition = '0.25s ease';
    setTimeout(() => hint.remove(), 250);
  }
}

// --- Patch switchView to show contextual hints ---
const _switchViewBeforeHelp = switchView;
switchView = function(view) {
  _switchViewBeforeHelp(view);
  // Remove existing hints when switching
  document.querySelectorAll('.view-hint').forEach(h => h.remove());
  // Show hint for new view after a short delay
  setTimeout(() => showViewHint(view), 200);
};

// --- Init on load (only if authenticated) ---
document.addEventListener('DOMContentLoaded', () => {
  // Wait for auth — only init help/onboarding after app is loaded
  const waitForApp = setInterval(() => {
    if (!appInitialized) return;
    clearInterval(waitForApp);

    setTimeout(initHelpTooltips, 1500);
    if (!localStorage.getItem('onboarding_done')) {
      setTimeout(startOnboarding, 2000);
    }
    setTimeout(() => showViewHint('tasks'), 1800);
  }, 500);
});
