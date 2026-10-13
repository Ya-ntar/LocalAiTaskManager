document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => {
  document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.id === button.dataset.tab));
  document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
  sessionStorage.setItem('board-tab', button.dataset.tab);
});
const initialTab = sessionStorage.getItem('board-tab') || 'kanban';
document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.id === initialTab));
document.querySelectorAll('[data-tab]').forEach(button => {
  button.classList.toggle('active', button.dataset.tab === initialTab);
});
async function boardAction(action) {
  const form = document.querySelector('#relation-form');
  const data = new FormData(form);
  const payload = {action, task: data.get('task'), related_task: data.get('related_task'), text: data.get('text')};
  const response = await fetch('/board/action', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || 'Ошибка операции'); return; }
  alert(result.result);
  reloadBoard();
}
async function taskAction(action, task) {
  const related = document.querySelector('#related-' + CSS.escape(task));
  const subtask = document.querySelector('#subtask-' + CSS.escape(task));
  const selected = related ? related.value : '';
  const text = subtask ? subtask.value : '';
  const title = document.querySelector('#title-' + CSS.escape(task));
  const importance = document.querySelector('#importance-' + CSS.escape(task));
  const minutes = document.querySelector('#minutes-' + CSS.escape(task));
  const picker = document.querySelector('#task-modal .theme-picker');
  if (action === 'archive' && !confirm('Переместить задачу в архив?')) return;
  if (action === 'delete' && !confirm('Удалить задачу окончательно? Это действие нельзя отменить.')) return;
  if (action === 'subtask' && !text.trim()) { alert('Введите название подзадачи'); return; }
  if (action === 'edit' && (!title.value.trim() || Number(importance.value) < 0 || Number(importance.value) > 1 || Number(minutes.value) < 0)) {
    alert('Проверьте название, приоритет от 0 до 1 и длительность'); return;
  }
  const response = await fetch('/board/action', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action, task, related_task: selected, text,
      title: title ? title.value : null,
      importance: importance ? Number(importance.value) : null,
      minutes: minutes ? Number(minutes.value) : null,
      tags: picker ? selectedThemes(picker) : null})
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || 'Ошибка операции'); return; }
  alert(result.result);
  reloadBoard();
}
function showTask(id) {
  const source = document.querySelector('#task-details-' + CSS.escape(id));
  const body = document.querySelector('#task-modal-body');
  const modal = document.querySelector('#task-modal');
  if (!source || !body || !modal) return;
  body.innerHTML = source.innerHTML;
  modal.hidden = false;
  setupThemePicker(body.querySelector('.theme-picker'));
}
function editTitle(id) {
  const title = document.querySelector('#task-modal .task-title') ||
    document.querySelector('#task-details-' + CSS.escape(id) + ' .task-title');
  if (!title || title.querySelector('input')) return;
  const input = document.createElement('input');
  input.value = title.textContent;
  input.className = 'inline-title';
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') saveInlineTitle(id, input.value);
    if (event.key === 'Escape') showTask(id);
  });
  input.addEventListener('blur', () => saveInlineTitle(id, input.value));
  title.replaceChildren(input);
  input.focus();
  input.select();
}
async function saveInlineTitle(id, value) {
  if (!value.trim()) return;
  await sendBoardAction({action:'edit', task:id, title:value, importance:null, minutes:null, tags:null});
}
async function addTask(column) {
  const modal = document.querySelector('#task-create-modal');
  const title = document.querySelector('#new-task-title');
  if (!modal || !title) return;
  modal.dataset.column = column;
  title.value = '';
  modal.hidden = false;
  setupThemePicker(document.querySelector('#new-task-themes'));
  title.focus();
}
async function saveNewTask() {
  const modal = document.querySelector('#task-create-modal');
  const title = document.querySelector('#new-task-title');
  if (!modal || !title || !title.value.trim()) {
    alert('Введите название задачи');
    return;
  }
  await sendBoardAction({
    action: 'add', column: modal.dataset.column, title: title.value.trim(),
    tags: selectedThemes(document.querySelector('#new-task-themes'))
  });
}
async function sendBoardAction(payload) {
  const response = await fetch('/board/action', {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || 'Ошибка операции'); return; }
  alert(result.result);
  reloadBoard();
}
function reloadBoard() {
  const selected = document.querySelector('.theme-list-item.active');
  if (selected) sessionStorage.setItem('board-theme', selected.dataset.theme);
  location.reload();
}
function closeTask() {
  const modal = document.querySelector('#task-modal');
  if (modal) modal.hidden = true;
}
function closeTaskCreator() {
  const modal = document.querySelector('#task-create-modal');
  if (modal) modal.hidden = true;
}
function selectedThemes(picker) {
  return picker
    ? [...picker.querySelectorAll('input[type="checkbox"]:checked')]
      .map(input => input.value)
      .filter(Boolean)
    : [];
}
function setupThemePicker(picker) {
  if (!picker || picker.dataset.ready) return;
  picker.dataset.ready = 'true';
  const search = picker.querySelector('.theme-search');
  if (!search) return;
  search.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    picker.querySelectorAll('.theme-options label').forEach(label => {
      label.hidden = query && !label.textContent.toLocaleLowerCase().includes(query);
    });
  });
}
function addTheme() {
  const name = prompt('Название новой темы:');
  if (name && name.trim()) sendBoardAction({action: 'add_theme', name: name.trim()});
}
function renameTheme(oldName) {
  const name = prompt('Новое название темы:', oldName);
  if (name && name.trim() && name.trim() !== oldName) {
    sendBoardAction({action: 'rename_theme', task: oldName, name: name.trim()});
  }
}
function deleteTheme(name) {
  if (!confirm('Удалить тему «' + name + '»? Тема будет убрана у всех задач.')) return;
  sendBoardAction({action: 'delete_theme', task: name});
}
function selectTheme(name) {
  sessionStorage.setItem('board-theme', name);
  document.querySelectorAll('.theme-list-item').forEach(item => {
    item.classList.toggle('active', item.dataset.theme === name);
  });
  document.querySelectorAll('.theme-task-panel').forEach(panel => {
    panel.hidden = panel.dataset.themePanel !== name;
  });
  const empty = document.querySelector('#theme-task-empty');
  if (empty) empty.hidden = Boolean(name);
}
function setupKanbanDragAndDrop() {
  document.querySelectorAll('.task-item[draggable="true"]').forEach(item => {
    item.addEventListener('dragstart', event => {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', item.dataset.taskId);
      item.classList.add('dragging');
    });
    item.addEventListener('dragend', () => item.classList.remove('dragging'));
  });
  document.querySelectorAll('[data-drop-column]').forEach(column => {
    column.addEventListener('dragover', event => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      column.classList.add('drag-over');
    });
    column.addEventListener('dragleave', event => {
      if (!column.contains(event.relatedTarget)) column.classList.remove('drag-over');
    });
    column.addEventListener('drop', event => {
      event.preventDefault();
      column.classList.remove('drag-over');
      const task = event.dataTransfer.getData('text/plain');
      if (task) sendBoardAction({
        action: 'move', task, column: column.dataset.dropColumn
      });
    });
  });
}
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.querySelector('#task-modal');
  if (modal) modal.addEventListener('click', event => {
    if (event.target.id === 'task-modal') closeTask();
  });
  document.querySelectorAll('.theme-picker').forEach(setupThemePicker);
  document.querySelectorAll('.theme-list-item').forEach(item => {
    item.addEventListener('click', event => {
      if (event.target.closest('.theme-rename')) {
        renameTheme(item.dataset.theme);
      } else {
        selectTheme(item.dataset.theme);
      }
    });
  });
  const themeSearch = document.querySelector('#theme-search');
  if (themeSearch) themeSearch.addEventListener('input', () => {
    const query = themeSearch.value.trim().toLocaleLowerCase();
    document.querySelectorAll('.theme-list-item').forEach(item => {
      item.hidden = query && !item.dataset.theme.toLocaleLowerCase().includes(query);
    });
    setupKanbanDragAndDrop();
  });
  const savedTheme = sessionStorage.getItem('board-theme');
  const savedItem = [...document.querySelectorAll('.theme-list-item')]
    .find(item => item.dataset.theme === savedTheme);
  if (savedItem) selectTheme(savedItem.dataset.theme);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    closeTask();
    closeTaskCreator();
  }
});
