document.addEventListener('DOMContentLoaded', () => {
    console.log('OAR Datalake Frontend Initialized');

    // Gestión de Login
    const loginView = document.getElementById('loginView');
    const appContainer = document.getElementById('appContainer');
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const logoutBtn = document.getElementById('logoutBtn');

    // Revisar si ya estamos logueados
    if (localStorage.getItem('oar_token')) {
        showApp(JSON.parse(localStorage.getItem('oar_user')));
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btn = loginForm.querySelector('.login-btn');
        const prevText = btn.textContent;
        btn.textContent = 'Verificando...';
        btn.disabled = true;
        loginError.style.display = 'none';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('oar_token', data.token);
                localStorage.setItem('oar_user', JSON.stringify(data.user));
                showApp(data.user);
            } else {
                loginError.style.display = 'block';
            }
        } catch (error) {
            console.error("Login err:", error);
            loginError.textContent = "Error de conexión";
            loginError.style.display = 'block';
        } finally {
            btn.textContent = prevText;
            btn.disabled = false;
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('oar_token');
        localStorage.removeItem('oar_user');
        loginView.style.display = 'flex';
        appContainer.style.display = 'none';
        document.getElementById('password').value = '';
    });

    function showApp(user) {
        loginView.style.display = 'none';
        appContainer.style.display = 'grid';
        document.getElementById('displayUser').textContent = user.username;
        document.getElementById('displayRole').textContent = user.role.toUpperCase();

        // Cargar datos
        updateDashboard();
        loadActivity();
    }

    const updateDashboard = async () => {
        try {
            const res = await fetch('/api/dashboard/stats');
            const stats = await res.json();

            // Actualizar contadores
            document.querySelector('[data-stat="datasets"]').textContent = stats.datasets;
            document.querySelector('[data-stat="files"]').textContent = stats.files;
            document.querySelector('[data-stat="success"]').textContent = stats.success_rate;
            document.querySelector('[data-stat="storage"]').textContent = stats.storage;
        } catch (e) {
            console.error("Error al cargar estadísticas", e);
        }
    };

    const loadActivity = async () => {
        try {
            const res = await fetch('/api/dashboard/recent-activity');
            const activities = await res.json();
            const list = document.getElementById('activityList');
            list.innerHTML = activities.map(act => `
                <li class="activity-item">
                    <span class="tag tag-api">${act.entity}</span>
                    <div class="item-details">
                        <span class="item-name">${act.action} en ${act.entity}</span>
                        <span class="item-meta">${new Date(act.created_at).toLocaleString()}</span>
                    </div>
                </li>
            `).join('');
        } catch (e) {
            console.error("Error al cargar actividad", e);
        }
    };

    updateDashboard();
    loadActivity();

    // Navegación Básica
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const view = item.getAttribute('data-view');
            console.log(`Cambiando a vista: ${view}`);
            // Aquí iría la lógica para cargar datos dinámicos
        });
    });

    // Simulación de interacción con la API
    async function checkHealth() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            console.log('Service Health:', data);
        } catch (error) {
            console.warn('Backend no disponible aún para healthcheck');
        }
    }

    checkHealth();

    // Evento Subir Archivo
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.addEventListener('click', () => {
        alert('Funcionalidad de subida en desarrollo. El backend está listo para recibir archivos en /upload');
    });
});
