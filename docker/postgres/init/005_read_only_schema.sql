DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'agent_reader'
    ) THEN
        CREATE ROLE agent_reader
        LOGIN
        PASSWORD 'agent_reader_local_password';
    END IF;
END
$$;

ALTER ROLE agent_reader
SET default_transaction_read_only = on;

ALTER ROLE agent_reader
WITH PASSWORD 'agent_reader_local_password';

REVOKE ALL ON DATABASE aisearchdb FROM agent_reader;
GRANT CONNECT ON DATABASE aisearchdb TO agent_reader;

REVOKE CREATE ON SCHEMA public FROM agent_reader;
GRANT USAGE ON SCHEMA public TO agent_reader;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM agent_reader;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM agent_reader;

-- Grant only operational metadata required by explicitly typed agent tools.
-- Add future incident tables individually instead of granting the whole schema.
GRANT SELECT ON TABLE documents, ingestion_jobs TO agent_reader;
