document.addEventListener('DOMContentLoaded', () => {
    console.log('OAR Datalake Frontend Initialized');

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
