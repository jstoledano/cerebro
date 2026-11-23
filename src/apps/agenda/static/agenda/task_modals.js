/* Fichas de actividad compartidas entre dashboard y pendientes generales. */
(() => {
  'use strict';
  const modal = document.getElementById('agenda-task-modal');
  if (!modal) return;
  const detailUrl = modal.dataset.detailUrl;
  const stateUrl = modal.dataset.stateUrl;
  const byId = id => document.getElementById(id);
  const form = byId('agenda-state-form');
  const result = byId('agenda-state-result');
  let current = null;
  const text = (tag, value, classes) => {
    const el = document.createElement(tag);
    el.textContent = String(value ?? '');
    if (classes) el.className = classes;
    return el;
  };
  const propsLabels = {
    PLAN:'Proyecto', SCOPE:'Ámbito', REFERENCE:'Referencia', OWNER:'Responsable',
    OPERATIVE:'Operativo', MONITOR:'Monitor', NEXT_REVIEW:'Próxima revisión'
  };
  const csrf = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
  function render(task) {
    current = task;
    byId('agenda-modal-id').textContent = task.id;
    byId('agenda-modal-title').textContent = task.title;
    const meta = byId('agenda-modal-meta');
    meta.replaceChildren();
    [task.state, task.priority].filter(Boolean).forEach(value => meta.appendChild(text('span', value, 'badge badge-outline')));
    const properties = byId('agenda-modal-properties');
    properties.replaceChildren();
    const fields = {
      'Inicio':task.scheduled, 'Vencimiento':task.deadline, 'Cierre':task.closed,
      ...Object.fromEntries(Object.entries(task.properties || {}).map(([key,value]) => [propsLabels[key] || key, value])),
      'Fuente':task.source
    };
    for (const [label, value] of Object.entries(fields)) {
      if (!value) continue;
      const box = text('div', '', 'rounded-lg bg-base-200/60 p-3 min-w-0');
      box.append(text('div', label, 'text-xs opacity-60'), text('div', value, 'mt-1 font-medium break-words'));
      properties.appendChild(box);
    }
    byId('agenda-modal-body').textContent = task.body || '';
    byId('agenda-modal-body-wrap').classList.toggle('hidden', !task.body);
    const writable = task.can_edit && ['TODO', 'DONE'].includes(task.state);
    byId('agenda-state-form-wrap').classList.toggle('hidden', !writable);
    byId('agenda-state-select').value = task.state === 'TODO' ? 'DONE' : 'TODO';
    byId('agenda-state-note').value = '';
    result.textContent = '';
  }
  async function open(taskId) {
    if (!taskId) return;
    current = null;
    byId('agenda-modal-id').textContent = taskId;
    byId('agenda-modal-title').textContent = 'Cargando ficha…';
    byId('agenda-modal-meta').replaceChildren();
    byId('agenda-modal-properties').replaceChildren();
    byId('agenda-modal-body-wrap').classList.add('hidden');
    byId('agenda-state-form-wrap').classList.add('hidden');
    modal.showModal();
    try {
      const response = await fetch(detailUrl + '?id=' + encodeURIComponent(taskId), {headers:{Accept:'application/json'}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se pudo cargar la ficha.');
      render(data);
    } catch (error) {
      byId('agenda-modal-title').textContent = 'Ficha no disponible';
      byId('agenda-modal-properties').appendChild(text('p', error.message, 'text-error'));
    }
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-agenda-task-id]');
    if (!link) return;
    event.preventDefault();
    open(link.dataset.agendaTaskId);
  });
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!current) return;
    const note = byId('agenda-state-note').value.trim();
    if (note.length < 3) {result.textContent = 'Escribe una nota de al menos tres caracteres.'; return;}
    const button = byId('agenda-state-submit');
    button.disabled = true;
    result.textContent = 'Actualizando actividad y sincronizando…';
    try {
      const response = await fetch(stateUrl, {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json', 'X-CSRFToken':decodeURIComponent(csrf()), Accept:'application/json'},
        body:JSON.stringify({id:current.id, state:byId('agenda-state-select').value, note})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se pudo guardar.');
      result.textContent = 'Cambio registrado y sincronizado. Actualizando…';
      window.location.reload();
    } catch (error) {
      result.textContent = error.message;
      result.classList.add('text-error');
    } finally {button.disabled = false;}
  });
  window.AgendaTaskModal = {open};
})();
