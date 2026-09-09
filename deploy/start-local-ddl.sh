#!/bin/zsh
set -eu

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_DIR="/Users/apple/ddl-local"
NPM="/usr/local/bin/npm"
cd "$PROJECT_DIR"

"$NPM" --prefix frontend run build
exec "$PROJECT_DIR/.venv/bin/daphne" -b 127.0.0.1 -p 8000 ddl_project.asgi:application
