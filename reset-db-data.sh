#!/usr/bin/env bash
set -euo pipefail

# Reset all service DB data (users/events/invitations).
# Works for both compose setups:
#   - dockerdb: docker-compose.yml (postgres runs in Docker)
#   - localdb:  docker-compose.localdb.yml (postgres runs on host)
#
# Usage:
#   ./reset-db-data.sh                 # default: localdb
#   ./reset-db-data.sh localdb
#   ./reset-db-data.sh dockerdb

MODE="${1:-localdb}"

if [[ "$MODE" == "dockerdb" ]]; then
  COMPOSE_FILE="docker-compose.yml"
elif [[ "$MODE" == "localdb" ]]; then
  COMPOSE_FILE="docker-compose.localdb.yml"
else
  echo "Invalid mode: $MODE"
  echo "Use: localdb or dockerdb"
  exit 1
fi

echo "Using compose file: $COMPOSE_FILE"

# Ensure services are up so exec can run.
docker compose -f "$COMPOSE_FILE" up -d user-service event-service invitation-service >/dev/null

run_reset() {
  local service_name="$1"
  echo "Resetting DB via $service_name ..."
  docker compose -f "$COMPOSE_FILE" exec -T "$service_name" python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public'"
            )
        )
        table_names = [row[0] for row in result.fetchall()]
        if table_names:
            quoted = ", ".join(f'public."{name}"' for name in table_names)
            await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    await engine.dispose()

asyncio.run(main())
PY
}

run_reset user-service
run_reset event-service
run_reset invitation-service

echo "All database data cleared."
echo "Recreating tables by restarting services..."
docker compose -f "$COMPOSE_FILE" restart user-service event-service invitation-service api-gateway >/dev/null || true
echo "Done."
