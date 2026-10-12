document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => {
  document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('active', tab.id === button.dataset.tab));
  document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
});
document.querySelector('[data-tab]').classList.add('active');
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
  location.reload();
}
async function taskAction(action, task) {
  const related = document.querySelector('#related-' + CSS.escape(task));
  const subtask = document.querySelector('#subtask-' + CSS.escape(task));
  const selected = related ? related.value : '';
  const text = subtask ? subtask.value : '';
  const title = document.querySelector('#title-' + CSS.escape(task));
  const importance = document.querySelector('#importance-' + CSS.escape(task));
  const minutes = document.querySelector('#minutes-' + CSS.escape(task));
  const tags = document.querySelector('#tags-' + CSS.escape(task));
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
      tags: tags ? tags.value.split(',').map(item => item.trim()).filter(Boolean) : null})
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || 'Ошибка операции'); return; }
  alert(result.result);
  location.reload();
}
function showTask(id) {
  const source = document.querySelector('#task-details-' + CSS.escape(id));
  const body = document.querySelector('#task-modal-body');
  const modal = document.querySelector('#task-modal');
  if (!source || !body || !modal) return;
  body.innerHTML = source.innerHTML;
  modal.hidden = false;
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
  const title = prompt('Название новой задачи:');
  if (!title || !title.trim()) return;
  const tags = prompt('Темы/теги через запятую (необязательно):') || '';
  await sendBoardAction({action:'add', column, title:title.trim(), tags:tags.split(',').map(item => item.trim()).filter(Boolean)});
}
async function sendBoardAction(payload) {
  const response = await fetch('/board/action', {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) { alert(result.error || 'Ошибка операции'); return; }
  alert(result.result);
  location.reload();
}
function closeTask() {
  const modal = document.querySelector('#task-modal');
  if (modal) modal.hidden = true;
}
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.querySelector('#task-modal');
  if (modal) modal.addEventListener('click', event => {
    if (event.target.id === 'task-modal') closeTask();
  });
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closeTask();
});
