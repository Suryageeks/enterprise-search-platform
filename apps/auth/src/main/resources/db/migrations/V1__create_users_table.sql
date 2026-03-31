CREATE TABLE "Users" (
    "Id" BIGSERIAL PRIMARY KEY NOT NULL,
    "emp_id" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "is_active" CHAR(1) DEFAULT '1' NOT NULL,
    "created_at" DATE DEFAULT CURRENT_TIMESTAMP
);