-- ============================================================
-- DATALAKE OAR — Database Bootstrap
-- Ejecutado automáticamente en el primer arranque del contenedor
-- ============================================================

\i /docker-entrypoint-initdb.d/db.sql

-- Admin user por defecto (password: 'admin123' — cambiar en producción)
INSERT INTO users (username, email, password, role)
VALUES (
    'admin',
    'admin@oar.railways',
    crypt('admin123', gen_salt('bf', 12)),
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Tags base del dominio OAR Ambiental
INSERT INTO tags (name, color) VALUES
    ('Calidad Ambiental',     '#10B981'),
    ('Mares y Biodiversidad', '#3B82F6'),
    ('Recurso Hídrico',      '#0EA5E9'),
    ('Bosques y Paisajes',   '#22C55E'),
    ('Cambio Climático',     '#EF4444')
ON CONFLICT (name) DO NOTHING;

-- Dataset de ejemplo
INSERT INTO datasets (name, description, domain, status)
VALUES (
    'Monitoreo Ambiental OAR',
    'Datos de base para monitoreo ambiental y biodiversidad',
    'calidad-ambiental',
    'active'
) ON CONFLICT DO NOTHING;
