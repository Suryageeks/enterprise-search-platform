#!/bin/sh
set -eu

if ! psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --command \
    "SELECT 1 FROM pg_database WHERE datname = 'mlflowdb'" | grep -q 1; then
    createdb --username "$POSTGRES_USER" mlflowdb
fi
