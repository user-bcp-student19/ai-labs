# Tasks

## 1. Caracterizacion antes del cambio funcional

- [x] 1.1 Ejecutar `mvn -Dtest=AuthResourceTest test` desde `auth/` y confirmar que el login valido conserva `200`, `user.username == student` y un `token` no vacio.
- [x] 1.2 Agregar a `AuthResourceTest` una caracterizacion de credenciales ordinarias no validas; verificar con `mvn -Dtest=AuthResourceTest test` que responde `401` y no devuelve `token` antes de cambiar la consulta.
- [x] 1.3 Agregar casos de regresion para el valor manipulador del Issue en `username` y `password`; ejecutar `mvn -Dtest=AuthResourceTest test` sin cambio funcional y confirmar/documentar que ambos casos reproducen el defecto al obtener acceso (`200` o `token`) en vez del `401` esperado.

## 2. Cambio acotado y validacion

- [x] 2.1 Parametrizar `username` y `password` en la consulta de credenciales de `auth/`; verificar con `mvn -Dtest=AuthResourceTest test` que el login valido sigue respondiendo `200` y ambos casos manipuladores responden `401` sin `token`.
- [x] 2.2 Ejecutar `mvn verify` desde `auth/`; confirmar que pasa la suite completa y se genera el reporte JaCoCo en `auth/target/site/jacoco/`.
- [x] 2.3 Revisar el reporte JaCoCo y confirmar cobertura de al menos 85% para el codigo modificado; revisar el diff de implementacion y pruebas para confirmar que queda limitado a `auth/` y no cambia `api/`, `web/` ni contratos ajenos al Issue #22.