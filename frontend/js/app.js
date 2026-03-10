document.addEventListener('DOMContentLoaded', () => {

    // ── Estado global ─────────────────────────────────────────────────
    let currentUser = null;
    let currentDatasetId = null;

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

        if (viewId === 'dashboardView') loadDashboard();
        if (viewId === 'datasetsView') loadDatasets();
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
        if (typeof d === 'object') return d.filename || d.dataset_name || JSON.stringify(d);
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
    // INICIO
    // ══════════════════════════════════════════════════════════════════
    if (!restoreSession()) {
        show('loginView');
    }
});
