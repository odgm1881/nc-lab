#!/bin/sh
set -eu

backup_file=${1:-}
target_url=${RESTORE_TEST_DATABASE_URL:-}

if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
  echo "Usage: RESTORE_TEST_DATABASE_URL=... $0 path/to/backup.dump" >&2
  exit 2
fi
if [ -z "$target_url" ]; then
  echo "RESTORE_TEST_DATABASE_URL is required" >&2
  exit 2
fi

libpq_url=$(printf '%s' "$target_url" | sed 's#^postgresql+psycopg://#postgresql://#')
database_name=$(psql "$libpq_url" -Atc 'select current_database()')
case "$database_name" in
  *_restore_test) ;;
  *)
    echo "Refusing restore: target database must end with _restore_test" >&2
    exit 3
    ;;
esac

if [ -f "$backup_file.sha256" ]; then
  backup_dir=$(dirname "$backup_file")
  checksum_name=$(basename "$backup_file").sha256
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$backup_dir" && sha256sum -c "$checksum_name")
  elif command -v shasum >/dev/null 2>&1; then
    (cd "$backup_dir" && shasum -a 256 -c "$checksum_name")
  else
    echo "Neither sha256sum nor shasum is available" >&2
    exit 5
  fi
fi

pg_restore --clean --if-exists --no-owner --no-acl --dbname="$libpq_url" "$backup_file"
table_count=$(psql "$libpq_url" -Atc "select count(*) from information_schema.tables where table_schema='public'")
alembic_revision=$(psql "$libpq_url" -Atc 'select version_num from alembic_version limit 1')

if [ "$table_count" -lt 7 ] || [ -z "$alembic_revision" ]; then
  echo "Restore verification failed" >&2
  exit 4
fi

printf 'restore_ok database=%s tables=%s revision=%s\n' "$database_name" "$table_count" "$alembic_revision"
