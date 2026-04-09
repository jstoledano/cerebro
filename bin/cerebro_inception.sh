#!/bin/bash

# ─────────────────────────────────────────────────────────────
# Cerebro Inception - Script de Despliegue Automatizado
# ─────────────────────────────────────────────────────────────

# Forzar el uso de slirp4netns para evitar el error de Pasta/IPv6 en WSL
export CONTAINER_NETWORK_BACKEND=slirp4netns

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$PROJECT_ROOT/lock"
COMPOSE_FILE="$PROJECT_ROOT/container/compose.yaml"
BACKUP_FILE="$PROJECT_ROOT/data/cerebro_plain.sql"

cd "$PROJECT_ROOT"

# 1. Verificación del Lock
if [ -f "$LOCK_FILE" ]; then
    echo " [!] Error: El archivo de bloqueo '$LOCK_FILE' ya existe."
    exit 1
fi

echo " [*] Iniciando proceso de Inception..."

# 2. Limpieza de contenedores e imágenes previas
echo " [*] Limpiando entorno..."
# Forzamos la eliminación de cualquier rastro
podman-compose -f "$COMPOSE_FILE" down -v 2>/dev/null
podman rm -f --all 2>/dev/null
podman rmi localhost/cerebro_web:latest 2>/dev/null

# 3. Creación de la imagen (forzar slirp4netns en el build)
echo " [*] Construyendo imagen de Django (sin caché)..."
if ! CONTAINER_NETWORK_BACKEND=slirp4netns podman build --network=slirp4netns --no-cache -t localhost/cerebro_web:latest -f Containerfile .; then
    echo " [!] Error crítico: Falló la construcción de la imagen."
    exit 1
fi

# 4. Ejecución del Compose
echo " [*] Levantando servicios..."
if ! CONTAINER_NETWORK_BACKEND=slirp4netns podman-compose -f "$COMPOSE_FILE" up -d; then
    echo " [!] Error crítico: No se pudieron levantar los servicios."
    exit 1
fi

# 5. Esperar a que la DB esté lista
echo " [*] Esperando a que la base de datos esté lista..."
# Intentar conectar hasta 10 veces antes de fallar
for i in {1..10}; do
    if podman exec sherpa-db pg_isready -U sherpa > /dev/null 2>&1; then
        echo " [+] Base de datos lista."
        break
    fi
    if [ $i -eq 10 ]; then
        echo " [!] Error: La base de datos no arrancó a tiempo."
        exit 1
    fi
    sleep 2
done

# 6. Restauración de la base de datos
echo " [*] Preparando esquema y restaurando respaldo..."
# Limpiar esquema completamente
podman exec sherpa-db psql -U sherpa -d sherpa -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null

if [ -f "$BACKUP_FILE" ]; then
    echo " [*] Restaurando datos desde $BACKUP_FILE..."
    podman cp "$BACKUP_FILE" sherpa-db:/tmp/backup.sql
    # Restaurar BD - ignorar errores de constraints que puedan ocurrir
    if podman exec sherpa-db psql -U sherpa -d sherpa -f /tmp/backup.sql 2>&1 | grep -q "ERROR.*already exists"; then
        echo " [!] Advertencia: Algunos constraints ya existen, pero la restauración continuó."
        podman exec sherpa-db psql -U sherpa -d sherpa -f /tmp/backup.sql > /dev/null 2>&1
    fi
    if podman exec sherpa-db psql -U sherpa -d sherpa -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | grep -q "[1-9]"; then
        echo " [+] Respaldo restaurado con éxito."
        podman exec sherpa-db rm /tmp/backup.sql
    else
        echo " [!] Error: La restauración del SQL no creó tablas."
        exit 1
    fi
else
    echo " [!] Advertencia: No se encontró el archivo de respaldo en $BACKUP_FILE"
    echo " [*] La base de datos estará vacía. Ejecuta 'python manage.py migrate' manualmente si es necesario."
fi

# 7. Finalización y creación del Lock
echo " [*] Reiniciando servidor web para refrescar conexiones..."
podman restart sherpa-web > /dev/null

# Crear lock - Si el sistema de archivos no permite 0400, al menos existirá
touch "$LOCK_FILE"
chmod 0400 "$LOCK_FILE" 2>/dev/null

echo " [✔] Proceso completado. Cerebro está operativo."
