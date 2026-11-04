# Validación de la issue #139

Rama `avatar-profile-#139`, creada desde `master` en `b89ca02fcebf5d7a3045d61e6b6b09825c467134`.

## Cambios

La navbar identifica al usuario por nombre y apellidos, con respaldo en `username`. El avatar utiliza `profile.siglas`, o las iniciales de las primeras dos palabras del nombre disponible. Admite perfiles ausentes y escapa los datos al renderizarlos.

En escritorio aparecen el avatar, el indicador de sesión y el nombre truncado. El desplegable permite leer el nombre completo y cerrar sesión. En móvil y tablet, la identificación y el cierre de sesión quedan dentro de la hamburguesa; su indicador muestra que existe una sesión activa. La búsqueda existente se conserva entre 768 y 1279 píxeles, donde dispone de espacio suficiente.

Los desplegables usan `details` y `summary`, con activación nativa mediante Enter/Espacio. JavaScript agrega navegación con flechas, cierre mediante Esc con retorno del foco, cierre al salir y sincronización de `aria-expanded`. Los formularios conservan POST y CSRF hacia el LogoutView existente, con redirección al inicio.

El cambio mantiene modelos, migraciones, dependencias y rutas de producción existentes.

## Pruebas automatizadas

Desde `src`, con el entorno virtual habitual activo, ejecutar lo siguiente.

```bash
python manage.py test core.tests_navbar --settings=core.settings_navbar_test -v 2
```

La configuración aislada usa SQLite en memoria y caché local, y carga autenticación, sesiones y perfiles. Las rutas auxiliares permiten renderizar los enlaces del menú. Las vistas de autenticación son LoginView y LogoutView de Django, con las mismas opciones de las rutas de producción. Esta ejecución comprende 14 pruebas específicas y excluye la suite de PAS y las pruebas antiguas de otros módulos.

Se cubren sesión anónima y autenticada, siglas, iniciales, username, perfil ausente, escape HTML, nombre largo, login, logout, POST obligatorio, CSRF, sesión vencida y separación de identidades ante la caché pública.

La comprobación de nombre largo conserva y verifica el texto completo en el HTML; la distribución visual corresponde a las pruebas de navegador.

## Estado de verificación durante la implementación

La compilación de los archivos Python modificados y la comprobación sintáctica del JavaScript finalizaron correctamente. La ejecución de Django y las pruebas visuales quedaron pendientes: el entorno de implementación carece de Django y del ejecutable de Chromium; el acceso a PyPI devolvió HTTP 403. El comando anterior permite ejecutar la suite en el entorno del proyecto.

## Pruebas manuales

1. Abrir una página del CMI como visitante. Comprobar «Iniciar sesión» y ausencia de identidad, indicador activo y cierre de sesión.
2. Iniciar sesión. Verificar nombre y siglas; repetir con un usuario sin siglas y otro sin nombre/apellidos.
3. Abrir el menú de usuario y verificar el nombre completo y «Cerrar sesión».
4. Recorrer los controles con Tab. Abrir con Enter y Espacio, navegar con flechas arriba/abajo y cerrar con Esc. Verificar que el foco vuelve al control que abrió el menú y que Tab permite salir.
5. Repetir en anchos de 320, 375, 768, 1024, 1280 y 1440 píxeles. En anchos menores de 1280, abrir la hamburguesa y verificar identidad y logout. Comprobar ausencia de desplazamiento horizontal, incluido un nombre largo sin espacios.
6. Hacer clic fuera del desplegable y cambiar el ancho de la ventana. Verificar su cierre y la presentación correspondiente.
7. Cerrar sesión. Confirmar redirección a la portada y estado anónimo al recargar. Repetir después de caducar la sesión.
8. Alternar dos usuarios en sesiones independientes y comprobar que cada navbar muestra la identidad correspondiente.

El cierre de la issue y el merge quedan pendientes de la validación del usuario.
