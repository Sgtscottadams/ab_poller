-- Schema for knowledge.db
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    client TEXT,
    location TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    collection TEXT,
    record_json TEXT,
    summary TEXT,
    tags TEXT,
    status TEXT,
    last_updated TEXT,
    file_path TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- Indexes for efficient searching
CREATE INDEX IF NOT EXISTS idx_records_project ON records(project_id);
CREATE INDEX IF NOT EXISTS idx_records_collection ON records(collection);
CREATE INDEX IF NOT EXISTS idx_records_tags ON records(tags);
CREATE INDEX IF NOT EXISTS idx_records_status ON records(status);
