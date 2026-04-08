#!/bin/bash

# ─────────────────────────────────────────────────────────────
# Cerebro Inception - Script de Despliegue Automatizado
# ─────────────────────────────────────────────────────────────

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$PROJECT_ROOT/lock"
COMPOSE_FILE="$PROJECT_ROOT/container/compose.yaml"
BACKUP_FILE="$PROJECT_ROOT/data/cerebro_plain.sql"

cd "$PROJECT_ROOT"

# 1. Verificación del Lock
if [ -f "$LOCK_FILE" ]; then
    echo " [!] Error: El archivo de bloqueo '$LOCK_FILE' ya existe."
    echo "     Esto indica que el sistema ya fue inicializado o un proceso previo falló."
    exit 1
fi

echo " [*] Iniciando proceso de Inception..."

# 2. Limpieza de contenedores e imágenes previas
echo " [*] Limpiando entorno..."
podman-compose -f "$COMPOSE_FILE" down -v 2>/dev/null
podman rmi localhost/sherpa_web:latest 2>/dev/null

# 3. Creación de la imagen
echo " [*] Construyendo imagen de Django (sin caché)..."
if ! podman build --no-cache -t localhost/sherpa_web:latest -f Containerfile .; then
    echo " [!] Error crítico: Falló la construcción de la imagen."
    exit 1
fi

# 4. Ejecución del Compose
echo " [*] Levantando servicios..."
if ! CONTAINER_NETWORK_BACKEND=slirp4netns podman-compose -f "$COMPOSE_FILE" up -d; then
    echo " [!] Error crítico: No se pudieron levantar los servicios."
    exit 1
fi

# Esperar a que la DB esté lista (Healthcheck)
echo " [*] Esperando a que la base de datos esté lista..."
sleep 10

# 5. Restauración de la base de datos
echo " [*] Preparando base de datos y restaurando respaldo..."
# Limpiar esquema actual
podman exec sherpa-db psql -U sherpa -d sherpa -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" > /dev/null

# Copiar y restaurar
podman cp "$BACKUP_FILE" sherpa-db:/tmp/backup.sql
if podman exec sherpa-db psql -U sherpa -d sherpa -f /tmp/backup.sql > /dev/null; then
    echo " [+] Respaldo restaurado con éxito."
    podman exec sherpa-db rm /tmp/backup.sql
else
    echo " [!] Error: Falló la restauración de la base de datos."
    exit 1
fi

# 6. Finalización y creación del Lock
echo " [*] Reiniciando servidor web para refrescar conexiones..."
podman restart sherpa-web > /dev/null

touch "$LOCK_FILE"
chmod 0400 "$LOCK_FILE"

echo " [✔] Proceso completado. Cerebro está operativo."
