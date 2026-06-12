CREATE TABLE IF NOT EXISTS "Users" (
    "Id" BIGSERIAL PRIMARY KEY NOT NULL,
    "emp_id" VARCHAR(255) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "is_active" CHAR(1) DEFAULT '1' NOT NULL,
    "created_at" DATE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    emp_id VARCHAR(50) NOT NULL,
    doc_id UUID UNIQUE,
    uploadtype VARCHAR(10),
    file_status VARCHAR(20),
    file_name VARCHAR(500),
    file_size BIGINT,
    file_path VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE,
    emp_id VARCHAR(50) NOT NULL,
    doc_id UUID,
    file_name VARCHAR(500),
    status VARCHAR(100),
    stream_name VARCHAR(250),
    error_message VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_emp_id ON documents(emp_id);
CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_emp_id ON ingestion_jobs(emp_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_doc_id ON ingestion_jobs(doc_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_job_id ON ingestion_jobs(job_id);

INSERT INTO "Users" ("emp_id", "name", "email", "password", "is_active")
VALUES ('EMP001', 'Local Admin', 'local.admin@example.com', 'admin', '1')
ON CONFLICT ("emp_id") DO NOTHING;
