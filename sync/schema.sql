CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    title_slug TEXT,
    lang TEXT,
    runtime INTEGER,
    memory INTEGER,
    runtime_percentile REAL,
    memory_percentile REAL,
    timestamp INTEGER,
    code TEXT
);