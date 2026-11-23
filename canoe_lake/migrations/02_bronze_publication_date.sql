-- register_manual_bronze records an optional publication date for manually gathered files.
ALTER TABLE bronze_sources ADD COLUMN IF NOT EXISTS publication_date DATE;
