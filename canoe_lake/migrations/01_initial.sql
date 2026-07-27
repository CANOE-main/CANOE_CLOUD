CREATE TABLE IF NOT EXISTS bronze_sources (
    id UUID PRIMARY KEY,
    source_name VARCHAR NOT NULL,
    source_type VARCHAR,
    source_url_or_doc_id VARCHAR,
    collection_date DATE NOT NULL,
    collected_by VARCHAR,
    file_path VARCHAR NOT NULL,
    file_hash VARCHAR,
    file_format VARCHAR,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS silver_datasets (
    id UUID PRIMARY KEY,
    bronze_id UUID REFERENCES bronze_sources(id),
    source_name VARCHAR NOT NULL,
    processing_script_path VARCHAR,
    git_hash VARCHAR,
    processed_date DATE NOT NULL,
    processed_by VARCHAR,
    file_path VARCHAR NOT NULL
);
