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

CREATE TABLE INGESTION_JOBS(
 	id SERIAL PRIMARY KEY,
	job_id UUID,
    emp_id VARCHAR(50) NOT NULL,
    doc_id UUID,
    file_name VARCHAR(500),
	status VARCHAR(100),
	stream_name VARCHAR(250),
	error_message VARCHAR,
	created_at TIMESTAMPTZ NOT NULL default current_timestamp,
    updated_at TIMESTAMP
);