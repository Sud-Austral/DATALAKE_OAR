/**
 * OAR — ADMINISTRATIVE FRONTEND LOGIC
 * Management for Strategic Questions, ERAM Axes, and KPIs.
 */

const API_BASE = '/api/oar';
let allQuestions = [];
let allCategories = [];

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    await fetchCategories();
    await fetchQuestions();
    await fetchDocuments();
    await fetchCifras();
    
    setupEventListeners();
}

async function fetchCategories() {
    try {
        const res = await fetch(`${API_BASE}/categories`);
        allCategories = await res.json();
        
        // Populate Selects
        const qCategory = document.getElementById('qCategory');
        qCategory.innerHTML = '<option value="">— Sin Categoría —</option>';
        allCategories.forEach(cat => {
            qCategory.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
        });

        renderCategoriesTab();
    } catch (err) { console.error('Error fetching categories:', err); }
}

async function fetchQuestions() {
    try {
        const res = await fetch(`${API_BASE}/questions`);
        allQuestions = await res.json();
        document.getElementById('qCount').textContent = allQuestions.length;
        renderQuestionsGrid(allQuestions);
    } catch (err) { console.error('Error fetching questions:', err); }
}

async function fetchDocuments() {
    try {
        const res = await fetch(`${API_BASE}/documents`);
        const docs = await res.json();
        document.getElementById('docCount').textContent = docs.length;
        renderDocumentsTable(docs);
    } catch (err) { console.error('Error fetching documents:', err); }
}

async function fetchCifras() {
    try {
        const res = await fetch(`${API_BASE}/cifras`);
        const cifras = await res.json();
        renderCifrasTab(cifras);
    } catch (err) { console.error('Error fetching cifras:', err); }
}

function renderQuestionsGrid(questions) {
    const grid = document.getElementById('questionsGrid');
    grid.innerHTML = '';
    
    if (questions.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align:center; padding: 2rem; color: #64748b;">No hay preguntas registradas.</p>';
        return;
    }

    questions.forEach(q => {
        const card = document.createElement('div');
        card.className = 'q-card';
        card.style.borderLeft = `4px solid ${q.color || '#15803D'}`;
        
        // Find Category
        const cat = allCategories.find(c => c.id === q.category_id);
        const catName = cat ? cat.name : 'Sin Categoría';
        const catColor = cat ? cat.color : '#cbd5e1';

        card.innerHTML = `
            <span class="q-badge" style="background: ${catColor}15; color: ${catColor}">${catName}</span>
            <div style="padding-top: 1rem;">
                <h3 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem;">${q.question}</h3>
                <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1rem; line-height: 1.4;">${q.description || ''}</p>
            </div>
            
            <div style="margin-top: auto; border-top: 1px solid #f1f5f9; padding-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; gap: 1rem;">
                    <span class="q-stat" title="Vistas únicas">👁️ ${q.view_count || 0}</span>
                    ${q.is_featured ? '<span class="q-stat featured-star" title="En Portada">⭐ Portada</span>' : ''}
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-secondary btn-sm" onclick="editQuestion('${q.id}')">✏️ Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteQuestion('${q.id}')" style="background: #fee2e2; color: #ef4444; border: none;">🗑️</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderDocumentsTable(docs) {
    const tbody = document.getElementById('docsTableBody');
    tbody.innerHTML = '';
    docs.forEach(doc => {
        tbody.innerHTML += `
            <tr>
                <td><small>${doc.id}</small></td>
                <td><b>${doc.name}</b></td>
                <td><span class="badge" style="background:#e2e8f0; color:#475569;">${doc.type || 'Doc'}</span></td>
                <td>${doc.country || 'Regional'}</td>
                <td>${doc.date ? new Date(doc.date).toLocaleDateString() : '-'}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="editDocument('${doc.id}')">✏️</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteDocument('${doc.id}')">🗑️</button>
                </td>
            </tr>
        `;
    });
}

function renderCategoriesTab() {
    const tbody = document.getElementById('categoriesTableBody');
    tbody.innerHTML = '';
    allCategories.forEach(cat => {
        tbody.innerHTML += `
            <tr>
                <td><b>${cat.linea}</b></td>
                <td>${cat.icon}</td>
                <td><span style="font-weight: 600;">${cat.name}</span></td>
                <td><div style="display: flex; align-items: center; gap: 0.5rem;"><div style="width: 12px; h-height: 12px; background: ${cat.color}; border-radius: 2px; height: 12px;"></div> ${cat.color}</div></td>
                <td><small>${cat.description || ''}</small></td>
            </tr>
        `;
    });
}

function renderCifrasTab(cifras) {
    const tbody = document.getElementById('cifrasTableBody');
    tbody.innerHTML = '';
    cifras.forEach(c => {
        tbody.innerHTML += `
            <tr>
                <td><b>${c.title}</b></td>
                <td style="color: #15803D; font-weight: 600;">${c.value} ${c.unit || ''}</td>
                <td>${c.category_id || '-'}</td>
                <td>${c.country_code || 'Regional'}</td>
                <td><small>${c.source || ''}</small></td>
                <td>
                    <button class="btn btn-secondary btn-sm">✏️</button>
                </td>
            </tr>
        `;
    });
}

// EVENTS
function setupEventListeners() {
    // Tabs Navigation
    document.querySelectorAll('.nav-oar-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.getAttribute('data-tab');
            
            // UI Update
            document.querySelectorAll('.nav-oar-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            // Visibility
            document.querySelectorAll('.tab-content').forEach(s => s.style.display = 'none');
            document.getElementById(`${tabId}Sec`).style.display = 'block';
        });
    });

    // Modals
    document.getElementById('addQuestionBtn').onclick = () => {
        openModal('add');
    };
    document.getElementById('addDocBtn').onclick = () => {
        openDocModal('add');
    };

    document.getElementById('closeQModal').onclick = closeModal;
    document.getElementById('closeDocModal').onclick = closeDocModal;
    
    document.getElementById('qForm').onsubmit = async (e) => {
        e.preventDefault();
        saveQuestion();
    };
    document.getElementById('docForm').onsubmit = async (e) => {
        e.preventDefault();
        saveDocument();
    };
}

// MODAL LOGIC (QUESTIONS)
function openModal(mode, qId = null) {
    const modalId = document.getElementById('qId');
    const modalTitle = document.getElementById('qModalTitle');
    
    if (mode === 'add') {
        document.getElementById('qForm').reset();
        modalId.readOnly = false;
        modalTitle.textContent = '🚀 Nueva Pregunta Estratégica';
    } else {
        const q = allQuestions.find(i => i.id === qId);
        if (!q) return;
        
        modalTitle.textContent = '✏️ Editando Pregunta';
        modalId.value = q.id;
        modalId.readOnly = true;
        
        document.getElementById('qCategory').value = q.category_id || '';
        document.getElementById('qText').value = q.question;
        document.getElementById('qShort').value = q.short_question || '';
        document.getElementById('qPath').value = q.path;
        document.getElementById('qDesc').value = q.description || '';
        document.getElementById('qHighlight').value = q.highlight || '';
        document.getElementById('qIcon').value = q.icon || 'Info';
        document.getElementById('qColor').value = q.color || '#15803D';
        document.getElementById('qFeatured').checked = q.is_featured;
        document.getElementById('qActive').checked = q.is_active;
    }
    document.getElementById('qModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('qModal').style.display = 'none';
}

// MODAL LOGIC (DOCUMENTS)
function openDocModal(mode, docId = null) {
    const modalId = document.getElementById('docId');
    const modalTitle = document.getElementById('docModalTitle');
    
    if (mode === 'add') {
        document.getElementById('docForm').reset();
        modalId.readOnly = false;
        modalTitle.textContent = '📄 Nuevo Documento Técnico';
    } else {
        fetch(`${API_BASE}/documents`).then(r => r.json()).then(docs => {
            const doc = docs.find(d => d.id === docId);
            if (!doc) return;
            
            modalTitle.textContent = '✏️ Editando Documento';
            modalId.value = doc.id;
            modalId.readOnly = true;
            
            document.getElementById('docName').value = doc.name;
            document.getElementById('docDesc').value = doc.description || '';
            document.getElementById('docSource').value = doc.source || '';
            document.getElementById('docAuthor').value = doc.author || '';
            document.getElementById('docType').value = doc.type || '';
            document.getElementById('docDate').value = doc.date || '';
            document.getElementById('docCountry').value = doc.country || '';
            document.getElementById('docUrl').value = doc.download_url || '#';
            document.getElementById('docThumbnail').value = doc.thumbnail || '';
            document.getElementById('docAxes').value = (doc.axes || []).join(', ');
        });
    }
    document.getElementById('docModal').style.display = 'flex';
}

function closeDocModal() {
    document.getElementById('docModal').style.display = 'none';
}

async function saveQuestion() {
    // Extract data
    const data = {
        id: document.getElementById('qId').value,
        category_id: document.getElementById('qCategory').value || null,
        question: document.getElementById('qText').value,
        short_question: document.getElementById('qShort').value || null,
        path: document.getElementById('qPath').value,
        description: document.getElementById('qDesc').value || null,
        highlight: document.getElementById('qHighlight').value || null,
        icon: document.getElementById('qIcon').value || 'Info',
        color: document.getElementById('qColor').value,
        is_featured: document.getElementById('qFeatured').checked,
        is_active: document.getElementById('qActive').checked
    };

    try {
        const res = await fetch(`${API_BASE}/maintainer/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            closeModal();
            fetchQuestions(); // Refresh
        } else {
            alert('Error al guardar la pregunta.');
        }
    } catch (err) { console.error('Error saving question:', err); }
}

async function saveDocument() {
    const data = {
        id: document.getElementById('docId').value,
        name: document.getElementById('docName').value,
        description: document.getElementById('docDesc').value || null,
        source: document.getElementById('docSource').value || null,
        author: document.getElementById('docAuthor').value || null,
        type: document.getElementById('docType').value || null,
        date: document.getElementById('docDate').value || null,
        country: document.getElementById('docCountry').value || null,
        download_url: document.getElementById('docUrl').value || '#',
        thumbnail: document.getElementById('docThumbnail').value || null,
        axes: document.getElementById('docAxes').value.split(',').map(s => s.trim()).filter(s => s !== ''),
        versions: [] // Managed as JSONB in DB
    };

    try {
        const res = await fetch(`${API_BASE}/maintainer/documents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            closeDocModal();
            fetchDocuments(); // Refresh
        } else {
            alert('Error al guardar el documento.');
        }
    } catch (err) { console.error('Error saving document:', err); }
}

function editQuestion(id) {
    openModal('edit', id);
}

function editDocument(id) {
    openDocModal('edit', id);
}

async function deleteQuestion(id) {
    if (!confirm('¿Seguro que quieres eliminar esta pregunta?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/maintainer/questions/${id}`, { method: 'DELETE' });
        if (res.ok) fetchQuestions();
    } catch (err) { console.error('Error deleting question:', err); }
}

async function deleteDocument(id) {
    if (!confirm('¿Seguro que quieres eliminar este documento?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/maintainer/documents/${id}`, { method: 'DELETE' });
        if (res.ok) fetchDocuments();
    } catch (err) { console.error('Error deleting document:', err); }
}
