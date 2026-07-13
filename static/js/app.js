let newsData = { today: { date: '', items: [] }, yesterday: { date: '', items: [] }, day_before_yesterday: { date: '', items: [] } };
let currentDay = 'today';
let currentFilters = { q: '', tag: '', source: '' };
let eventSource = null;

// Clock (UTC+7)
function updateClock() {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Bangkok',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
  document.getElementById('clock').textContent = fmt.format(new Date()) + ' UTC+7';
}
setInterval(updateClock, 1000);
updateClock();

async function fetchNews() {
  try {
    const res = await fetch('/api/news');
    const json = await res.json();
    newsData = json;
    updateHeaderStats();
    populateFilters();
    initGrid(currentDay);
  } catch (e) {
    const grid = document.getElementById('intelGrid');
    grid.innerHTML = '';
    const err = document.createElement('div');
    err.className = 'loading';
    err.textContent = '// CONNECTION ERROR // CHECK API ENDPOINT';
    grid.appendChild(err);
  }
}

function updateHeaderStats() {
  const itemCount = (newsData.today?.items?.length || 0) + (newsData.yesterday?.items?.length || 0) + (newsData.day_before_yesterday?.items?.length || 0);
  document.getElementById('itemCount').textContent = itemCount + ' items loaded';
  document.getElementById('tabToday').textContent = newsData.today?.date || 'today';
  document.getElementById('tabYesterday').textContent = newsData.yesterday?.date || 'yesterday';
  document.getElementById('tabDBY').textContent = newsData.day_before_yesterday?.date || 'two days ago';
  document.getElementById('lastUpdated').textContent = 'Last Update: ' + (newsData.today?.date || '-');
}

function getFilteredItems(day) {
  let items = newsData[day]?.items || [];
  if (currentFilters.q) {
    const q = currentFilters.q.toLowerCase();
    items = items.filter(i => (i.title + ' ' + i.summary + ' ' + i.desc).toLowerCase().includes(q));
  }
  if (currentFilters.tag) {
    items = items.filter(i => (i.tag || '').toLowerCase().includes(currentFilters.tag.toLowerCase()));
  }
  if (currentFilters.source) {
    items = items.filter(i => (i.source || '').toLowerCase() === currentFilters.source.toLowerCase());
  }
  return items;
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function setText(el, text) {
  el.textContent = text;
}

function initGrid(day) {
  const grid = document.getElementById('intelGrid');
  const items = getFilteredItems(day);
  grid.innerHTML = '';
  if (items.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'loading';
    empty.textContent = '// NO DATA FOR THIS SECTOR';
    grid.appendChild(empty);
    return;
  }
  items.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = 'card' + (item.is_read ? ' read' : '');
    card.dataset.id = item.id;
    card.onclick = (e) => { if (!e.target.closest('.bookmark-btn')) openModal(day, idx); };

    const header = document.createElement('div');
    header.className = 'card-header';
    const iconBox = document.createElement('div');
    iconBox.className = 'icon-box';
    setText(iconBox, String(idx + 1).padStart(2, '0'));
    const unit = document.createElement('span');
    unit.style.cssText = 'font-weight:700; color:#fff; font-size:.75rem;';
    setText(unit, `${day.toUpperCase()} — UNIT_${String(idx + 1).padStart(2, '0')}`);
    header.appendChild(iconBox);
    header.appendChild(unit);
    card.appendChild(header);

    const content = document.createElement('div');
    content.className = 'card-content';
    const tag = document.createElement('span');
    tag.className = 'tag';
    setText(tag, item.tag || 'General / Tech');
    content.appendChild(tag);
    const title = document.createElement('div');
    title.className = 'title';
    setText(title, item.title);
    content.appendChild(title);
    const desc = document.createElement('div');
    desc.className = 'description';
    setText(desc, item.desc || '');
    content.appendChild(desc);
    card.appendChild(content);

    const actions = document.createElement('div');
    actions.className = 'card-actions';
    const source = document.createElement('span');
    source.className = 'source-label';
    setText(source, item.source || 'Unknown');
    actions.appendChild(source);
    const btn = document.createElement('button');
    btn.className = 'bookmark-btn' + (item.is_bookmarked ? ' active' : '');
    btn.onclick = () => toggleBookmark(item.id, btn);
    setText(btn, item.is_bookmarked ? '★ Bookmarked' : '☆ Bookmark');
    actions.appendChild(btn);
    card.appendChild(actions);

    grid.appendChild(card);
  });
}

async function toggleBookmark(id, btn) {
  const key = getApiKey();
  try {
    const res = await fetch(`/api/articles/${id}/bookmark`, { method: 'POST', headers: key ? {'Authorization': `Bearer ${key}`} : {} });
    if (!res.ok) throw new Error(`${res.status}`);
    const json = await res.json();
    btn.classList.toggle('active', json.is_bookmarked);
    btn.textContent = json.is_bookmarked ? '★ Bookmarked' : '☆ Bookmark';
    const item = findItemById(id);
    if (item) item.is_bookmarked = json.is_bookmarked;
    loadBookmarks();
  } catch (e) {
    showToast('Bookmark failed: ' + e.message);
  }
}

function setErrorDisplay(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'loading';
  div.textContent = message;
  el.appendChild(div);
}

function findItemById(id) {
  for (const day of ['today', 'yesterday', 'day_before_yesterday']) {
    const found = newsData[day].items.find(i => i.id === id);
    if (found) return found;
  }
  return null;
}

function openModal(day, idx) {
  const item = getFilteredItems(day)[idx];
  if (!item) return;
  document.getElementById('modalTag').textContent = item.tag || 'General / Tech';
  document.getElementById('modalTitle').textContent = item.title;
  document.getElementById('modalSummary').textContent = item.summary || item.desc || 'No summary available.';
  document.getElementById('modalImportance').textContent = item.importance || 'No analysis available.';
  document.getElementById('modalNoteworthy').textContent = item.noteworthy || 'No action items available.';
  document.getElementById('modalLink').href = item.link;
  document.getElementById('modalOverlay').style.display = 'flex';
  const key = getApiKey();
  fetch(`/api/articles/${item.id}/read`, { method: 'POST', headers: key ? {'Authorization': `Bearer ${key}`} : {} }).then(r => {
    if (!r.ok) throw new Error(r.status);
    item.is_read = true;
    initGrid(currentDay);
  }).catch(() => {});
}

function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; }

function getApiKey() {
  const input = document.getElementById('apiKeyInput');
  return input ? input.value.trim() : '';
}

function saveApiKey() {
  const key = getApiKey();
  if (key) localStorage.setItem('dash_api_key', key);
}

function loadApiKey() {
  const input = document.getElementById('apiKeyInput');
  const saved = localStorage.getItem('dash_api_key');
  if (input && saved) input.value = saved;
}

function bindButton(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('click', handler);
}

const TOOL_ACTIONS = {
  bold: ['**', '**'],
  italic: ['*', '*'],
  strike: ['~~', '~~'],
  code: ['`', '`'],
  link: ['[', ']()'],
  bullet: ['\n- ', ''],
  checkbox: ['\n- [ ] ', ''],
  numbered: ['\n1. ', ''],
  quote: ['\n> ', ''],
  heading: ['###### ', ''],
  hr: ['---\n', ''],
  spoiler: ['||', '||'],
  highlight: ['==', '=='],
  'highlight-yellow': ['==', '=='],
  codeblock: ['\n```\n', '\n```\n'],
};

function bindToolbar() {
  document.querySelectorAll('.tool-btn[data-action]').forEach(btn => {
    const action = TOOL_ACTIONS[btn.dataset.action];
    if (!action) return;
    btn.addEventListener('click', () => insertText(action[0], action[1]));
  });
}

// Date tabs
document.getElementById('dateTabs').addEventListener('click', e => {
  const tab = e.target.closest('.date-tab');
  if (tab) {
    document.querySelectorAll('.date-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentDay = tab.dataset.day;
    initGrid(currentDay);
  }
});

// Side pane tabs
document.querySelector('.pane-tabs').addEventListener('click', e => {
  const tab = e.target.closest('.pane-tab');
  if (tab) {
    document.querySelectorAll('.pane-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.pane-body').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('pane-' + tab.dataset.pane).classList.add('active');
    if (tab.dataset.pane === 'sources') loadSources();
    if (tab.dataset.pane === 'bookmarks') loadBookmarks();
  }
});

// Search/filters
document.getElementById('searchBox').addEventListener('input', e => {
  currentFilters.q = e.target.value;
  initGrid(currentDay);
});
document.getElementById('tagFilter').addEventListener('change', e => {
  currentFilters.tag = e.target.value;
  initGrid(currentDay);
});
document.getElementById('sourceFilter').addEventListener('change', e => {
  currentFilters.source = e.target.value;
  initGrid(currentDay);
});

function populateFilters() {
  const tagSet = new Set();
  const sourceSet = new Set();
  for (const day of ['today', 'yesterday', 'day_before_yesterday']) {
    (newsData[day].items || []).forEach(i => {
      if (i.tag) tagSet.add(String(i.tag));
      if (i.source) sourceSet.add(String(i.source));
    });
  }
  const tagSel = document.getElementById('tagFilter');
  const savedTag = tagSel.value;
  tagSel.innerHTML = '';
  const allTags = document.createElement('option');
  allTags.value = '';
  allTags.textContent = 'All Tags';
  tagSel.appendChild(allTags);
  Array.from(tagSet).sort().forEach(t => {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    tagSel.appendChild(opt);
  });
  tagSel.value = savedTag;

  const srcSel = document.getElementById('sourceFilter');
  const savedSrc = srcSel.value;
  srcSel.innerHTML = '';
  const allSrc = document.createElement('option');
  allSrc.value = '';
  allSrc.textContent = 'All Sources';
  srcSel.appendChild(allSrc);
  Array.from(sourceSet).sort().forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    srcSel.appendChild(opt);
  });
  srcSel.value = savedSrc;
}

// Sources pane
async function loadSources() {
  try {
    const res = await fetch('/api/sources');
    const sources = await res.json();
    const container = document.getElementById('sourcesList');
    container.innerHTML = '';
    if (!sources.length) {
      const empty = document.createElement('div');
      empty.className = 'loading';
      empty.textContent = '// No source status yet';
      container.appendChild(empty);
      return;
    }
    sources.forEach(s => {
      const statusClass = s.status === 'ok' ? 'ok' : (s.status === 'error' ? 'error' : 'unknown');
      const time = s.last_fetch ? new Date(s.last_fetch).toLocaleString() : 'never';

      const item = document.createElement('div');
      item.className = 'source-item';
      const body = document.createElement('div');
      const sourceName = document.createElement('div');
      sourceName.className = 'source-name';
      const dot = document.createElement('span');
      dot.className = 'status-dot ' + statusClass;
      sourceName.appendChild(dot);
      const nameText = document.createTextNode(s.source);
      sourceName.appendChild(nameText);
      body.appendChild(sourceName);

      const meta = document.createElement('div');
      meta.className = 'source-meta';
      meta.textContent = `${time} · ${s.item_count} new articles`;
      body.appendChild(meta);

      if (s.error_message) {
        const err = document.createElement('div');
        err.className = 'source-meta';
        err.style.color = 'var(--accent)';
        err.textContent = s.error_message;
        body.appendChild(err);
      }

      item.appendChild(body);
      container.appendChild(item);
    });
  } catch (e) {
    const container = document.getElementById('sourcesList');
    container.innerHTML = '';
    const err = document.createElement('div');
    err.className = 'loading';
    err.textContent = '// Source error';
    container.appendChild(err);
  }
}

// Bookmarks pane
async function loadBookmarks() {
  try {
    const res = await fetch('/api/bookmarks');
    const bookmarks = await res.json();
    const container = document.getElementById('bookmarksList');
    container.innerHTML = '';
    if (!bookmarks.length) {
      const empty = document.createElement('div');
      empty.className = 'loading';
      empty.textContent = '// No bookmarks';
      container.appendChild(empty);
      return;
    }
    bookmarks.forEach(b => {
      const item = document.createElement('div');
      item.className = 'bm-item';
      item.onclick = () => openBookmarkById(b.id);
      const title = document.createElement('div');
      title.className = 'bm-title';
      title.textContent = b.title;
      const tag = document.createElement('div');
      tag.className = 'bm-tag';
      tag.textContent = `${b.tag || 'General / Tech'} · ${b.source || 'Unknown'}`;
      item.appendChild(title);
      item.appendChild(tag);
      container.appendChild(item);
    });
  } catch (e) {
    const container = document.getElementById('bookmarksList');
    container.innerHTML = '';
    const err = document.createElement('div');
    err.className = 'loading';
    err.textContent = '// Bookmark error';
    container.appendChild(err);
  }
}

function openBookmarkById(id) {
  fetch(`/api/articles/${id}`).then(r => r.json()).then(item => {
    document.getElementById('modalTag').textContent = item.tag || 'General / Tech';
    document.getElementById('modalTitle').textContent = item.title;
    document.getElementById('modalSummary').textContent = item.summary || item.desc || 'No summary available.';
    document.getElementById('modalImportance').textContent = item.importance || 'No analysis available.';
    document.getElementById('modalNoteworthy').textContent = item.noteworthy || 'No action items available.';
    document.getElementById('modalLink').href = item.url;
    document.getElementById('modalOverlay').style.display = 'flex';
  });
}

// Notes system
const editor = document.getElementById('notes-editor');
const vaultPathInput = document.getElementById('vaultPath');
function loadNotes() {
  const s = localStorage.getItem('dash_notes_v3');
  if (s) editor.value = s;
  const v = localStorage.getItem('dash_vault_path');
  if (v) vaultPathInput.value = v;
}
function saveNotes() { localStorage.setItem('dash_notes_v3', editor.value); }
function clearNotes() { if(confirm('Clear all notes?')) { editor.value = ''; saveNotes(); } }
function insertText(before, after) {
  const s = editor.selectionStart, e = editor.selectionEnd, t = editor.value;
  editor.value = t.slice(0, s) + before + t.slice(s, e) + after + t.slice(e);
  editor.focus();
  editor.setSelectionRange(s + before.length, s + before.length);
  saveNotes();
}
vaultPathInput.addEventListener('input', () => localStorage.setItem('dash_vault_path', vaultPathInput.value));

async function exportToObsidian() {
  saveApiKey();
  const key = getApiKey();
  const text = editor.value;
  const now = new Date();
  const dateStamp = now.toISOString().split('T')[0];
  const content = `---\ndate: ${dateStamp}\ntags: [daily-digest, intelligence, dashboard]\nsource: ${window.location.origin}\n---\n\n${text}`;
  const vaultPath = vaultPathInput.value || null;
  const headers = {'Content-Type':'application/json'};
  if (key) headers['Authorization'] = `Bearer ${key}`;
  try {
    const res = await fetch('/api/export', { method:'POST', headers, body: JSON.stringify({content, vault_path: vaultPath}) });
    const json = await res.json();
    const msg = document.getElementById('exportMsg');
    if(json.success) { msg.textContent = 'Saved: ' + json.file.split('/').pop(); msg.style.color = 'var(--green)'; }
    else { msg.textContent = 'Export failed: ' + (json.detail || res.status); msg.style.color = 'var(--accent)'; }
    setTimeout(() => msg.textContent = '', 5000);
  } catch(err) {
    const msg = document.getElementById('exportMsg');
    msg.textContent = 'Server error — falling back to download';
    msg.style.color = 'var(--yellow)';
    const blob = new Blob([content], {type:'text/markdown'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'daily-digest-'+dateStamp+'.md'; a.click();
    URL.revokeObjectURL(url);
    setTimeout(() => msg.textContent = '', 5000);
  }
}

// Modal close on overlay click
document.getElementById('modalOverlay').addEventListener('click', e => { if(e.target.id === 'modalOverlay') closeModal(); });

// Update trigger
async function triggerUpdate() {
  const btn = document.getElementById('refreshBtn');
  btn.disabled = true;
  btn.textContent = 'Refreshing...';
  saveApiKey();
  const key = getApiKey();
  try {
    const res = await fetch('/api/trigger-update', { method: 'POST', headers: key ? {'Authorization': `Bearer ${key}`} : {} });
    if (res.ok) {
      showToast('Update triggered');
    } else {
      const body = await res.json().catch(() => ({}));
      showToast(`Trigger failed: ${res.status} ${body.detail || res.statusText}`);
    }
  } catch (e) {
    showToast('Trigger failed: ' + e.message);
  } finally {
    setTimeout(() => { btn.disabled = false; btn.textContent = 'Refresh Now'; }, 3000);
  }
}

// SSE
function connectSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/api/events');
  eventSource.addEventListener('news_updated', e => {
    const data = JSON.parse(e.data);
    showToast(`${data.new_articles} new articles · ${data.errors} errors`);
    fetchNews();
    loadSources();
  });
  eventSource.addEventListener('ping', () => {});
  eventSource.onerror = () => {
    // Fallback polling if SSE fails
    setTimeout(connectSSE, 5000);
  };
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 4000);
}

function togglePane() {
  document.getElementById('sidePane').classList.toggle('open');
}

window.onload = () => {
  fetchNews();
  loadSources();
  loadBookmarks();
  loadNotes();
  loadApiKey();
  const apiKeyInput = document.getElementById('apiKeyInput');
  if (apiKeyInput) apiKeyInput.addEventListener('input', saveApiKey);
  editor.addEventListener('input', saveNotes);
  bindButton('refreshBtn', triggerUpdate);
  bindButton('modalCloseBtn', closeModal);
  bindButton('mobileToggle', togglePane);
  bindButton('clearNotesBtn', clearNotes);
  bindButton('exportBtn', exportToObsidian);
  bindToolbar();
  connectSSE();
  setInterval(() => { fetchNews(); loadSources(); }, 60000);
};
