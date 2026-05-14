document.addEventListener('DOMContentLoaded', () => {

    // ── Estado global ─────────────────────────────────────────────────
    let currentUser = null;
    let currentDatasetId = null;
    let _allIngestions = [];       // cache para el filtro de ingestas
    let _pollingTimers = {};        // {ingestion_id: intervalId}

    // ── Helpers UI ────────────────────────────────────────────────────
    const $ = id => document.getElementById(id);
    const show = id => { const e = $(id); if (e) e.style.display = 'block'; };
    const hide = id => { const e = $(id); if (e) e.style.display = 'none'; };
    const flex = id => { const e = $(id); if (e) e.style.display = 'flex'; };

    // ── API helper — inyecta JWT automáticamente ──────────────────────
    async function api(url, opts = {}) {
        const token = localStorage.getItem('oar_token');
        const headers = { ...(opts.headers || {}) };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(url, { ...opts, headers });

        if (res.status === 401) {
            localStorage.clear();
            location.reload();
            return;
        }
        if (!res.ok) {
            let msg;
            try { const j = await res.json(); msg = j.detail || JSON.stringify(j); }
            catch { msg = await res.text(); }
            throw new Error(`${res.status}: ${msg}`);
        }
        return res.json();
    }

    // ══════════════════════════════════════════════════════════════════
    // AUTENTICACIÓN
    // ══════════════════════════════════════════════════════════════════
    function restoreSession() {
        try {
            const token = localStorage.getItem('oar_token');
            const user = JSON.parse(localStorage.getItem('oar_user') || 'null');
            if (token && user) { currentUser = user; showApp(user); return true; }
        } catch { localStorage.clear(); }
        return false;
    }

    function showApp(user) {
        hide('loginView');
        $('appContainer').style.display = 'grid';
        $('displayUser').textContent = user.username;
        $('displayRole').textContent = user.role.toUpperCase();
        $('avatarLetter').textContent = user.username[0].toUpperCase();
        // Ocultar "Configuración" si no es admin
        const settingsNavItem = document.querySelector('[data-view="settingsView"]');
        if (settingsNavItem && user.role !== 'admin') {
            settingsNavItem.style.display = 'none';
        }
        switchView('dashboardView');
    }

    $('loginForm').addEventListener('submit', async e => {
        e.preventDefault();
        const btn = $('loginBtn');
        btn.textContent = 'Ingresando...';
        btn.disabled = true;
        hide('loginError');
        try {
            const data = await api('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: $('username').value.trim(),
                    password: $('password').value,
                }),
            });
            localStorage.setItem('oar_token', data.token);
            localStorage.setItem('oar_user', JSON.stringify(data.user));
            currentUser = data.user;
            showApp(data.user);
        } catch (err) {
            console.error('Login error:', err.message);
            show('loginError');
        } finally {
            btn.textContent = 'Ingresar';
            btn.disabled = false;
        }
    });

    $('logoutBtn').addEventListener('click', () => {
        localStorage.clear();
        currentUser = null;
        location.reload();
    });

    // ══════════════════════════════════════════════════════════════════
    // NAVEGACIÓN
    // ══════════════════════════════════════════════════════════════════
    const ALL_VIEWS = ['dashboardView', 'datasetsView', 'filesView', 'ingestionsView', 'settingsView'];
    const navItems = document.querySelectorAll('.nav-item[data-view]');

    function switchView(viewId) {
        ALL_VIEWS.forEach(id => { const e = $(id); if (e) e.style.display = 'none'; });
        const target = $(viewId);
        if (!target) { console.warn('Vista no encontrada:', viewId); return; }
        target.style.display = 'block';

        if (viewId === 'dashboardView')   loadDashboard();
        if (viewId === 'datasetsView')    loadDatasets();
        if (viewId === 'ingestionsView')  loadIngestions();
        if (viewId === 'settingsView')    loadSettingsView();
    }

    navItems.forEach(item => {
        item.addEventListener('click', e => {
            e.preventDefault();
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            switchView(item.getAttribute('data-view'));
        });
    });

    // Header: "Nuevo Dataset" rápido y botón Actualizar
    $('globalAddBtn').addEventListener('click', () => openDatasetModal());
    $('refreshBtn').addEventListener('click', () => {
        const active = document.querySelector('.nav-item.active');
        if (active) switchView(active.getAttribute('data-view'));
    });

    // ══════════════════════════════════════════════════════════════════
    // DASHBOARD
    // ══════════════════════════════════════════════════════════════════
    function setText(id, val) {
        const el = $(id);
        if (el) el.textContent = (val !== null && val !== undefined) ? val : '--';
    }

    async function loadDashboard() {
        try {
            const s = await api('/api/dashboard/stats');
            setText('statDatasets', s.datasets);
            setText('statFiles', s.files);
            setText('statSuccess', s.success_rate);
            setText('statStorage', s.storage);
        } catch (e) { console.error('Stats error:', e.message); }

        try {
            const acts = await api('/api/dashboard/recent-activity');
            const list = $('activityList');
            if (!acts.length) {
                list.innerHTML = '<li style="color:var(--text-muted);padding:1rem 0">Sin actividad registrada aún.</li>';
                return;
            }
            list.innerHTML = acts.map(a => `
                <li class="activity-item">
                    <span class="tag ${entityTag(a.entity)}">${a.entity}</span>
                    <div class="item-details">
                        <span class="item-name">${a.action}: ${fmtDetails(a.details)}</span>
                        <span class="item-meta">${a.created_at ? new Date(a.created_at).toLocaleString('es-CL') : ''}</span>
                    </div>
                </li>`).join('');
        } catch (e) { console.error('Activity:', e.message); }
    }

    function entityTag(e) {
        return e === 'files' ? 'tag-geo' : e === 'api_ingestions' ? 'tag-api' : 'tag-pdf';
    }
    function fmtDetails(d) {
        if (!d) return '';
        if (typeof d === 'object') return d.filename || d.dataset_name || d.source || JSON.stringify(d);
        return String(d);
    }

    // ══════════════════════════════════════════════════════════════════
    // DATASETS
    // ══════════════════════════════════════════════════════════════════
    async function loadDatasets() {
        const grid = $('datasetsGrid');
        grid.innerHTML = '<p style="color:var(--text-muted)">Cargando...</p>';
        try {
            const list = await api('/api/datasets/');
            if (!list.length) {
                grid.innerHTML = `
                    <div style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--text-muted)">
                        <div style="font-size:3rem;margin-bottom:1rem">🗂️</div>
                        <p>No hay datasets creados aún.</p>
                        <button class="btn btn-primary" style="margin-top:1rem" onclick="document.getElementById('newDatasetBtn').click()">
                            + Crear el primero
                        </button>
                    </div>`;
                return;
            }
            grid.innerHTML = list.map(ds => `
                <div class="card dataset-card" onclick="openDataset('${ds.id}','${escHtml(ds.name)}')">
                    <div class="ds-icon">📁</div>
                    <h4>${escHtml(ds.name)}</h4>
                    <p style="color:var(--text-muted);font-size:0.875rem;flex:1">
                        ${escHtml(ds.description || 'Sin descripción')}
                    </p>
                    <div class="ds-footer">
                        <span class="tag tag-api">${escHtml(ds.domain || 'general')}</span>
                        <span class="ds-date">${ds.created_at ? new Date(ds.created_at).toLocaleDateString('es-CL') : ''}</span>
                    </div>
                </div>`).join('');
        } catch (e) {
            grid.innerHTML = `<p style="color:var(--danger)">Error cargando datasets: ${e.message}</p>`;
        }
    }

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Exponer globalmente para el onclick inline del card
    window.openDataset = function (id, name) {
        currentDatasetId = id;
        $('currentDatasetName').textContent = name;
        $('uploadDatasetId').value = id;
        $('uploadTargetLabel').textContent = `Dataset: ${name}`;
        navItems.forEach(i => i.classList.remove('active'));
        switchView('filesView');
        loadFiles(id);
    };

    $('backToDatasets').addEventListener('click', () => {
        document.querySelector('[data-view="datasetsView"]')?.classList.add('active');
        switchView('datasetsView');
    });

    // ══════════════════════════════════════════════════════════════════
    // MODAL: NUEVO DATASET
    // ══════════════════════════════════════════════════════════════════
    function openDatasetModal() {
        $('datasetForm').reset();
        flex('datasetModal');
    }

    $('newDatasetBtn').addEventListener('click', openDatasetModal);
    $('closeDatasetModal').addEventListener('click', () => hide('datasetModal'));

    // Cerrar al hacer click fuera del card
    $('datasetModal').addEventListener('click', e => {
        if (e.target === $('datasetModal')) hide('datasetModal');
    });

    $('datasetForm').addEventListener('submit', async e => {
        e.preventDefault();
        if (!currentUser) return;
        const btn = $('datasetSubmitBtn');
        btn.textContent = 'Creando...';
        btn.disabled = true;
        try {
            await api('/api/datasets/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: $('dsName').value.trim(),
                    description: $('dsDesc').value.trim() || null,
                    domain: $('dsDomain').value,
                    owner_id: currentUser.id,
                }),
            });
            hide('datasetModal');
            // Ir a datasets y recargar
            document.querySelector('[data-view="datasetsView"]')?.classList.add('active');
            document.querySelector('[data-view="dashboardView"]')?.classList.remove('active');
            switchView('datasetsView');
        } catch (err) {
            alert(`Error al crear dataset:\n${err.message}`);
        } finally {
            btn.textContent = '✅ Crear Dataset';
            btn.disabled = false;
        }
    });

    // ══════════════════════════════════════════════════════════════════
    // ARCHIVOS
    // ══════════════════════════════════════════════════════════════════
    async function loadFiles(datasetId) {
        const tbody = $('filesTableBody');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">Cargando archivos...</td></tr>';
        try {
            const files = await api(`/api/files/list/${datasetId}`);
            if (!files.length) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">
                    No hay archivos en este dataset. <button class="btn btn-primary" style="margin-left:1rem;" onclick="document.getElementById('openUploadBtn').click()">Subir primero</button>
                </td></tr>`;
                return;
            }
            tbody.innerHTML = files.map(f => `
                <tr>
                    <td><strong>${escHtml(f.name)}</strong></td>
                    <td><span class="tag tag-geo">${f.file_type}</span></td>
                    <td>${fmtBytes(f.size_bytes)}</td>
                    <td>${f.created_at ? new Date(f.created_at).toLocaleDateString('es-CL') : '—'}</td>
                    <td>
                        <button class="btn btn-secondary" style="padding:0.4rem 0.9rem;font-size:0.8rem;"
                            onclick="downloadFile('${f.id}')">⬇️ Descargar</button>
                    </td>
                </tr>`).join('');
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger);padding:1rem">Error: ${e.message}</td></tr>`;
        }
    }

    function fmtBytes(b) {
        if (!b) return '0 B';
        if (b >= 1073741824) return (b / 1073741824).toFixed(2) + ' GB';
        if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB';
        if (b >= 1024) return (b / 1024).toFixed(1) + ' KB';
        return b + ' B';
    }

    window.downloadFile = async function (fileId) {
        const token = localStorage.getItem('oar_token');
        try {
            const res = await fetch(`/api/files/download/${fileId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) { throw new Error(await res.text()); }
            const blob = await res.blob();
            const disp = res.headers.get('Content-Disposition') || '';
            const nameMatch = disp.match(/filename="?([^"]+)"?/);
            const filename = nameMatch ? nameMatch[1] : 'archivo';
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename;
            document.body.appendChild(a); a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (e) { alert(`Error al descargar: ${e.message}`); }
    };

    // ══════════════════════════════════════════════════════════════════
    // MODAL: SUBIR ARCHIVO
    // ══════════════════════════════════════════════════════════════════
    $('openUploadBtn').addEventListener('click', () => {
        if (!currentDatasetId) { alert('Primero selecciona un dataset.'); return; }
        $('fileInput').value = '';
        flex('uploadModal');
    });

    $('closeUploadModal').addEventListener('click', () => hide('uploadModal'));
    $('uploadModal').addEventListener('click', e => {
        if (e.target === $('uploadModal')) hide('uploadModal');
    });

    $('uploadForm').addEventListener('submit', async e => {
        e.preventDefault();
        const fileInput = $('fileInput');
        if (!fileInput.files.length) { alert('Selecciona un archivo primero.'); return; }
        if (!currentUser) { alert('Sesión expirada. Por favor inicia sesión de nuevo.'); return; }
        if (!currentDatasetId) { alert('Sin dataset seleccionado.'); return; }

        const btn = $('uploadSubmitBtn');
        btn.textContent = '⏳ Subiendo...';
        btn.disabled = true;

        try {
            const fd = new FormData();
            fd.append('file', fileInput.files[0]);
            fd.append('dataset_id', currentDatasetId);
            fd.append('user_id', currentUser.id);

            const result = await api('/api/files/upload', { method: 'POST', body: fd });
            console.log('Upload OK:', result);

            hide('uploadModal');
            fileInput.value = '';
            await loadFiles(currentDatasetId);
            loadDashboard();
        } catch (err) {
            alert(`Error al subir el archivo:\n${err.message}`);
        } finally {
            btn.textContent = '⬆️ Iniciar Carga';
            btn.disabled = false;
        }
    });

    // ══════════════════════════════════════════════════════════════════
    // INGESTAS API
    // ══════════════════════════════════════════════════════════════════

    // ── Helpers de estado ─────────────────────────────────────────────
    function ingStatusBadge(status) {
        const MAP = {
            pending: '<span class="badge badge-gray">⏳ Pendiente</span>',
            running: '<span class="badge badge-blue">🔄 Ejecutando</span>',
            success: '<span class="badge badge-green">✅ Exitosa</span>',
            failed:  '<span class="badge badge-red">❌ Fallida</span>',
        };
        return MAP[status] || `<span class="badge badge-gray">${status}</span>`;
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        return new Date(iso).toLocaleString('es-CL');
    }

    // ── Render de tabla ───────────────────────────────────────────────
    function renderIngestions(list) {
        const tbody = $('ingestionsTableBody');
        if (!list.length) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:3rem;color:var(--text-muted)">
                <div style="font-size:2.5rem;margin-bottom:0.5rem">📭</div>
                No hay ingestas configuradas aún.
            </td></tr>`;
            return;
        }
        tbody.innerHTML = list.map(ing => `
            <tr id="ing-row-${ing.id}">
                <td><strong>${escHtml(ing.source)}</strong></td>
                <td class="endpoint-cell" title="${escHtml(ing.endpoint)}">${escHtml(ing.endpoint)}</td>
                <td><span class="badge badge-method">${ing.method}</span></td>
                <td id="ing-status-${ing.id}">${ingStatusBadge(ing.status)}</td>
                <td>${fmtDate(ing.finished_at || ing.started_at)}</td>
                <td class="actions-cell">
                    <button class="btn btn-primary btn-sm" onclick="runIngestion('${ing.id}')"
                        ${ing.status === 'running' ? 'disabled' : ''}>▶ Ejecutar</button>
                    <button class="btn btn-secondary btn-sm" onclick="deleteIngestion('${ing.id}')">🗑️</button>
                </td>
            </tr>
            ${ing.status === 'failed' && ing.error_message ? `
            <tr>
                <td colspan="6" class="error-row">
                    <details><summary>Ver error</summary><pre>${escHtml(ing.error_message)}</pre></details>
                </td>
            </tr>` : ''}
        `).join('');
    }

    // ── Carga principal ───────────────────────────────────────────────
    async function loadIngestions() {
        const tbody = $('ingestionsTableBody');
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted)">Cargando...</td></tr>';
        try {
            _allIngestions = await api('/api/ingestions/');
            applyIngestionFilter();
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger);padding:1rem">Error: ${e.message}</td></tr>`;
        }
    }

    // ── Filtros ───────────────────────────────────────────────────────
    let _activeFilter = 'all';
    document.querySelectorAll('#ingestionFilterBar .filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#ingestionFilterBar .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            _activeFilter = btn.getAttribute('data-filter');
            applyIngestionFilter();
        });
    });

    function applyIngestionFilter() {
        const filtered = _activeFilter === 'all'
            ? _allIngestions
            : _allIngestions.filter(i => i.status === _activeFilter);
        renderIngestions(filtered);
    }

    // ── Ejecutar ──────────────────────────────────────────────────────
    window.runIngestion = async function (id) {
        try {
            await api(`/api/ingestions/${id}/run`, { method: 'POST' });
            // Actualizar visualmente a "running" de inmediato
            const cell = $(`ing-status-${id}`);
            if (cell) cell.innerHTML = ingStatusBadge('running');
            // Iniciar polling
            startPolling(id);
        } catch (e) {
            alert(`Error al ejecutar ingesta:\n${e.message}`);
        }
    };

    function startPolling(id) {
        if (_pollingTimers[id]) return;   // ya está corriendo
        _pollingTimers[id] = setInterval(async () => {
            try {
                const data = await api(`/api/ingestions/${id}/status`);
                const cell = $(`ing-status-${id}`);
                if (cell) cell.innerHTML = ingStatusBadge(data.status);
                if (data.status !== 'running') {
                    clearInterval(_pollingTimers[id]);
                    delete _pollingTimers[id];
                    // Recargar lista completa para refrescar fechas
                    await loadIngestions();
                }
            } catch {
                clearInterval(_pollingTimers[id]);
                delete _pollingTimers[id];
            }
        }, 2500);  // cada 2.5 segundos
    }

    // ── Eliminar ──────────────────────────────────────────────────────
    window.deleteIngestion = async function (id) {
        if (!confirm('¿Eliminar esta ingesta permanentemente?')) return;
        try {
            await api(`/api/ingestions/${id}`, { method: 'DELETE' });
            _allIngestions = _allIngestions.filter(i => i.id !== id);
            applyIngestionFilter();
        } catch (e) {
            alert(`Error al eliminar:\n${e.message}`);
        }
    };

    // ── Modal: Nueva Ingesta ──────────────────────────────────────────
    async function openIngestionModal() {
        $('ingestionForm').reset();
        // Cargar datasets en el select
        const sel = $('ingDataset');
        sel.innerHTML = '<option value="">— Sin asignar —</option>';
        try {
            const datasets = await api('/api/datasets/');
            datasets.forEach(ds => {
                const opt = document.createElement('option');
                opt.value = ds.id;
                opt.textContent = ds.name;
                sel.appendChild(opt);
            });
        } catch { /* sin datasets disponibles */ }
        flex('ingestionModal');
    }

    $('newIngestionBtn').addEventListener('click', openIngestionModal);
    $('closeIngestionModal').addEventListener('click', () => hide('ingestionModal'));
    $('ingestionModal').addEventListener('click', e => {
        if (e.target === $('ingestionModal')) hide('ingestionModal');
    });

    $('ingestionForm').addEventListener('submit', async e => {
        e.preventDefault();
        const btn = $('ingestionSubmitBtn');
        btn.textContent = 'Guardando...';
        btn.disabled = true;

        // Parsear JSON de params y headers (tolerante a error)
        const parseJSON = (text, field) => {
            if (!text.trim()) return {};
            try { return JSON.parse(text); }
            catch { alert(`El campo "${field}" no es JSON válido.`); throw new Error('bad json'); }
        };

        try {
            const params  = parseJSON($('ingParams').value, 'Parámetros');
            const headers = parseJSON($('ingHeaders').value, 'Headers');
            const dsId    = $('ingDataset').value || null;

            await api('/api/ingestions/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source:     $('ingSource').value.trim(),
                    endpoint:   $('ingEndpoint').value.trim(),
                    method:     $('ingMethod').value,
                    parameters: params,
                    headers:    headers,
                    dataset_id: dsId,
                }),
            });
            hide('ingestionModal');
            await loadIngestions();
        } catch (err) {
            if (!err.message.includes('bad json'))
                alert(`Error al guardar ingesta:\n${err.message}`);
        } finally {
            btn.textContent = '✅ Guardar Ingesta';
            btn.disabled = false;
        }
    });

    // ══════════════════════════════════════════════════════════════════
    // CONFIGURACIÓN
    // ══════════════════════════════════════════════════════════════════

    function loadSettingsView() {
        // Cargar el tab activo
        const activeTab = document.querySelector('.settings-tab.active');
        if (activeTab) switchSettingsTab(activeTab.getAttribute('data-tab'));
    }

    // ── Tabs de Configuración ─────────────────────────────────────────
    const ALL_SETTINGS_TABS = ['tabUsers', 'tabSystemInfo', 'tabAudit'];

    function switchSettingsTab(tabId) {
        ALL_SETTINGS_TABS.forEach(t => {
            const el = $(t);
            if (el) el.style.display = 'none';
        });
        document.querySelectorAll('.settings-tab').forEach(b => b.classList.remove('active'));
        const target = $(tabId);
        if (target) target.style.display = 'block';
        const activeBtn = document.querySelector(`.settings-tab[data-tab="${tabId}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        if (tabId === 'tabUsers')      loadUsers();
        if (tabId === 'tabSystemInfo') loadSystemInfo();
        if (tabId === 'tabAudit')      loadAuditLog();
    }

    document.querySelectorAll('.settings-tab').forEach(btn => {
        btn.addEventListener('click', () => switchSettingsTab(btn.getAttribute('data-tab')));
    });

    // ── Usuarios ──────────────────────────────────────────────────────
    async function loadUsers() {
        const tbody = $('usersTableBody');
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted)">Cargando...</td></tr>';
        try {
            const users = await api('/api/config/users');
            if (!users.length) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted)">No hay usuarios.</td></tr>';
                return;
            }
            tbody.innerHTML = users.map(u => `
                <tr>
                    <td><strong>${escHtml(u.username)}</strong></td>
                    <td>${escHtml(u.email || '—')}</td>
                    <td>${roleBadge(u.role)}</td>
                    <td>${u.is_active
                        ? '<span class="badge badge-green">Activo</span>'
                        : '<span class="badge badge-gray">Inactivo</span>'}</td>
                    <td>${u.created_at ? new Date(u.created_at).toLocaleDateString('es-CL') : '—'}</td>
                    <td class="actions-cell">
                        <button class="btn btn-secondary btn-sm"
                            onclick="editUser('${u.id}','${escHtml(u.username)}','${escHtml(u.email || '')}','${u.role}')">
                            ✏️ Editar
                        </button>
                        ${u.id !== currentUser?.id ? `
                        <button class="btn btn-secondary btn-sm" style="color:var(--danger)"
                            onclick="deleteUser('${u.id}')">🗑️</button>` : ''}
                    </td>
                </tr>`).join('');
        } catch (e) {
            if (e.message.includes('403')) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted)">🔒 Solo los administradores pueden ver los usuarios.</td></tr>';
            } else {
                tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger);padding:1rem">Error: ${e.message}</td></tr>`;
            }
        }
    }

    function roleBadge(role) {
        const MAP = {
            admin:  '<span class="badge badge-blue">🔑 Admin</span>',
            editor: '<span class="badge badge-green">✏️ Editor</span>',
            viewer: '<span class="badge badge-gray">👁️ Viewer</span>',
        };
        return MAP[role] || `<span class="badge badge-gray">${role}</span>`;
    }

    // Modal: Nuevo Usuario
    function openUserModal(editId = null, username = '', email = '', role = 'viewer') {
        $('userForm').reset();
        $('userEditId').value = editId || '';
        if (editId) {
            $('userModalTitle').textContent = '✏️ Editar Usuario';
            $('userUsername').value = username;
            $('userUsername').disabled = true;   // no cambiar username en edición
            $('userEmail').value = email;
            $('userRole').value = role;
            $('pwHint').textContent = '(dejar vacío para no cambiar)';
        } else {
            $('userModalTitle').textContent = '👤 Nuevo Usuario';
            $('userUsername').disabled = false;
            $('pwHint').textContent = '(requerida)';
        }
        flex('userModal');
    }

    window.editUser = function (id, username, email, role) {
        openUserModal(id, username, email, role);
    };

    window.deleteUser = async function (id) {
        if (!confirm('¿Eliminar este usuario permanentemente?\nEsta acción no se puede deshacer.')) return;
        try {
            await api(`/api/config/users/${id}`, { method: 'DELETE' });
            await loadUsers();
        } catch (e) {
            alert(`Error al eliminar usuario:\n${e.message}`);
        }
    };

    $('newUserBtn').addEventListener('click', () => openUserModal());
    $('closeUserModal').addEventListener('click', () => hide('userModal'));
    $('userModal').addEventListener('click', e => {
        if (e.target === $('userModal')) hide('userModal');
    });

    $('userForm').addEventListener('submit', async e => {
        e.preventDefault();
        const btn = $('userSubmitBtn');
        btn.textContent = 'Guardando...';
        btn.disabled = true;

        const editId   = $('userEditId').value;
        const password = $('userPassword').value;
        const isNew    = !editId;

        if (isNew && !password) {
            alert('La contraseña es obligatoria para nuevos usuarios.');
            btn.textContent = '✅ Guardar'; btn.disabled = false;
            return;
        }

        try {
            if (isNew) {
                await api('/api/config/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: $('userUsername').value.trim(),
                        email:    $('userEmail').value.trim(),
                        password: password,
                        role:     $('userRole').value,
                    }),
                });
            } else {
                const body = {
                    email:    $('userEmail').value.trim() || undefined,
                    role:     $('userRole').value,
                };
                if (password) body.password = password;
                await api(`/api/config/users/${editId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
            }
            hide('userModal');
            await loadUsers();
        } catch (err) {
            alert(`Error al guardar usuario:\n${err.message}`);
        } finally {
            btn.textContent = '✅ Guardar';
            btn.disabled = false;
        }
    });

    // ── System Info ───────────────────────────────────────────────────
    async function loadSystemInfo() {
        try {
            const info = await api('/api/config/system-info');

            // Usuarios por rol
            let totalUsers = 0;
            info.users_by_role.forEach(r => { totalUsers += Number(r.cnt); });
            setText('sysUserTotal', totalUsers);

            // Ingestas
            let success = 0, failed = 0;
            info.ingestions_by_status.forEach(r => {
                if (r.status === 'success') success += Number(r.cnt);
                if (r.status === 'failed')  failed  += Number(r.cnt);
            });
            setText('sysIngSuccess', success);
            setText('sysIngFailed', failed);
            setText('sysAuditTotal', info.audit_total);

            // Chart de roles (barras inline)
            const chart = $('roleChart');
            if (chart) {
                const maxCount = Math.max(...info.users_by_role.map(r => Number(r.cnt)), 1);
                const COLORS = { admin: '#818CF8', editor: '#34D399', viewer: '#6B7280' };
                chart.innerHTML = info.users_by_role.map(r => {
                    const pct = Math.round((Number(r.cnt) / maxCount) * 100);
                    const col = COLORS[r.role] || '#6B7280';
                    return `
                    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem;">
                        <span style="width:70px;font-size:0.85rem;color:var(--text-muted)">${r.role}</span>
                        <div style="flex:1;background:var(--bg-tertiary);border-radius:4px;height:10px;">
                            <div style="width:${pct}%;background:${col};height:100%;border-radius:4px;transition:width 0.5s;"></div>
                        </div>
                        <span style="width:30px;text-align:right;font-size:0.85rem;font-weight:600">${r.cnt}</span>
                    </div>`;
                }).join('');
            }
        } catch (e) {
            console.error('System info error:', e.message);
        }
    }

    // ── Audit Log ─────────────────────────────────────────────────────
    async function loadAuditLog() {
        const tbody = $('auditTableBody');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">Cargando...</td></tr>';
        try {
            const entries = await api('/api/config/audit-log?limit=100');
            if (!entries.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">Sin registros de auditoría.</td></tr>';
                return;
            }
            tbody.innerHTML = entries.map(e => `
                <tr>
                    <td style="white-space:nowrap;">${e.created_at ? new Date(e.created_at).toLocaleString('es-CL') : '—'}</td>
                    <td>${escHtml(e.username || '—')}</td>
                    <td><span class="badge ${auditActionBadge(e.action)}">${e.action}</span></td>
                    <td><code style="font-size:0.75rem;">${escHtml(e.entity)}</code></td>
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                        title="${escHtml(typeof e.details === 'object' ? JSON.stringify(e.details) : String(e.details || ''))}"
                    >${typeof e.details === 'object' ? JSON.stringify(e.details) : escHtml(String(e.details || ''))}</td>
                </tr>`).join('');
        } catch (err) {
            if (err.message.includes('403')) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">🔒 Solo los administradores pueden ver el audit log.</td></tr>';
            } else {
                tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger);padding:1rem">Error: ${err.message}</td></tr>`;
            }
        }
    }

    function auditActionBadge(action) {
        if (['UPLOAD', 'CREATE', 'CREATE_USER'].some(a => action.includes(a))) return 'badge-green';
        if (['DELETE', 'DELETE_USER'].some(a => action.includes(a))) return 'badge-red';
        if (['RUN_INGESTION'].some(a => action.includes(a))) return 'badge-blue';
        return 'badge-gray';
    }

    $('refreshAuditBtn')?.addEventListener('click', loadAuditLog);

    // ══════════════════════════════════════════════════════════════════
    // INICIO
    // ══════════════════════════════════════════════════════════════════
    if (!restoreSession()) {
        show('loginView');
    }
});
