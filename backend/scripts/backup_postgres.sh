#!/bin/sh
set -eu

backup_root=${1:-./var/backups}
database_url=${DATABASE_URL:-}

if [ -z "$database_url" ]; then
  echo "DATABASE_URL is required" >&2
  exit 2
fi

case "$database_url" in
  sqlite*)
    echo "PostgreSQL backup cannot use a SQLite DATABASE_URL" >&2
    exit 2
    ;;
esac

libpq_url=$(printf '%s' "$database_url" | sed 's#^postgresql+psycopg://#postgresql://#')
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$backup_root"
backup_name="nklab-$timestamp-$$.dump"
backup_file="$backup_root/$backup_name"

umask 077
pg_dump --format=custom --no-owner --no-acl --file="$backup_file" "$libpq_url"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$backup_root" && sha256sum "$backup_name" > "$backup_name.sha256")
elif command -v shasum >/dev/null 2>&1; then
  (cd "$backup_root" && shasum -a 256 "$backup_name" > "$backup_name.sha256")
else
  echo "Neither sha256sum nor shasum is available" >&2
  exit 5
fi
printf '%s\n' "$backup_file"
