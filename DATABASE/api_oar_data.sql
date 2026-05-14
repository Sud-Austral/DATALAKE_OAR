-- ============================================================
-- OAR PROJECT — INITIAL SEED DATA (UPDATED)
-- Populate tables with data from prototypes
-- ============================================================

-- 1. Insert Countries
INSERT INTO oar_countries (code, name, flag) VALUES
('GT', 'Guatemala', '🇬🇹'),
('SV', 'El Salvador', '🇸🇻'),
('HN', 'Honduras', '🇭🇳'),
('NI', 'Nicaragua', '🇳🇮'),
('CR', 'Costa Rica', '🇨🇷'),
('PA', 'Panamá', '🇵🇦'),
('BZ', 'Belice', '🇧🇿'),
('DO', 'República Dominicana', '🇩🇴'),
('Regional', 'SICA Regional', '🌍')
ON CONFLICT (code) DO NOTHING;

-- 2. Insert Categories (Ejes Estratégicos)
INSERT INTO oar_categories (id, name, linea, color, color_secondary, icon, path, description) VALUES
('calidad', 'Calidad Ambiental', '1', '#2563eb', '#eff6ff', 'Wind', '/strategic-axis/calidad', 'Monitoreo de la calidad del aire, suelo y agua, así como la gestión de residuos y contaminantes.'),
('mares', 'Mares y Biodiversidad', '2', '#0891b2', '#ecfeff', 'Waves', '/strategic-axis/mares', 'Protección de ecosistemas marinos, costeros y la biodiversidad terrestre de la región.'),
('agua', 'Gestión Hídrica', '3', '#3b82f6', '#eff6ff', 'Droplet', '/strategic-axis/agua', 'Gestión integral de los recursos hídricos y cuencas transfronterizas del SICA.'),
('bosques', 'Bosques y Paisajes', '4', '#059669', '#ecfdf5', 'Trees', '/strategic-axis/bosques', 'Conservación de la cobertura forestal, restauración de paisajes y lucha contra los incendios.'),
('clima', 'Cambio Climático', '5', '#9333ea', '#faf5ff', 'CloudRain', '/strategic-axis/clima', 'Mitigación y adaptación al cambio climático y gestión de riesgos ante desastres naturales.')
ON CONFLICT (id) DO NOTHING;

-- 3. Initial Cifras (Updated Samples)
INSERT INTO oar_cifras (title, value, unit, description, source, category_id, country_code) VALUES
('PÉRDIDA TOTAL (2010-2023)', '7,000,468', 'ha', 'Pérdida bruta total de dosel arbóreo (>30% densidad).', 'Global Forest Watch', 'bosques', 'GT'),
('COBERTURA PROTEGIDA', '24.0', '%', 'Porcentaje de territorio terrestre bajo esquemas de protección legal.', 'WDPA / Protected Planet', 'mares', 'GT'),
('INCENDIOS ACTIVOS', '6,767', 'puntos', 'Focos de calor detectados por sensores satelitales en las últimas 24h.', 'VIIRS / NASA FIRMS', 'bosques', 'GT'),
('EXTRACCIÓN DE AGUA', '14.5', 'km³/año', 'Volumen anual de agua dulce extraída para uso antropogénico.', 'Aqueduct / WRI', 'agua', 'GT'),
('SALUD OCEÁNICA', '81.0', '/100', 'Índice de Salud de los Océanos basado en biodiversidad y servicios ecosistémicos.', 'Ocean Health Index', 'mares', 'GT'),
('EMISIONES GEI', '145.8', 'MtCO2e', 'Emisiones totales de gases de efecto invernadero del sector LULUCF.', 'CAIT Climate Data', 'clima', 'GT'),
('REGISTROS BIODIVERSIDAD', '12,450,000', 'obs', 'Total de registros de presencia de especies disponibles en la red regional.', 'GBIF', 'mares', 'Regional'),
('HUELLA HUMANA', '3.7', 'index', 'Nivel promedio de presión humana sobre ecosistemas terrestres.', 'Venter et al. 2016', 'mares', 'GT'),
('CAPACIDAD INSTALADA RENOVABLE', '67.4', '%', 'Participación de fuentes renovables en la matriz energética regional.', 'SE-SICA', 'clima', 'GT'),
('ÁREAS MARINAS PROTEGIDAS', '13.2', '%', 'Superficie de la Zona Económica Exclusiva bajo figuras de protección.', 'UN Biodiversity Lab', 'mares', 'GT')
ON CONFLICT DO NOTHING;

-- 4. Insert Initial Questions
INSERT INTO oar_questions (id, category_id, question, short_question, description, highlight, path, icon, color, is_featured, view_count) VALUES
('forest-state', 'bosques', '¿Cuál es el estado de los bosques de la región?', '¿Cómo están los bosques?', 'Análisis integral del estado de los recursos forestales (Estado de los Bosques).', 'Monitoreo integral', '/preguntas/estado-bosques', 'Trees', '#15803D', TRUE, 452),
('forest-loss', 'bosques', '¿Dónde y cuánto bosque estamos perdiendo?', '¿Dónde y cuánto bosque perdemos?', 'Análisis anual de pérdida de cobertura arbórea y emisiones asociadas (GFW).', '<p class="text-sm text-slate-600">Más de <span class="font-bold text-[#97BD3D]">7 millones de hectáreas</span> de cobertura arbórea perdidas en el SICA desde 2010.</p>', '/preguntas/perdida-bosque', 'Trees', '#15803D', TRUE, 1205),
('conservation-30x30', 'mares', '¿Estamos cerca de la meta de conservación 30x30?', '¿Cómo vamos con la meta 30x30?', 'Estado actual de las áreas protegidas y OECMs reportadas.', '<p class="text-sm text-slate-600">La región protege el <span class="font-bold text-[#10B981]">20.4%</span> de su territorio. Falta un 9.6% para alcanzar el objetivo global al 2030.</p>', '/preguntas/meta-30x30', 'Shield', '#10B981', TRUE, 843),
('active-fires', 'bosques', '¿Dónde hay incendios activos en este momento?', '¿Dónde hay incendios activos ahora?', 'Monitoreo en tiempo casi real de alertas de fuego (VIIRS/MODIS).', '<p class="text-sm text-slate-600">Detectados <span class="font-bold text-[#EF4444]">7,280 focos de calor</span> en las últimas 24h, con alta incidencia en el Petén y Olancho.</p>', '/preguntas/incendios-activos', 'Flame', '#EF4444', TRUE, 3210),
('species-records', 'mares', '¿Qué nos dicen los registros de especies en vivo?', '¿Qué especies hay registradas?', 'Dashboard de biodiversidad basado en observaciones de GBIF.', 'Monitorero GBIF en vivo', '/preguntas/registros-especies', 'Footprints', '#10B981', FALSE, 156),
('drought-risk', 'clima', '¿Cuál es el riesgo de sequía en el Corredor Seco?', '¿Riesgo de sequía en Corredor Seco?', 'Indicadores climáticos y proyecciones de estrés hídrico.', '<p class="text-sm text-slate-600">Riesgo <span class="font-bold text-[#8B5CF6]">Moderado a Severo</span> debido a un déficit pluviométrico detectado en los últimos 90 días.</p>', '/preguntas/riesgo-sequia', 'CloudRain', '#8B5CF6', TRUE, 654),
('ocean-health', 'mares', '¿Cuál es el estado de salud de nuestros océanos?', '¿Nuestros océanos se calientan?', 'Índice de salud oceánica y áreas marinas protegidas.', '<p class="text-sm text-slate-600">Anomalía térmica de <span class="font-bold text-[#06B6D4]">+0.88°C</span> en aguas regionales, elevando el riesgo de blanqueamiento coralino.</p>', '/preguntas/salud-oceanos', 'Anchor', '#06B6D4', FALSE, 213),
('water-security', 'agua', '¿Cuál es el riesgo de seguridad hídrica por país?', '¿Qué tan segura es nuestra agua?', 'Disponibilidad y extracción de agua dulce (Aqueduct).', '<p class="text-sm text-slate-600">Estrés hídrico <span class="font-bold text-[#3B82F6]">Medio-Alto (2.8/5)</span> en la región, con una cobertura de agua potable del 89%.</p>', '/preguntas/seguridad-hidrica', 'Droplet', '#3B82F6', TRUE, 421),
('protected-areas', 'mares', '¿Qué áreas protegidas están reportadas oficialmente?', '¿Qué áreas están protegidas?', 'Base de datos mundial sobre áreas protegidas (Protected Planet).', 'Reporte oficial WDPA', '/preguntas/areas-protegidas', 'MapIcon', '#10B981', FALSE, 189),
('analisis-multidimensional', NULL, '¿Cómo puedo realizar cruces de variables personalizados?', 'Análisis Multidimensional (BI)', 'Explore y cruce variables de múltiples bases de datos oficiales en un entorno sandbox.', 'Sandbox Experimental', '/analisis-multidimensional', 'Database', '#1E293B', FALSE, 342)
ON CONFLICT (id) DO NOTHING;

-- 5. Insert Documents (documentation.js)
INSERT INTO oar_documents (id, name, description, source, axes, type, date, country, author, download_url, thumbnail, versions) VALUES
('DOC-001', 'Informe Regional del Estado de los Bosques 2023', 'Análisis exhaustivo de la cobertura forestal en la región SICA, incluyendo tasas de deforestación y esfuerzos de restauración.', 'CCAD / Observatorio Ambiental Regional', ARRAY['Bosques', 'Clima'], 'PDF', '2023-11-15', 'Regional', 'Comité Técnico de Bosques - CCAD', '#', 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&q=80&w=300', '[{"year": 2023, "url": "#", "label": "Versión Final"}, {"year": 2022, "url": "#", "label": "Archivo"}]'),
('DOC-002', 'Guía Metodológica para el Monitoreo de Incendios', 'Protocolos estandarizados para la detección y reporte de incendios forestales utilizando sensores remotos (VIIRS/MODIS).', 'PRIAS / SICA', ARRAY['Bosques', 'Gestión de Riesgos'], 'Manual', '2024-01-20', 'Regional', 'Unidad de Monitoreo Ambiental', '#', 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&q=80&w=300', '[{"year": 2024, "url": "#", "label": "Edición 2024"}]'),
('DOC-003', 'Base de Datos de Áreas Protegidas SICA (WDPA)', 'Compendio tabular de los límites, categorías de manejo y gobernanza de las áreas protegidas terrestres y marinas.', 'UNEP-WCMC', ARRAY['Biodiversidad', 'Mares'], 'Excel', '2023-12-05', 'Regional', 'Base de Datos Mundial sobre Áreas Protegidas', '#', 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&q=80&w=300', '[{"year": 2023, "url": "#", "label": "Dataset v3.0"}]'),
('DOC-004', 'Estrategia Regional de Cambio Climático 2021-2030', 'Documento marco para la mitigación y adaptación al cambio climático en los estados miembros del SICA.', 'Consejo de Ministros de CCAD', ARRAY['Clima', 'Gobernanza'], 'Estrategia', '2021-06-12', 'Regional', 'Secretaría Ejecutiva CCAD', '#', 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&q=80&w=300', '[{"year": 2021, "url": "#", "label": "Documento Base"}]'),
('DOC-005', 'Análisis de Vulnerabilidad Hídrica en el Corredor Seco', 'Estudio sobre la disponibilidad de agua y riesgos de sequía en las zonas críticas del corredor seco centroamericano.', 'FAO / CCAD', ARRAY['Agua', 'Clima'], 'Reporte', '2024-02-14', 'Guatemala', 'Programa de Resiliencia Climática', '#', 'https://images.unsplash.com/photo-1470075801209-17f9ec0cada6?auto=format&fit=crop&q=80&w=300', '[{"year": 2024, "url": "#", "label": "Fase 1"}]'),
('DOC-006', 'Plan Maestro de Manejo de la Reserva de la Biosfera Maya', 'Instrumento de gestión integral para la conservación de la mayor selva tropical de Mesoamérica.', 'CONAP', ARRAY['Bosques', 'Gobernanza'], 'Plan', '2022-08-10', 'Guatemala', 'Consejo Nacional de Áreas Protegidas', '#', 'https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?auto=format&fit=crop&q=80&w=300', '[{"year": 2022, "url": "#", "label": "Vigente"}]')
ON CONFLICT (id) DO NOTHING;

-- 6. Insert View Guides (viewGuides.json - partial)
INSERT INTO oar_view_guides (path, title, description, features, source, learn_more, image) VALUES
('/', 'Portal Principal OAR', 'Bienvenido al Observatorio Ambiental Regional. Esta vista central conecta todas las herramientas estratégicas del SICA.', ARRAY['Acceso a Preguntas Estratégicas', 'Visualización de Cifras Regionales', 'Monitoreo de compromisos', 'Laboratorio de Análisis'], 'Sistemas integrados de CCAD, NASA, GFW', '/technical/docs', 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800'),
('/preguntas', 'Preguntas Estratégicas', 'Respuestas directas a las interrogantes más críticas sobre el estado del ambiente regional.', ARRAY['Exploración por temas', 'Visualizaciones interactivas', 'Acceso a datos crudos', 'Narrativas simplificadas'], 'Base de datos unificada del OAR', '/strategic-questions', 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800'),
('/technical/geo-analysis', 'Laboratorio Geoespacial', 'Herramientas avanzadas de análisis espacial para la toma de decisiones.', ARRAY['Detección histórica de deforestación', 'Análisis de restricciones', 'Inventario dinámico', 'Cruce de proyectos'], 'Motores de procesamiento OAR, Sentinel-2', '/technical/map', 'https://images.unsplash.com/photo-1526772662000-3f88f10405ff?auto=format&fit=crop&q=80&w=800')
ON CONFLICT (path) DO NOTHING;
