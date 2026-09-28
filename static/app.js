const $ = id => document.getElementById(id);
const history = [];
let busy = false;
const setStatus = (message, error = false) => { $('status').textContent = message; $('status').classList.toggle('error', error); };
async function api(path, options = {}) {
  const response = await fetch(path, {credentials:'same-origin', ...options});
  let data;
  try { data = await response.json(); } catch { throw new Error('The server did not respond as expected.'); }
  if (!response.ok) throw new Error(data.detail || 'Something went wrong.');
  return data;
}
function renderDocuments(documents) {
  $('documents').replaceChildren();
  for (const doc of documents) {
    const li = document.createElement('li');
    li.textContent = '▤  ' + doc.name;
    const meta = document.createElement('small'); meta.textContent = `${doc.pages} readable pages`;
    li.append(meta); $('documents').append(li);
  }
}
function addMessage(role, content, sources = []) {
  $('empty').hidden = true;
  const message = document.createElement('div'); message.className = 'message ' + role;
  message.textContent = content;
  if (sources.length) {
    const list = document.createElement('div'); list.className = 'sources';
    for (const source of sources) {
      const item = document.createElement('span');
      item.textContent = `[${source.number}] ${source.filename} · p. ${source.page}`;
      list.append(item);
    }
    message.append(list);
  }
  $('chat').append(message); $('chat').scrollTop = $('chat').scrollHeight;
  return message;
}
async function upload(files) {
  if (busy || !files.length) return;
  if (files.length > 5 || [...files].reduce((sum, file) => sum + file.size, 0) > 4 * 1024 * 1024 || [...files].some(f => f.size > 4 * 1024 * 1024 || !f.name.toLowerCase().endsWith('.pdf'))) {
    setStatus('Select up to five PDFs, with a combined upload no larger than 4 MB.', true); return;
  }
  busy = true; setStatus(`Processing ${files.length} ${files.length === 1 ? 'PDF' : 'PDFs'}… This may take a minute.`);
  const body = new FormData(); for (const file of files) body.append('files', file);
  try {
    const result = await api('/api/upload', {method:'POST', body});
    renderDocuments(result.documents);
    const successes = result.results.filter(r => r.document).length;
    const failures = result.results.filter(r => r.error).map(r => `${r.name}: ${r.error}`);
    setStatus([successes ? `${successes} ready to explore.` : '', ...failures].filter(Boolean).join(' '), !!failures.length);
  } catch (error) { setStatus(error.message, true); }
  finally { busy = false; $('files').value = ''; }
}
$('files').addEventListener('change', event => upload(event.target.files));
const drop = $('drop');
for (const name of ['dragenter','dragover']) drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('drag'); });
for (const name of ['dragleave','drop']) drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('drag'); });
drop.addEventListener('drop', event => upload(event.dataTransfer.files));
$('form').addEventListener('submit', async event => {
  event.preventDefault(); const question = $('question').value.trim(); if (!question || busy) return;
  busy = true; $('send').disabled = true; $('question').value = '';
  const prior = history.slice(-12); addMessage('user', question);
  const loading = addMessage('assistant', 'Looking through your documents…');
  try {
    const result = await api('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, history:prior})});
    loading.remove(); addMessage('assistant', result.answer, result.sources);
    history.push({role:'user',content:question},{role:'assistant',content:result.answer});
  } catch (error) { loading.remove(); addMessage('assistant', error.message); }
  finally { busy = false; $('send').disabled = false; $('question').focus(); }
});
$('question').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('form').requestSubmit(); } });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { $('question').value = button.dataset.prompt; $('question').focus(); }));
$('clear').addEventListener('click', async () => {
  if (busy || !confirm('Delete all uploaded documents in this workspace and clear this chat?')) return;
  busy = true;
  try { await api('/api/workspace', {method:'DELETE'}); renderDocuments([]); history.length = 0; $('chat').querySelectorAll('.message').forEach(node => node.remove()); $('empty').hidden = false; setStatus('Workspace cleared.'); }
  catch (error) { setStatus(error.message, true); }
  finally { busy = false; }
});
api('/api/documents').then(data => renderDocuments(data.documents)).catch(error => setStatus(error.message, true));
