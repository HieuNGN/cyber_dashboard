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
    document.getElementById('intelGrid').innerHTML = '<div class="loading">// CONNECTION ERROR // CHECK API ENDPOINT</div>';
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

function initGrid(day) {
  const grid = document.getElementById('intelGrid');
  const items = getFilteredItems(day);
  grid.innerHTML = '';
  if (items.length === 0) {
    grid.innerHTML = '<div class="loading">// NO DATA FOR THIS SECTOR</div>';
    return;
  }
  items.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = 'card' + (item.is_read ? ' read' : '');
    card.dataset.id = item.id;
    card.onclick = (e) => { if (!e.target.closest('.bookmark-btn')) openModal(day, idx); };
    card.innerHTML = `
      <div class="card-header">
        <div class="icon-box">${String(idx + 1).padStart(2, '0')}</div>
        <span style="font-weight:700; color:#fff; font-size:.75rem;">${day.toUpperCase()} — UNIT_${String(idx + 1).padStart(2, '0')}</span>
      </div>
      <div class="card-content">
        <span class="tag">${item.tag || 'General / Tech'}</span>
        <div class="title">${item.title}</div>
        <div class="description">${item.desc || ''}</div>
      </div>
      <div class="card-actions">
        <span class="source-label">${item.source || 'Unknown'}</span>
        <button class="bookmark-btn ${item.is_bookmarked ? 'active' : ''}" onclick="toggleBookmark(${item.id}, this)">
          ${item.is_bookmarked ? '★ Bookmarked' : '☆ Bookmark'}
        </button>
      </div>`;
    grid.appendChild(card);
  });
}

async function toggleBookmark(id, btn) {
  try {
    const res = await fetch(`/api/articles/${id}/bookmark`, { method: 'POST' });
    const json = await res.json();
    btn.classList.toggle('active', json.is_bookmarked);
    btn.textContent = json.is_bookmarked ? '★ Bookmarked' : '☆ Bookmark';
    const item = findItemById(id);
    if (item) item.is_bookmarked = json.is_bookmarked;
    loadBookmarks();
  } catch (e) {
    showToast('Bookmark failed');
  }
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
  fetch(`/api/articles/${item.id}/read`, { method: 'POST' }).then(() => {
    item.is_read = true;
    initGrid(currentDay);
  });
}

function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; }

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
      if (i.tag) tagSet.add(i.tag);
      if (i.source) sourceSet.add(i.source);
    });
  }
  const tagSel = document.getElementById('tagFilter');
  const savedTag = tagSel.value;
  tagSel.innerHTML = '<option value="">All Tags</option>' + Array.from(tagSet).sort().map(t => `<option value="${t}">${t}</option>`).join('');
  tagSel.value = savedTag;

  const srcSel = document.getElementById('sourceFilter');
  const savedSrc = srcSel.value;
  srcSel.innerHTML = '<option value="">All Sources</option>' + Array.from(sourceSet).sort().map(s => `<option value="${s}">${s}</option>`).join('');
  srcSel.value = savedSrc;
}

// Sources pane
async function loadSources() {
  try {
    const res = await fetch('/api/sources');
    const sources = await res.json();
    const container = document.getElementById('sourcesList');
    if (!sources.length) {
      container.innerHTML = '<div class="loading">// No source status yet</div>';
      return;
    }
    container.innerHTML = sources.map(s => {
      const statusClass = s.status === 'ok' ? 'ok' : (s.status === 'error' ? 'error' : 'unknown');
      const time = s.last_fetch ? new Date(s.last_fetch).toLocaleString() : 'never';
      return `<div class="source-item">
        <div>
          <div class="source-name"><span class="status-dot ${statusClass}"></span>${s.source}</div>
          <div class="source-meta">${time} · ${s.item_count} new articles</div>
          ${s.error_message ? `<div class="source-meta" style="color:var(--accent)">${s.error_message}</div>` : ''}
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    document.getElementById('sourcesList').innerHTML = '<div class="loading">// Source error</div>';
  }
}

// Bookmarks pane
async function loadBookmarks() {
  try {
    const res = await fetch('/api/bookmarks');
    const bookmarks = await res.json();
    const container = document.getElementById('bookmarksList');
    if (!bookmarks.length) {
      container.innerHTML = '<div class="loading">// No bookmarks</div>';
      return;
    }
    container.innerHTML = bookmarks.map(b => `
      <div class="bm-item" onclick="openBookmarkById(${b.id})">
        <div class="bm-title">${b.title}</div>
        <div class="bm-tag">${b.tag || 'General / Tech'} · ${b.source || 'Unknown'}</div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('bookmarksList').innerHTML = '<div class="loading">// Bookmark error</div>';
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
  const text = editor.value;
  const now = new Date();
  const dateStamp = now.toISOString().split('T')[0];
  const content = `---\ndate: ${dateStamp}\ntags: [daily-digest, intelligence, dashboard]\nsource: ${window.location.origin}\n---\n\n${text}`;
  const vaultPath = vaultPathInput.value || null;
  try {
    const res = await fetch('/api/export', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({content, vault_path: vaultPath}) });
    const json = await res.json();
    const msg = document.getElementById('exportMsg');
    if(json.success) { msg.textContent = 'Saved: ' + json.file.split('/').pop(); msg.style.color = 'var(--green)'; }
    else { msg.textContent = 'Export failed'; msg.style.color = 'var(--accent)'; }
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
  try {
    await fetch('/api/trigger-update', { method: 'POST' });
    showToast('Update triggered');
  } catch (e) {
    showToast('Trigger failed');
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
  editor.addEventListener('input', saveNotes);
  connectSSE();
  setInterval(() => { fetchNews(); loadSources(); }, 60000);
};
