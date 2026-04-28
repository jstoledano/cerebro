# Cerebro - Guía de Operaciones

Instrucciones para levantar, actualizar y detener el servicio de Cerebro usando Docker Compose con Podman.

## Tabla de Contenidos

- [Levantamiento del Servicio](#levantamiento-del-servicio)
- [Detención del Servicio](#detención-del-servicio)
- [Actualización del Servicio](#actualización-del-servicio)
- [Inicialización Completa (Primera Vez)](#inicialización-completa-primera-vez)
- [Arquitectura de Persistencia](#arquitectura-de-persistencia)
- [Troubleshooting](#troubleshooting)

---

## Levantamiento del Servicio

### Después de un Reinicio (Recomendado)

```bash
cd container
podman-compose up -d
```

**Lo que ocurre:**
- Los volúmenes persistentes (BD, static files, media) se reutilizan
- Los contenedores se crean/inician desde la última configuración
- La base de datos mantiene todos los datos
- El servicio está disponible en `http://127.0.0.1:8000`

**Tiempo estimado:** 10-20 segundos

**Verificación:**
```bash
podman-compose ps
# Debe mostrar sherpa-db y sherpa-web en estado "Up"
```

---

## Detención del Servicio

### Forma Correcta (SIN Pérdida de Datos)

```bash
cd container
podman-compose down
```

**Lo que ocurre:**
- Los contenedores se detienen y se eliminan
- Los volúmenes persistentes se **preservan** (datos persisten)
- La próxima vez que ejecutes `podman-compose up -d`, todo funciona igual

⚠️ **NUNCA uses:**
```bash
podman-compose down -v  # ❌ Esto BORRA la base de datos
```

---

## Actualización del Servicio

### Cuando hay cambios en el código o dependencias

```bash
cd container
podman-compose down
podman-compose up -d --build
```

**Lo que ocurre:**
1. Se detienen los contenedores actuales
2. Se reconstruye la imagen del web (Containerfile)
3. Se levantan nuevamente los contenedores
4. Los volúmenes persistentes se reutilizan (datos intactos)

**Para actualizaciones solo de código (sin dependencias nuevas):**
```bash
cd container
podman-compose up -d
# Los cambios en src/ se aplican automáticamente (volumen montado)
```

---

## Inicialización Completa (Primera Vez)

### Cuando necesitas crear la BD desde cero

```bash
cd /path/to/cerebro
bash bin/cerebro_inception.sh
```

**Este script hace:**
1. Limpia completamente el entorno (contenedores, imágenes, volúmenes)
2. Reconstruye la imagen de Django (sin caché)
3. Levanta los servicios con `network_mode: "host"`
4. Espera a que PostgreSQL esté listo
5. Restaura la BD desde `data/cerebro_plain.sql` (si existe)
6. Reinicia el web para refrescar conexiones

**⚠️ Cuidado:** Este script **BORRA TODOS LOS DATOS ANTERIORES**. Solo usar en primera instalación o para resetear completamente.

---

## Arquitectura de Persistencia

### Volúmenes Docker

Cerebro usa **tres volúmenes persistentes** que sobreviven reinicios y actualizaciones:

| Volumen | Propósito | Ubicación |
|---------|-----------|-----------|
| `sherpa-pgdata` | Base de datos PostgreSQL | `/var/lib/postgresql/data` |
| `sherpa-staticfiles` | Archivos estáticos de Django | `/app/staticfiles` |
| `sherpa-media` | Archivos subidos por usuarios | `/app/media` |

**Ubicación en el host (Podman rootless):**
```
~/.local/share/containers/storage/volumes/cerebro_<volumen_name>/_data/
```

### Flujo de Datos

```
┌─────────────────────────────────────────────────┐
│         Reinicio del Equipo                     │
└─────────────────────────┬───────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────┐
│    podman-compose up -d (en container/)         │
└─────────────────────────┬───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
    sherpa-db        sherpa-web      Volúmenes
   (PostgreSQL)     (Django/Gunicorn)   (BD + Files)
   REUTILIZA        REUTILIZA         REUTILIZAN
   última config    última config     datos persistentes
         │                │                │
         └────────────────┼────────────────┘
                          │
                          ▼
              ✅ Servicio Funcional
              (todos los datos intactos)
```

---

## Configuración Crítica

### `network_mode: "host"` (En compose.yaml)

Cerebro usa `network_mode: "host"` en ambos servicios. Esto significa:
- Los contenedores usan la red del **host directamente**
- PostgreSQL escucha en `localhost:5432` del host
- Django se conecta a `localhost:5432`
- No hay aislamiento de red entre contenedores

**Por qué es necesario en este entorno:**
- Compatibilidad con Podman rootless en WSL/RHEL
- Evita problemas de routing IPv6

### Variables de Entorno (`.env.container`)

```env
DB_HOST=localhost              # Host donde PostgreSQL escucha
DB_PORT=5432                   # Puerto de PostgreSQL
DATABASE_URL=postgres://sherpa:el-charro-negro@localhost:5432/sherpa
```

⚠️ **NO cambiar estos valores** sin entender las implicaciones de `network_mode: "host"`.

---

## Comandos Útiles

### Logs en Tiempo Real

```bash
cd container
# Logs de todos los servicios
podman-compose logs -f

# Logs solo de la BD
podman-compose logs -f db

# Logs solo del web
podman-compose logs -f web
```

### Conectarse a PostgreSQL Directamente

```bash
podman exec -it sherpa-db psql -U sherpa -d sherpa

# Comandos útiles en psql:
\dt                    # Listar tablas
\d <table_name>        # Ver estructura de tabla
SELECT COUNT(*) FROM <table_name>;  # Contar registros
```

### Ejecutar Comandos Django

```bash
podman exec sherpa-web python manage.py <comando>

# Ejemplos:
podman exec sherpa-web python manage.py shell
podman exec sherpa-web python manage.py createsuperuser
podman exec sherpa-web python manage.py collectstatic --noinput
```

### Estado de Volúmenes

```bash
podman volume ls
podman volume inspect cerebro_sherpa-pgdata
```

---

## Troubleshooting

### Problema: "Address already in use" (Puerto 5432)

**Causa:** PostgreSQL en el host o contenedor anterior bloqueando puerto.

**Solución:**
```bash
# Ver qué usa el puerto
sudo lsof -i :5432

# Matar proceso (si es anterior)
sudo kill -9 <PID>

# Limpiar completamente
podman-compose down
podman system prune -f
podman-compose up -d
```

### Problema: "relation ... does not exist"

**Causa:** Migrations no se ejecutaron.

**Solución:**
```bash
# Espera a que DB esté lista
sleep 5

# Ejecuta migrations
podman exec sherpa-web python manage.py migrate

# Reinicia web
podman restart sherpa-web
```

### Problema: Los cambios en código no se aplican

**Causa:** El contenedor puede tener caché.

**Solución:**
```bash
cd container
podman-compose restart web
# O reconstruir:
podman-compose up -d --build
```

### Problema: "Too many routes" / networking errors

**Causa:** Problemas de routing en Podman con IPv6.

**Solución:**
```bash
# Usa slirp4netns explícitamente
export CONTAINER_NETWORK_BACKEND=slirp4netns
podman-compose down
podman-compose up -d
```

---

## Checklist de Mantenimiento

- ☐ Hacer backup de `data/cerebro_plain.sql` regularmente
- ☐ Verificar logs de errores en Django (`podman-compose logs web`)
- ☐ Monitorear uso de disco en volúmenes
- ☐ Actualizar dependencias en `requirements.txt` cuando sea necesario
- ☐ Usar `podman-compose down` (sin `-v`) para paradas correctas

---

## Resumen Rápido

| Acción | Comando | Datos Persistidos |
|--------|---------|-------------------|
| Arrancar | `podman-compose up -d` | ✅ Sí |
| Parar (correcto) | `podman-compose down` | ✅ Sí |
| Parar (incorrecto) | `podman-compose down -v` | ❌ No |
| Actualizar | `podman-compose up -d --build` | ✅ Sí |
| Reset total | `bash bin/cerebro_inception.sh` | ❌ No (restaura BD) |

