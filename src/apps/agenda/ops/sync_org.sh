#!/bin/sh
# Ejecucion desde cron en el servidor. Requiere git, flock, emacs y Python/Django.
# Uso: sync_org.sh /ruta/agenda-repo /ruta/cerebro/src /ruta/.venv/bin/python
set -eu
if [ "$#" -ne 3 ]; then
  printf 'Uso: %s AGENDA_REPO CEREBRO_SRC PYTHON_BIN\n' "$0" >&2
  exit 2
fi
AGENDA_REPO=$1
CEREBRO_SRC=$2
PYTHON_BIN=$3
LOCK_FILE="${TMPDIR:-/tmp}/cerebro-agenda-sync.lock"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

# El pull debe terminar correctamente para publicar datos nuevos.
git -C "$AGENDA_REPO" pull --ff-only
cd "$CEREBRO_SRC"
"$PYTHON_BIN" manage.py agenda_export
