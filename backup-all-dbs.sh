#!/usr/bin/env bash
set -euo pipefail

# Export all service Postgres DBs into SQL dumps.
# Optionally exports each table as CSV too.
#
# Usage:
#   ./backup-all-dbs.sh
#   ./backup-all-dbs.sh --env-file .env --out-dir backups/interview --with-csv
#
# Output:
#   <out-dir>/users_db.sql
#   <out-dir>/events_db.sql
#   <out-dir>/invitations_db.sql
#   <out-dir>/manifest.txt
#   <out-dir>/*.csv (if --with-csv)

ENV_FILE=".env"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="backups/${TIMESTAMP}"
WITH_CSV="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --with-csv)
      WITH_CSV="true"
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: ./backup-all-dbs.sh [--env-file .env] [--out-dir backups/x] [--with-csv]"
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

mkdir -p "$OUT_DIR"
OUT_DIR_ABS="$(cd "$OUT_DIR" && pwd)"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

parse_db_url() {
  local url="$1"
  python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

raw = sys.argv[1].strip()
normalized = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
p = urlparse(normalized)
user = p.username or ""
password = p.password or ""
host = p.hostname or "localhost"
port = str(p.port or 5432)
db = (p.path or "/").lstrip("/")
print("\t".join([user, password, host, port, db]))
PY
}

dump_one_db() {
  local label="$1"
  local db_url="$2"

  IFS=$'\t' read -r db_user db_pass db_host db_port db_name <<< "$(parse_db_url "$db_url")"
  if [[ -z "$db_name" || -z "$db_user" ]]; then
    echo "Failed to parse DB URL for $label"
    exit 1
  fi

  echo "Dumping $label -> ${db_name}.sql"
  docker run --rm \
    --add-host=host.docker.internal:host-gateway \
    -v "$OUT_DIR_ABS:/backup" \
    -e PGPASSWORD="$db_pass" \
    postgres:16-alpine \
    sh -lc "pg_dump -h '$db_host' -p '$db_port' -U '$db_user' -d '$db_name' --no-owner --no-privileges -f '/backup/${db_name}.sql'"

  if [[ "$WITH_CSV" == "true" ]]; then
    echo "Exporting CSV tables for $label"
    local table_list
    table_list="$(
      docker run --rm \
        --add-host=host.docker.internal:host-gateway \
        -e PGPASSWORD="$db_pass" \
        postgres:16-alpine \
        sh -lc "psql -h '$db_host' -p '$db_port' -U '$db_user' -d '$db_name' -Atc \"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\""
    )"

    if [[ -n "$table_list" ]]; then
      while IFS= read -r table; do
        [[ -z "$table" ]] && continue
        docker run --rm \
          --add-host=host.docker.internal:host-gateway \
          -v "$OUT_DIR_ABS:/backup" \
          -e PGPASSWORD="$db_pass" \
          postgres:16-alpine \
          sh -lc "psql -h '$db_host' -p '$db_port' -U '$db_user' -d '$db_name' -c \"\\copy public.\\\"$table\\\" TO '/backup/${db_name}__${table}.csv' CSV HEADER\""
      done <<< "$table_list"
    fi
  fi
}

dump_one_db "user-service" "${USERS_DATABASE_URL:?USERS_DATABASE_URL missing}"
dump_one_db "event-service" "${EVENTS_DATABASE_URL:?EVENTS_DATABASE_URL missing}"
dump_one_db "invitation-service" "${INVITATIONS_DATABASE_URL:?INVITATIONS_DATABASE_URL missing}"

cat > "${OUT_DIR_ABS}/manifest.txt" <<EOF
Backup created at: $(date)
Env file: ${ENV_FILE}
Contains:
  - users_db.sql
  - events_db.sql
  - invitations_db.sql
CSV exported: ${WITH_CSV}

Restore examples:
  psql -h <host> -U users -d users_db < users_db.sql
  psql -h <host> -U events -d events_db < events_db.sql
  psql -h <host> -U invitations -d invitations_db < invitations_db.sql
EOF

echo "Backup complete: ${OUT_DIR_ABS}"
