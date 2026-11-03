# Validación de la issue 138

La gestión normativa utiliza la unidad asignada a la actividad y la estructura activa del personal responsable de cada ejecución. La cabecera funcional local 50 comprende sus descendientes y las unidades 51, 52 y 53 con sus descendientes activos. Una asignación normativa en una actividad conserva ese alcance, sin extenderlo al resto del plan. Se conserva la política de visibilidad de los planes; un plan restringido requiere el permiso de consulta existente.

La consulta consolidada se abre desde **Agenda → Evidencias del equipo**, en `/pas/evidences/`. Incluye filtros combinables por actividad, ejecución, responsable operativo, fecha de evidencia (extremos inclusivos) y estado de ejecución. Se pagina en grupos de 30. La API admite los mismos parámetros `actividad`, `ejecucion`, `responsable`, `desde`, `hasta` y `estado` en `/api/v1/pas/evidences/`.

La gestión autenticada valida el alcance tanto en consultas como en mutaciones. Se conserva la consulta anónima de evidencias publicadas mediante la visibilidad pública ya existente. La auditoría se muestra exclusivamente a usuarios autorizados para gestionar la ejecución.

Un normativo puede editar los metadatos y sustituir el archivo de una ejecución terminada. Crear o eliminar evidencias sigue requiriendo una ejecución abierta. Los planes cerrados o con recurrencia registrada conservan su bloqueo. El autor original permanece y `modificada_por` identifica la última modificación. El historial registra actor, rol, operación y valores anteriores y posteriores. La baja física conserva ese historial y elimina el archivo tras confirmar la transacción; una referencia compartida conserva su archivo mientras exista otra evidencia que lo utilice.

## Preparación

Desde `src`, con el entorno habitual del proyecto activado, aplicar la migración de auditoría.

```sh
python manage.py migrate pas
```

## Pruebas automatizadas

La nueva cobertura está en `apps.pas.tests_normativo`. Ejecutar las pruebas de PAS y después la suite completa con la configuración de pruebas del proyecto.

```sh
python manage.py test apps.pas --settings=core.settings_test
python manage.py test --settings=core.settings_test
```

En el entorno de implementación se comprobó la sintaxis Python y el diff. Las pruebas Django quedaron pendientes porque Django no estaba instalado y el instalador no pudo obtener las dependencias. La suite nueva contiene casos de jerarquía local y distrital, unidades inactivas, límites de acceso, fechas y estados, paginación, edición cerrada, autoría, auditoría, sustitución de archivo, baja física y reversión de transacciones.

## Pruebas manuales

| Caso | Resultado esperado |
|---|---|
| Normativo 50, operativos 5011, 51 y 5203 activos y correctamente relacionados | Puede consultar, crear, editar y eliminar evidencias de sus ejecuciones abiertas. |
| Actividad asignada normativamente a 50 con responsables de otras áreas | Puede gestionar las evidencias de esa actividad. |
| Otra actividad del mismo plan sin relación normativa ni personal a cargo | Queda fuera de la gestión y consulta consolidada autenticada. |
| Subordinado asignado a otro plan visible | Sus evidencias aparecen en la consulta consolidada. |
| Evidencia de ejecución terminada | El normativo puede editarla y reemplazar el archivo; la ejecución conserva su estado. |
| Guardar una edición sin seleccionar archivo | Se conserva el archivo anterior. |
| Confirmar eliminación en ejecución abierta | Desaparecen registro y archivo; la ejecución y su historial permanecen. |
| Cancelar eliminación | Se conservan registro y archivo. |
| Filtros combinados y cambio de página | Se conserva el alcance y la selección de filtros. |
| Historial de creación, edición y eliminación | Muestra identidad, rol, operación, fecha y valores registrados. |
| Usuario operativo con unidad organizacional | Conserva el bloqueo de edición en sus ejecuciones terminadas. |
| Plan restringido o cerrado | Conserva sus reglas de visibilidad y bloqueo, respectivamente. |

La migración agrega campos y una tabla de auditoría. El historial comienza con las operaciones realizadas después de aplicar el cambio; los registros existentes conservan su autor y su archivo.
