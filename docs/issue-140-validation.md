# Agenda diaria y notificaciones documentales

## Reglas de operación

PM² usa un calendario único de días administrado por usuarios con el permiso `pas.change_calendarionotificaciones`; los superusuarios cuentan con ese permiso. El valor inicial es lunes a viernes. El envío programado ocurre a las 08:00 en `America/Mexico_City`. Un servidor apagado a esa hora retomará el envío en el siguiente día habilitado; el temporizador evita un envío tardío al encenderlo.

Las unidades activas `00`, `10`, `20`, `30` y `50` reciben automáticamente su agenda con el mismo alcance y clasificación de Alarma, Faro y Radar de la pantalla. Los demás usuarios pueden activar su agenda mediante el interruptor de «Mi agenda por correo». Se reutiliza `Profile.recibe_notificaciones` para esa preferencia; la suscripción documental de PMML sigue siendo independiente.

Cada responsable operativo recibe automáticamente las ejecuciones asignadas que vencen ese día y las que continúan vencidas. Se excluyen ejecuciones concluidas, planes cerrados y planes que el destinatario carezca de permiso para consultar. Se envía un mensaje agrupado por usuario y fecha, que incorpora su agenda cuando corresponda. Se omiten resúmenes vacíos y cuentas inactivas o con correo inválido.

La persona normativa se resuelve a partir de la cabecera funcional de la clave de la actividad, por ejemplo `51` o `5010` corresponden a `50`. Cuando la actividad carece de clave normativa se usa la unidad del responsable operativo. Si existe exactamente un titular activo en esa cabecera con correo válido, el aviso lo identifica y permite remitirle evidencia. Cuando la asignación es ambigua, se utiliza una solicitud genérica de seguimiento sin atribuir instrucciones a una persona arbitraria. Las respuestas recibidas por correo requieren revisión y registro humano; no se incorporan automáticamente como evidencias.

## Entrega y seguridad de las pruebas

`NOTIFICACIONES_MODO` acepta `simular` (valor inicial) o `produccion`. Los comandos en modo simulado muestran destinatarios y conservan intactos los registros de envío. `--prueba` genera una sola muestra a `NOTIFICACIONES_CORREO_PRUEBA`, cuyo valor inicial es `javier.sanchezt@ine.mx`. Las muestras carecen de CC, BCC y Reply-To hacia destinatarios reales, y no marcan entregas de producción. El correo de Eileen nunca se usa como destino de una muestra.

La entrega usa el backend de correo configurado en Django, actualmente SMTP/Mailgun. Los modelos y la selección de tareas no dependen de su API. Cambiar de proveedor requiere configurar un backend compatible y sus credenciales; no se incorpora Microsoft Graph en este cambio.

Una reserva atómica impide que dos procesos envíen el mismo registro. Los resultados posibles son pendiente, enviando, aceptado, fallido o incierto. «Aceptado» acredita aceptación por SMTP, no llegada a la bandeja del destinatario. La desconexión durante una entrega puede producir un resultado incierto; ese registro y los que queden en estado enviando requieren revisar los eventos del proveedor por Message-ID antes de cualquier intervención. Un rechazo definitivo permite `--reintentar-fallidos`. No se promete entrega exactamente una vez frente a la pérdida de conexión después de la aceptación remota.

## PMML

El comando anterior marcaba todas las revisiones notificadas incluso cuando un envío individual fallaba. Ahora conserva una relación única entre revisión y destinatario y solo completa una revisión después de la aceptación de todos sus suscriptores activos válidos. Los destinatarios ya aceptados quedan excluidos del reenvío efectivo. Los suscriptores con direcciones inválidas producen una incidencia y mantienen las revisiones pendientes hasta su corrección.

El diagnóstico consulta suscripciones y resultados locales. No activa suscripciones ni envía correos. En particular, la existencia de una cuenta de usuario y su preferencia de agenda no implican una suscripción activa a PMML.

```bash
python manage.py diagnosticar_correo eileen.zacaula@ine.mx
```

Los registros históricos que ya quedaron marcados como notificados antes de esta migración no contienen detalle suficiente para reconstruir sus entregas por destinatario. Este cambio conserva esas marcas para evitar un reenvío masivo. Para resolver un caso histórico, revisar primero suscripción, eventos de Mailgun y, si hay aceptación por el receptor institucional, trazas o cuarentena del buzón. El acceso al servidor y al proveedor es necesario para confirmar la causa concreta del caso de Eileen.

## Validación

Desde `src`, con el entorno virtual activo, ejecutar las pruebas específicas. Usan SQLite y correo en memoria, sin secretos SMTP ni conexión a Mailgun.

```bash
python manage.py test core.tests_mail --settings=core.settings_mail_test -v 2
```

El workflow de GitHub Actions ejecuta estas pruebas y verifica migraciones con un único trabajo de hasta cinco minutos. No ejecuta las suites obsoletas. La clasificación de la agenda web se extrajo a un servicio común conservando sus reglas; las pruebas comprueban el alcance y las tres categorías.

## Instalación y prueba controlada

1. Incorporar la rama y ejecutar `python manage.py migrate`. Reiniciar el proceso de Django.
2. Mantener `NOTIFICACIONES_MODO=simular` durante la revisión. Este valor también aplica al comando semanal `notificar_docs`; sus envíos reales requieren completar la activación descrita más abajo.
3. Abrir `/pas/agenda/correo/`. Para la administración del calendario, usar `/pas/agenda/calendario-correo/` con la cuenta administradora. Comprobar que una cuenta ordinaria recibe 403 en esa ruta.
4. Activar la agenda personal de Javier si desea recibir el resumen. Las cabeceras x0 quedan incluidas automáticamente. Verificar días seleccionados y rechazo de un calendario vacío.
5. Simular y comparar los resultados con la agenda y las asignaciones de cada usuario.

```bash
python manage.py notificar_agenda --simular
python manage.py notificar_docs --simular
```

Para recibir una muestra de la agenda prevista para Eileen exclusivamente en el correo de Javier, usar el siguiente comando en el equipo que tiene acceso a la base de datos y a SMTP.

```bash
python manage.py notificar_agenda --prueba --usuario eileen.zacaula@ine.mx
```

El calendario seleccionado se respeta también en la muestra. Si está fuera de los días habilitados o el resumen está vacío, el comando lo omitirá. La muestra documental se obtiene con `python manage.py notificar_docs --prueba`; requiere revisiones semanales pendientes.

## Programación después de validar

Usar el servidor existente. Las unidades de `conf/cerebro-agenda.service` y `conf/cerebro-agenda.timer` son plantillas basadas en las rutas y el usuario de `conf/cerebro.service`. Verificar `User`, `Group`, `WorkingDirectory` y la ruta de Python contra la instalación real antes de instalarlas.

Después de aprobar la prueba, establecer `NOTIFICACIONES_MODO=produccion` en el `.env` del servidor. Conservar la programación semanal existente de `notificar_docs` y utilizar una sola programación diaria para la agenda; evitar añadir un cron paralelo al timer.

```bash
sudo cp conf/cerebro-agenda.service conf/cerebro-agenda.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cerebro-agenda.timer
systemctl list-timers cerebro-agenda.timer
```

Consultar los resultados con `journalctl -u cerebro-agenda.service`. Para suspender la agenda, usar `sudo systemctl disable --now cerebro-agenda.timer`. Para suspender además los envíos semanales desde los nuevos comandos, volver a `NOTIFICACIONES_MODO=simular`.

Los timers y los envíos reales no se activan al hacer pull, migrar o abrir esta pull request. La issue permanece pendiente de validación manual y del diagnóstico de entrega institucional.
