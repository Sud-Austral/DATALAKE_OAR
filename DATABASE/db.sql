-- ============================================================
-- DATALAKE OAR — PostgreSQL Schema
-- Railway data lake: APIs, CSV, GeoJSON, Shapefile, PDF
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS & AUTH
-- ============================================================
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,  -- bcrypt hash
    role        TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- DATASETS — Logical grouping of data assets
-- ============================================================
CREATE TABLE datasets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         TEXT NOT NULL,
    description  TEXT,
    source       TEXT,
    domain       TEXT,                     -- e.g. railway, infrastructure, environment
    version      TEXT DEFAULT '1.0.0',
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'draft')),
    owner_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    size_bytes   BIGINT DEFAULT 0,
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- FILES — Physical file registry (CSV, GeoJSON, Shapefile, PDF)
-- ============================================================
CREATE TABLE files (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id     UUID REFERENCES datasets(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    original_name  TEXT NOT NULL,
    file_type      TEXT NOT NULL CHECK (file_type IN ('csv', 'geojson', 'shapefile', 'pdf', 'other')),
    mime_type      TEXT,
    storage_path   TEXT NOT NULL,          -- path in MinIO bucket
    bucket         TEXT NOT NULL DEFAULT 'oar-datalake',
    size_bytes     BIGINT,
    checksum_md5   TEXT,
    uploaded_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata       JSONB DEFAULT '{}',
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- API INGESTIONS — External API data pulls
-- ============================================================
CREATE TABLE api_ingestions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id    UUID REFERENCES datasets(id) ON DELETE SET NULL,
    source        TEXT NOT NULL,
    endpoint      TEXT NOT NULL,
    method        TEXT NOT NULL DEFAULT 'GET' CHECK (method IN ('GET', 'POST', 'PUT')),
    parameters    JSONB DEFAULT '{}',
    headers       JSONB DEFAULT '{}',
    file_path     TEXT,                    -- resulting file in storage
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed')),
    error_message TEXT,
    triggered_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    started_at    TIMESTAMP WITH TIME ZONE,
    finished_at   TIMESTAMP WITH TIME ZONE,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- TAGS — Semantic classification
-- ============================================================
CREATE TABLE tags (
    id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name  TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#6B7280'
);

CREATE TABLE dataset_tags (
    dataset_id  UUID REFERENCES datasets(id) ON DELETE CASCADE,
    tag_id      UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (dataset_id, tag_id)
);

-- ============================================================
-- AUDIT LOG — Operation traceability
-- ============================================================
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,             -- e.g. UPLOAD, DELETE, DOWNLOAD, LOGIN
    entity      TEXT NOT NULL,             -- e.g. files, datasets, api_ingestions
    entity_id   UUID,
    details     JSONB DEFAULT '{}',
    ip_address  TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_datasets_owner   ON datasets(owner_id);
CREATE INDEX idx_datasets_status  ON datasets(status);
CREATE INDEX idx_files_dataset    ON files(dataset_id);
CREATE INDEX idx_files_type       ON files(file_type);
CREATE INDEX idx_api_status       ON api_ingestions(status);
CREATE INDEX idx_audit_user       ON audit_log(user_id);
CREATE INDEX idx_audit_entity     ON audit_log(entity, entity_id);
CREATE INDEX idx_audit_created    ON audit_log(created_at DESC);