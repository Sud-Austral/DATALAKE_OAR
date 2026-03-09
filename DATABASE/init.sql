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

-- Tags base del dominio ferroviario
INSERT INTO tags (name, color) VALUES
    ('railway',        '#3B82F6'),
    ('infrastructure', '#8B5CF6'),
    ('geospatial',     '#10B981'),
    ('environment',    '#22C55E'),
    ('traffic',        '#F59E0B'),
    ('safety',         '#EF4444'),
    ('maintenance',    '#F97316')
ON CONFLICT (name) DO NOTHING;

-- Dataset de ejemplo
INSERT INTO datasets (name, description, domain, status)
VALUES (
    'OAR Base Infrastructure',
    'Datos base de infraestructura ferroviaria OAR',
    'railway',
    'active'
) ON CONFLICT DO NOTHING;
