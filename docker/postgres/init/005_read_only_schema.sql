CREATE ROLE agent_reader LOGIN PASSWORD 'admin';

GRANT CONNECT ON DATABASE aisearchdb TO agent_reader;
GRANT USAGE ON SCHEMA public to agent_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public to agent_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES to agent_reader;

ALTER ROLE agent_reader SET default_transaction_read_only = on;