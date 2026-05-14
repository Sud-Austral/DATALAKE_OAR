-- ============================================================
-- OAR PROJECT — SQL SCHEMA
-- Tables for Strategic Questions, Monitoring, and Data
-- ============================================================

-- 1. Categories (Ejes Estratégicos ERAM)
CREATE TABLE IF NOT EXISTS oar_categories (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    linea             TEXT,
    color             TEXT,
    color_secondary   TEXT,
    icon              TEXT,
    path              TEXT,
    description       TEXT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Countries
CREATE TABLE IF NOT EXISTS oar_countries (
    code              TEXT PRIMARY KEY, -- ISO code (GT, SV, HN, NI, CR, PA, BZ, DO, Regional)
    name              TEXT NOT NULL,
    flag              TEXT
);

-- 3. Strategic Questions
CREATE TABLE IF NOT EXISTS oar_questions (
    id                TEXT PRIMARY KEY,
    category_id       TEXT REFERENCES oar_categories(id) ON DELETE SET NULL,
    question          TEXT NOT NULL,
    short_question    TEXT,
    description       TEXT,
    highlight         TEXT, -- HTML content for highlights
    path              TEXT NOT NULL,
    icon              TEXT,
    color             TEXT,
    is_featured       BOOLEAN DEFAULT FALSE,
    view_count        INT DEFAULT 0,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Cifras (Indicators/Stats)
CREATE TABLE IF NOT EXISTS oar_cifras (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title             TEXT NOT NULL,
    value             TEXT NOT NULL,
    unit              TEXT,
    description       TEXT,
    source            TEXT,
    category_id       TEXT REFERENCES oar_categories(id) ON DELETE SET NULL,
    country_code      TEXT REFERENCES oar_countries(code) ON DELETE CASCADE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Monitoring Indicators
CREATE TABLE IF NOT EXISTS oar_indicators (
    id                TEXT PRIMARY KEY, -- e.g. "Goal A (1)"
    category_label    TEXT, -- "Objetivos Globales", etc.
    type              TEXT, -- "impacto", "gestion"
    title             TEXT NOT NULL,
    synergies         TEXT[], -- Array of strings
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Metrics for Indicators
CREATE TABLE IF NOT EXISTS oar_metrics (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indicator_id      TEXT REFERENCES oar_indicators(id) ON DELETE CASCADE,
    variable          TEXT,
    unit              TEXT,
    method            TEXT,
    source_national   TEXT,
    source_regional   TEXT
);

-- 7. Map Layers
CREATE TABLE IF NOT EXISTS oar_map_layers (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    category          TEXT, -- "Ambiental", "Productiva", etc.
    layer_type        TEXT, -- "GeoJSON", "WMS", "Raster"
    status            TEXT DEFAULT 'active',
    color             TEXT,
    description       TEXT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Historical Trends
CREATE TABLE IF NOT EXISTS oar_trends (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year              INT NOT NULL,
    cover             BIGINT,
    loss              BIGINT,
    restoration       BIGINT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Documents (New Functionality)
CREATE TABLE IF NOT EXISTS oar_documents (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    description       TEXT,
    source            TEXT,
    axes              TEXT[], -- e.g. ['Bosques', 'Clima']
    type              TEXT, -- e.g. 'PDF', 'Manual'
    date              DATE,
    country           TEXT,
    author            TEXT,
    download_url      TEXT,
    thumbnail         TEXT,
    versions          JSONB DEFAULT '[]',
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. View Guides (Page Metadata)
CREATE TABLE IF NOT EXISTS oar_view_guides (
    path              TEXT PRIMARY KEY, -- e.g. '/' or '/preguntas'
    title             TEXT NOT NULL,
    description       TEXT,
    features          TEXT[],
    source            TEXT,
    learn_more        TEXT,
    image             TEXT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_oar_questions_cat ON oar_questions(category_id);
CREATE INDEX IF NOT EXISTS idx_oar_cifras_country ON oar_cifras(country_code);
CREATE INDEX IF NOT EXISTS idx_oar_cifras_cat     ON oar_cifras(category_id);
CREATE INDEX IF NOT EXISTS idx_oar_questions_featured ON oar_questions(is_featured) WHERE is_featured = TRUE;
