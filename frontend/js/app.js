document.addEventListener('DOMContentLoaded', () => {
    console.log('OAR Datalake Frontend Initialized');

    // UI Elements
    const loginView = document.getElementById('loginView');
    const appContainer = document.getElementById('appContainer');
    const sections = document.querySelectorAll('.content-view');
    const navItems = document.querySelectorAll('.nav-item');

    // Auth & User State
    let currentUser = JSON.parse(localStorage.getItem('oar_user'));

    if (localStorage.getItem('oar_token')) {
        showApp(currentUser);
    }

    // --- NAVIGATION ---
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });

    function switchView(viewId) {
        sections.forEach(s => s.style.display = 'none');
        document.getElementById(viewId).style.display = 'block';
        if (viewId === 'dashboardView') updateDashboard();
        if (viewId === 'datasetsView') loadDatasets();
    }

    function showApp(user) {
        loginView.style.display = 'none';
        appContainer.style.display = 'grid';
        document.getElementById('displayUser').textContent = user.username;
        document.getElementById('displayRole').textContent = user.role.toUpperCase();
        document.getElementById('avatarLetter').textContent = user.username[0].toUpperCase();
        switchView('dashboardView');
    }

    // --- DASHBOARD LOGIC ---
    async function updateDashboard() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            document.querySelector('[data-stat="datasets"]').textContent = data.datasets;
            document.querySelector('[data-stat="files"]').textContent = data.files;
            document.querySelector('[data-stat="success"]').textContent = data.success_rate;
            document.querySelector('[data-stat="storage"]').textContent = data.storage;

            const actRes = await fetch('/api/dashboard/recent-activity');
            const acts = await actRes.json();
            const list = document.getElementById('activityList');
            list.innerHTML = acts.map(a => `
                <li class="activity-item">
                    <span class="tag ${getTagClass(a.entity)}">${a.entity}</span>
                    <div class="item-details">
                        <span class="item-name">${a.action}: ${a.details || ''}</span>
                        <span class="item-meta">${new Date(a.created_at).toLocaleString()}</span>
                    </div>
                </li>
            `).join('');
        } catch (e) { console.error(e); }
    }

    function getTagClass(entity) {
        if (entity === 'files') return 'tag-geo';
        if (entity === 'api_ingestions') return 'tag-api';
        return 'tag-pdf';
    }

    // --- DATASETS LOGIC ---
    async function loadDatasets() {
        try {
            const res = await fetch('/api/datasets/');
            const datasets = await res.json();
            const grid = document.getElementById('datasetsGrid');
            grid.innerHTML = datasets.map(ds => `
                <div class="card dataset-card" onclick="openDataset('${ds.id}', '${ds.name}')">
                    <div class="ds-icon">📁</div>
                    <h4>${ds.name}</h4>
                    <p>${ds.description || 'Sin descripción'}</p>
                    <div class="ds-footer">
                        <span class="tag tag-api">${ds.domain}</span>
                        <span class="ds-date">${new Date(ds.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');
        } catch (e) { console.error(e); }
    }

    window.openDataset = async (id, name) => {
        document.getElementById('currentDatasetName').textContent = name;
        document.getElementById('uploadDatasetId').value = id;
        switchView('filesView');
        loadFiles(id);
    };

    async function loadFiles(datasetId) {
        try {
            const res = await fetch(`/api/files/list/${datasetId}`);
            const files = await res.json();
            const tbody = document.getElementById('filesTableBody');
            tbody.innerHTML = files.map(f => `
                <tr>
                    <td><strong>${f.name}</strong></td>
                    <td><span class="tag tag-geo">${f.file_type}</span></td>
                    <td>${(f.size_bytes / 1024).toFixed(1)} KB</td>
                    <td>${new Date(f.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="downloadFile('${f.id}')">⬇️</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    }

    window.downloadFile = async (id) => {
        const res = await fetch(`/api/files/download/${id}`);
        const data = await res.json();
        window.open(data.url, '_blank');
    };

    // --- MODALS & FORMS ---
    const uploadModal = document.getElementById('uploadModal');
    const datasetModal = document.getElementById('datasetModal');

    document.getElementById('newDatasetBtn').addEventListener('click', () => datasetModal.style.display = 'flex');
    document.getElementById('openUploadBtn').addEventListener('click', () => uploadModal.style.display = 'flex');
    document.getElementById('closeDatasetModal').addEventListener('click', () => datasetModal.style.display = 'none');
    document.getElementById('closeUploadModal').addEventListener('click', () => uploadModal.style.display = 'none');

    document.getElementById('datasetForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = {
            name: document.getElementById('dsName').value,
            description: document.getElementById('dsDesc').value,
            domain: document.getElementById('dsDomain').value,
            owner_id: currentUser.id
        };
        const res = await fetch('/api/datasets/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            datasetModal.style.display = 'none';
            loadDatasets();
        }
    });

    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('file', document.getElementById('fileInput').files[0]);
        formData.append('dataset_id', document.getElementById('uploadDatasetId').value);
        formData.append('user_id', currentUser.id);

        const res = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });
        if (res.ok) {
            uploadModal.style.display = 'none';
            loadFiles(document.getElementById('uploadDatasetId').value);
        }
    });

    document.getElementById('backToDatasets').addEventListener('click', () => switchView('datasetsView'));

    // --- LOGIN FORM ---
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('oar_token', data.token);
            localStorage.setItem('oar_user', JSON.stringify(data.user));
            currentUser = data.user;
            showApp(data.user);
        } else {
            document.getElementById('loginError').style.display = 'block';
        }
    });
});
