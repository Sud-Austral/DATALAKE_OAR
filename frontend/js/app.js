document.addEventListener('DOMContentLoaded', () => {

    // ─── Referencias UI ──────────────────────────────────────────────
    const loginView = document.getElementById('loginView');
    const appContainer = document.getElementById('appContainer');
    const navItems = document.querySelectorAll('.nav-item[data-view]');

    let currentUser = null;
    let currentDatasetId = null;

    // ─── Helpers ─────────────────────────────────────────────────────
    function showEl(id) { const el = document.getElementById(id); if (el) el.style.display = 'block'; }
    function hideEl(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }
    function flexEl(id) { const el = document.getElementById(id); if (el) el.style.display = 'flex'; }

    async function apiFetch(url, options = {}) {
        const res = await fetch(url, options);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`${res.status}: ${text}`);
        }
        return res.json();
    }

    // ─── Autenticación ────────────────────────────────────────────────
    const stored = localStorage.getItem('oar_user');
    if (stored && localStorage.getItem('oar_token')) {
        try {
            currentUser = JSON.parse(stored);
            showApp(currentUser);
        } catch { localStorage.clear(); }
    }

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        hideEl('loginError');
        try {
            const data = await apiFetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('username').value.trim(),
                    password: document.getElementById('password').value,
                }),
            });
            localStorage.setItem('oar_token', data.token);
            localStorage.setItem('oar_user', JSON.stringify(data.user));
            currentUser = data.user;
            showApp(data.user);
        } catch (err) {
            console.error('Login error:', err);
            showEl('loginError');
        }
    });

    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.clear();
        location.reload();
    });

    function showApp(user) {
        hideEl('loginView');
        document.getElementById('appContainer').style.display = 'grid';
        document.getElementById('displayUser').textContent = user.username;
        document.getElementById('displayRole').textContent = user.role.toUpperCase();
        document.getElementById('avatarLetter').textContent = user.username[0].toUpperCase();
        switchView('dashboardView');
    }

    // ─── Navegación ──────────────────────────────────────────────────
    const ALL_VIEWS = ['dashboardView', 'datasetsView', 'filesView', 'ingestionsView', 'settingsView'];

    function switchView(viewId) {
        ALL_VIEWS.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        const target = document.getElementById(viewId);
        if (!target) { console.warn(`Vista no encontrada: ${viewId}`); return; }
        target.style.display = 'block';

        if (viewId === 'dashboardView') updateDashboard();
        if (viewId === 'datasetsView') loadDatasets();
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            switchView(item.getAttribute('data-view'));
        });
    });

    // ─── Dashboard ───────────────────────────────────────────────────
    async function updateDashboard() {
        try {
            const stats = await apiFetch('/api/dashboard/stats');
            document.querySelector('[data-stat="datasets"]').textContent = stats.datasets;
            document.querySelector('[data-stat="files"]').textContent = stats.files;
            document.querySelector('[data-stat="success"]').textContent = stats.success_rate;
            document.querySelector('[data-stat="storage"]').textContent = stats.storage;
        } catch (e) { console.error('Stats error:', e); }

        try {
            const acts = await apiFetch('/api/dashboard/recent-activity');
            const list = document.getElementById('activityList');
            if (!acts.length) {
                list.innerHTML = '<li style="color:var(--text-muted);padding:1rem">Sin actividad registrada.</li>';
                return;
            }
            list.innerHTML = acts.map(a => `
                <li class="activity-item">
                    <span class="tag ${tagClass(a.entity)}">${a.entity}</span>
                    <div class="item-details">
                        <span class="item-name">${a.action}: ${formatDetails(a.details)}</span>
                        <span class="item-meta">${new Date(a.created_at).toLocaleString('es-CL')}</span>
                    </div>
                </li>
            `).join('');
        } catch (e) { console.error('Activity error:', e); }
    }

    function tagClass(entity) {
        return entity === 'files' ? 'tag-geo' : entity === 'api_ingestions' ? 'tag-api' : 'tag-pdf';
    }
    function formatDetails(d) {
        if (!d) return '';
        if (typeof d === 'object') return d.filename || d.dataset_name || JSON.stringify(d);
        return d;
    }

    // ─── Datasets ────────────────────────────────────────────────────
    async function loadDatasets() {
        const grid = document.getElementById('datasetsGrid');
        grid.innerHTML = '<p style="color:var(--text-muted)">Cargando...</p>';
        try {
            const datasets = await apiFetch('/api/datasets/');
            if (!datasets.length) {
                grid.innerHTML = '<p style="color:var(--text-muted)">No hay datasets creados aún.</p>';
                return;
            }
            grid.innerHTML = datasets.map(ds => `
                <div class="card dataset-card" data-id="${ds.id}" data-name="${ds.name}">
                    <div class="ds-icon">📁</div>
                    <h4>${ds.name}</h4>
                    <p>${ds.description || 'Sin descripción'}</p>
                    <div class="ds-footer">
                        <span class="tag tag-api">${ds.domain || 'general'}</span>
                        <span class="ds-date">${ds.created_at ? new Date(ds.created_at).toLocaleDateString('es-CL') : ''}</span>
                    </div>
                    <button class="btn btn-primary" style="margin-top:1rem;" onclick="openDataset('${ds.id}','${ds.name.replace(/'/g, "\\'")}')">Ver Archivos →</button>
                </div>
            `).join('');
        } catch (e) {
            console.error('Datasets error:', e);
            grid.innerHTML = `<p style="color:red">Error al cargar datasets: ${e.message}</p>`;
        }
    }

    window.openDataset = function (id, name) {
        currentDatasetId = id;
        document.getElementById('currentDatasetName').textContent = name;
        document.getElementById('uploadDatasetId').value = id;
        // Desactivar nav y mostrar vista de archivos
        navItems.forEach(i => i.classList.remove('active'));
        switchView('filesView');
        loadFiles(id);
    };

    document.getElementById('backToDatasets').addEventListener('click', () => {
        document.querySelector('[data-view="datasetsView"]')?.classList.add('active');
        switchView('datasetsView');
    });

    // ─── Archivos ────────────────────────────────────────────────────
    async function loadFiles(datasetId) {
        const tbody = document.getElementById('filesTableBody');
        tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-muted);text-align:center">Cargando archivos...</td></tr>';
        try {
            const files = await apiFetch(`/api/files/list/${datasetId}`);
            if (!files.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-muted);text-align:center">No hay archivos en este dataset.</td></tr>';
                return;
            }
            tbody.innerHTML = files.map(f => `
                <tr>
                    <td><strong>${f.name}</strong></td>
                    <td><span class="tag tag-geo">${f.file_type}</span></td>
                    <td>${formatBytes(f.size_bytes)}</td>
                    <td>${f.created_at ? new Date(f.created_at).toLocaleDateString('es-CL') : '—'}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="downloadFile('${f.id}')">⬇ Descargar</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error('Files error:', e);
            tbody.innerHTML = `<tr><td colspan="5" style="color:red">Error: ${e.message}</td></tr>`;
        }
    }

    function formatBytes(bytes) {
        if (!bytes) return '0 B';
        if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 ** 3)).toFixed(2) + ' GB';
        if (bytes >= 1024 * 1024) return (bytes / (1024 ** 2)).toFixed(1) + ' MB';
        if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return bytes + ' B';
    }

    window.downloadFile = async function (fileId) {
        try {
            const data = await apiFetch(`/api/files/download/${fileId}`);
            window.open(data.url, '_blank');
        } catch (e) {
            alert(`Error al generar enlace de descarga: ${e.message}`);
        }
    };

    // ─── Modal: Subir Archivo ─────────────────────────────────────────
    const uploadModal = document.getElementById('uploadModal');
    document.getElementById('openUploadBtn').addEventListener('click', () => flexEl('uploadModal'));
    document.getElementById('closeUploadModal').addEventListener('click', () => hideEl('uploadModal'));

    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('fileInput');
        if (!fileInput.files.length) { alert('Selecciona un archivo.'); return; }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('dataset_id', document.getElementById('uploadDatasetId').value);
        formData.append('user_id', currentUser.id);

        const btn = e.target.querySelector('[type="submit"]');
        btn.textContent = 'Subiendo…';
        btn.disabled = true;

        try {
            await apiFetch('/api/files/upload', { method: 'POST', body: formData });
            hideEl('uploadModal');
            fileInput.value = '';
            loadFiles(currentDatasetId);
            updateDashboard();
        } catch (err) {
            alert(`Error al subir: ${err.message}`);
        } finally {
            btn.textContent = 'Iniciar Carga';
            btn.disabled = false;
        }
    });

    // ─── Modal: Nuevo Dataset ─────────────────────────────────────────
    document.getElementById('newDatasetBtn').addEventListener('click', () => flexEl('datasetModal'));
    document.getElementById('closeDatasetModal').addEventListener('click', () => hideEl('datasetModal'));

    document.getElementById('datasetForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('[type="submit"]');
        btn.textContent = 'Creando…';
        btn.disabled = true;

        try {
            await apiFetch('/api/datasets/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: document.getElementById('dsName').value.trim(),
                    description: document.getElementById('dsDesc').value.trim(),
                    domain: document.getElementById('dsDomain').value,
                    owner_id: currentUser.id,
                }),
            });
            hideEl('datasetModal');
            e.target.reset();
            loadDatasets();
        } catch (err) {
            alert(`Error al crear dataset: ${err.message}`);
        } finally {
            btn.textContent = 'Crear';
            btn.disabled = false;
        }
    });
});
