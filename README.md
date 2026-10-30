# Cuadro de Mando Integral

### Información operativa, documental, geográfica y de seguimiento en una sola plataforma.

**CMI** es una plataforma web desarrollada para concentrar herramientas de información y seguimiento utilizadas por la Junta Local Ejecutiva del INE en Tlaxcala.

El proyecto integra gestión documental, seguimiento de planes y actividades, información geográfica electoral, indicadores operativos y capacidades de consulta fuera de línea dentro de una misma arquitectura.

`cerebro` es el nombre del repositorio y del proyecto Django que soporta al CMI.

---

## Una plataforma, varios problemas reales

El CMI parte de una idea sencilla: información relacionada con una misma operación institucional debería poder consultarse, relacionarse y utilizarse desde un mismo entorno.

Actualmente la plataforma cubre cinco grandes capacidades:

**Documentación · Planes · Cartografía · Indicadores · Movilidad**

Cada módulo resuelve un problema específico y comparte infraestructura, autenticación, permisos, información organizacional y una interfaz común.

---

# Documentación del SGC

## El documento vigente, su historia y su integridad

El módulo `docs` funciona como repositorio documental del Sistema de Gestión de la Calidad.

Los documentos se organizan por proceso y tipo, conservando cada revisión como una entidad independiente. Esto permite consultar tanto el documento vigente como su historial completo.

### Capacidades principales

- Lista Maestra de Documentos.
- Clasificación por procesos y tipos documentales.
- Control de revisiones.
- Historial de cambios.
- Archivos asociados a cada revisión.
- Checksum **SHA-256** para control de integridad.
- Búsqueda documental.
- Documentos de resultados.
- Reporte de documentos con problemas.
- Notificaciones de nuevas revisiones.
- Alertas urgentes.
- Suscripción a notificaciones.

El modelo documental conserva la trazabilidad entre:

```text
Documento
   └── Revisión 01
   └── Revisión 02
   └── Revisión 03
          ├── archivo
          ├── cambios
          ├── fecha
          ├── autor
          └── SHA-256
```

La revisión es parte del dato. El archivo es únicamente uno de sus componentes.

---

# CMI Móvil

## Documentación controlada incluso sin acceso a la red institucional

CMI Móvil extiende la gestión documental hacia escenarios con conectividad limitada o inexistente.

El sistema genera un paquete portátil que puede almacenarse en una memoria USB y consultarse localmente desde un navegador.

La aplicación portátil permite:

- sincronizar el directorio documental;
- buscar y filtrar documentos;
- trabajar sin conexión con el servidor;
- comprobar la vigencia de una copia;
- verificar que el archivo no haya sido alterado;
- trasladar documentación controlada a sitios sin conectividad.

La comprobación de integridad aprovecha la misma información criptográfica utilizada por el repositorio central.

```text
CMI
 │
 ├── documento vigente
 ├── metadatos
 └── checksum SHA-256
          │
          ▼
     CMI Móvil
          │
          ├── consulta offline
          ├── validación
          └── copia controlada
```

---

# Agenda y seguimiento de planes

## De un plan de acción a una agenda operativa

El módulo `pas` transforma planes, programas, metas y proyectos en trabajo concreto que puede seguirse en el tiempo.

Puede representar instrumentos muy distintos, desde un Plan de Acción del Sistema de Gestión de la Calidad hasta metas individuales o colectivas, actividades periódicas y proyectos transversales.

Su estructura operativa se basa en cuatro niveles:

```text
Plan
  └── Actividad
        └── Ciclo
              └── Ejecución
                    └── Evidencia
```

Una actividad describe **qué debe hacerse**.

Una ejecución representa **cada ocasión concreta en la que debe hacerse**.

Esta separación permite modelar actividades únicas, mensuales, semanales, continuas o aplicables simultáneamente a diferentes ámbitos organizacionales.

### Agenda PEC 2026-2027

La Agenda constituye la vista operativa del sistema.

En lugar de obligar a revisar individualmente todos los planes, presenta el trabajo desde la perspectiva de quien debe realizarlo.

Incluye:

- calendario de actividades;
- próximas acciones;
- actividades vencidas;
- responsables normativos;
- responsables operativos;
- ciclos;
- ámbitos de ejecución;
- evidencias;
- cierre y reapertura de ejecuciones;
- avance de los planes.

El radar clasifica el trabajo en tres horizontes:

**Urgente · Atención · Vigilar**

El objetivo es reducir la carga cognitiva asociada con el seguimiento de numerosos planes simultáneos y mostrar primero aquello que requiere una decisión o una acción.

### Estado calculado desde la ejecución real

El avance se obtiene a partir de las ejecuciones registradas y permite distinguir actividades:

- cerradas;
- abiertas en tiempo;
- abiertas fuera de tiempo;
- cerradas en tiempo;
- cerradas fuera de tiempo.

Un plan puede contener pocas actividades y, al mismo tiempo, decenas o cientos de ejecuciones cuando existen periodicidades o múltiples ámbitos.

---

# Cartografía electoral

## Del archivo cartográfico al expediente de una sección

El módulo `pusinex`, presentado en la interfaz como **Cartografía**, integra información geográfica electoral con información operativa asociada a distritos, municipios y secciones.

Está construido sobre modelos espaciales de Django y permite trabajar con geometrías electorales dentro de PostgreSQL/PostGIS.

Entre las entidades geográficas administradas se encuentran:

```text
Entidad
 ├── Distrito Federal
 ├── Distrito Local
 ├── Municipio
 └── Sección
       ├── Localidades
       ├── Manzanas
       ├── PE / LN
       └── PUSINEX
```

### Expedientes geográficos

Cada sección puede funcionar como un expediente que concentra información como:

- distrito;
- municipio;
- tipo de sección;
- ubicación;
- distancias y tiempos de traslado;
- Padrón Electoral;
- Lista Nominal;
- localidades;
- manzanas;
- archivos PUSINEX;
- historial de actualizaciones.

### PUSINEX

El sistema administra los Planos Urbanos por Sección Individual con Números Exteriores y permite:

- registrar nuevas versiones;
- mantener trazabilidad por usuario y fecha;
- consultar disponibilidad;
- generar paquetes;
- generar paquetes estatales;
- generar paquetes por distrito.

### Actualización del Marco Geográfico Electoral

La aplicación mantiene infraestructura para registrar procesos de actualización geográfica y documentar cambios tales como:

- modificación de geometrías;
- altas;
- bajas;
- reactivaciones.

Los procesos conservan actor, origen, estado, reporte y cambios realizados.

### VNM 2026

La cartografía incorpora herramientas específicas para la **VNM 2026**, incluyendo:

- secciones seleccionadas;
- seguimiento de cobertura;
- actualización;
- paquetes distritales;
- generación automatizada de entregables.

La lógica cartográfica y la preparación de productos operativos conviven así dentro del mismo sistema.

---

# Indicadores

## Los datos operativos convertidos en información para decidir

El CMI incorpora tableros especializados que procesan información operativa y la presentan mediante indicadores, distribuciones, tendencias y análisis históricos.

Actualmente existen dos tableros principales.

---

## Evaluación de desempeño CECyRD

Este módulo procesa información de trámites y permite evaluar el comportamiento de los tiempos asociados con la disponibilidad de credenciales.

Incluye un proceso **ETL** para incorporar archivos de operación al modelo interno.

Entre sus capacidades se encuentran:

- carga de archivos de trámites;
- procesamiento ETL;
- seguimiento del progreso de la carga;
- análisis histórico;
- análisis semestral;
- consultas por periodos personalizados;
- volumen de trámites;
- credenciales recibidas en tiempo;
- credenciales recibidas con retraso;
- porcentaje de cumplimiento;
- distribución de tiempos;
- relación entre volumen y desempeño;
- revisión semanal;
- generación de reportes PDF;
- conclusiones para la revisión del SGC.

El tablero permite pasar del archivo operativo a una lectura histórica y comparable del desempeño.

```text
Archivo operativo
       │
       ▼
      ETL
       │
       ▼
   PostgreSQL
       │
       ▼
 Indicadores
       │
       ├── tendencia
       ├── distribución
       ├── cumplimiento
       └── reporte
```

---

## Artículo 141

El tablero de **Artículo 141** analiza información histórica de trámites relacionados con este procedimiento y proporciona distintas perspectivas sobre su comportamiento.

Entre los análisis disponibles se encuentran:

- resumen general;
- trámites por mes;
- distribución por sexo;
- pirámide de edades;
- flujo entre distritos;
- desempeño de entrega;
- distribución de días de entrega;
- comparación por año.

El mismo módulo incorpora un tablero específico para **Voto Anticipado**, con información por distrito y sección, así como componentes de georreferencia.

Esto permite combinar análisis estadístico y dimensión territorial dentro de una misma herramienta.

---

# Una arquitectura integrada

CMI está construido como un **monolito modular Django**.

Cada dominio mantiene sus propios modelos, vistas, servicios, plantillas y rutas, mientras comparte una infraestructura común.

```text
                    ┌─────────────────────┐
                    │        CMI          │
                    └──────────┬──────────┘
                               │
        ┌──────────────┬───────┴───────┬──────────────┐
        │              │               │              │
        ▼              ▼               ▼              ▼
  Documentación      Planes        Cartografía    Indicadores
      docs             pas           pusinex       cecyrd
        │               │               │           art141
        │               │               │
        ▼               ▼               ▼
   CMI Móvil        Agenda PEC       PostGIS
```

### Backend

- Python
- Django
- Django REST Framework
- PostgreSQL
- PostGIS
- Redis
- django-redis

### Interfaz

- Django Templates
- Tailwind CSS / daisyUI
- JavaScript
- HTMX en flujos interactivos
- visualizaciones especializadas en los tableros

### Servicios

- Nginx
- caché Redis
- archivos estáticos y media gestionados por el servidor web
- generación de PDF con WeasyPrint
- APIs REST con autenticación JWT y de sesión

---

# API

Parte de las capacidades del CMI están disponibles mediante una API versionada.

```text
/api/v1/
```

Actualmente existen endpoints para distintos dominios, entre ellos:

```text
/api/v1/docs/
/api/v1/pas/
/api/v1/profiles/
/api/v1/ideas/
/api/v1/vozmac/
```

Esto permite que determinadas funciones puedan ser consumidas por clientes distintos de la interfaz web principal.

---

# Componentes auxiliares

El proyecto incluye además servicios de soporte que complementan los módulos principales.

### Perfiles

Extiende la autenticación de Django con información organizacional, puesto, adscripción y jerarquía. Esta información permite contextualizar permisos, responsabilidades y visibilidad dentro de otros módulos.

### Ideas

Proporciona un mecanismo sencillo para registrar propuestas y dar seguimiento a su valoración.

### PMML

Servicio ligero de suscripción utilizado para gestionar destinatarios de alertas y notificaciones documentales.

### VozMAC

Módulo especializado para procesamiento y visualización de información de satisfacción ciudadana de los Módulos de Atención Ciudadana, con análisis estatal, distrital y por MAC.

---

# El principio

CMI intenta representar procesos institucionales reales mediante modelos suficientemente estructurados para ofrecer trazabilidad, automatización y análisis sin convertir la herramienta en el centro del proceso.

La plataforma está diseñada alrededor de una premisa:

> **La realidad debe modelar al sistema, no al revés.**

Documentos, actividades, ejecuciones, evidencia, territorio e indicadores pertenecen a dominios diferentes. El valor del CMI aparece cuando esos dominios pueden convivir dentro de una misma plataforma sin perder su significado.
