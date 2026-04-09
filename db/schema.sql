-- Knowledge Base Schema
-- Table: documents - stores searchable content

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster text search
CREATE INDEX IF NOT EXISTS idx_documents_content 
ON documents(content);

CREATE INDEX IF NOT EXISTS idx_documents_category 
ON documents(category);
