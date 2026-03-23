CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    emp_id VARCHAR(50) NOT NULL,
    doc_id UUID,
    uploadtype VARCHAR(10),
    file_status VARCHAR(20),
    file_name VARCHAR(500),
    file_size BIGINT,
    file_path VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL default current_timestamp,
    updated_at TIMESTAMP
);