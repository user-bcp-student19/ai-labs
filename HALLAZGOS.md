# HU-01 - Token firmado con expiracion y claims minimos

## Veredicto
**Usable con ajustes.** La historia conecta seguridad, configuracion, testing y evidencia.

## Contexto
El servicio de autenticacion expone `POST /auth/login` y devuelve `token`, `expiresIn` y `user`. La implementacion usa firma HMAC y lee `AUTH_TOKEN_SECRET`.

## Ajustes necesarios
- Exigir los claims `sub`, `client`, `iat` y `exp`.
- Obtener `client` desde la solicitud, validarlo y reflejarlo en el token.
- Comprobar que `expiresIn` coincide con `exp - now` usando una tolerancia documentada.
- Eliminar el secreto por defecto fuera del laboratorio o documentarlo como exclusivo de laboratorio.
- Evitar logs del token y del secreto.
- Mantener como decision tecnica si se conserva HMAC o se adopta una libreria JWT.

## Criterios de aceptacion
- Un token valido contiene `sub`, `client`, `iat` y `exp`.
- `expiresIn` es coherente con `exp - now` dentro de la tolerancia definida.
- Login valido, credenciales invalidas y token expirado tienen pruebas.
- No se registran tokens, secretos ni valores sensibles.
- La decision sobre HMAC frente a una libreria JWT queda documentada.

## Evidencia esperada
- Documento generado por los Skills a partir de este archivo.
- Pruebas de claims, expiracion y errores de autenticacion.
- Configuracion documentada de `AUTH_TOKEN_SECRET`.
- Evidencia de logs redactados.

## Discovery de api — candidatos

### H-API-08 — `/api/backend-health` expone el cuerpo de respuesta y detalles de error del servicio upstream
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:157,160-163`; `api/tests/test_api.py:277-298` comprueba que el detalle de una excepción se devuelve en el cuerpo.
- Impacto: un usuario autenticado puede recibir información de diagnóstico del servicio dependiente que podría revelar detalles internos; no se ha verificado que el cuerpo real contenga datos sensibles.
- Prioridad propuesta: Media, pendiente de confirmar qué información devuelve el servicio dependiente y quién debe consumirla.
- Contrato potencialmente afectado: respuesta de `GET /api/backend-health`, en particular los campos `status` y `body`.
- Cómo validarlo: probar respuestas y errores representativos del servicio dependiente y comprobar si la respuesta pública revela detalles que el contrato acordado considere internos; definir y probar el comportamiento público esperado.

### H-API-09 — Las cargas con el mismo nombre comparten destino y pueden sobrescribirse
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:141-148` construye el destino con el nombre validado y escribe con `write_bytes`; `api/tests/test_api.py:387-404` verifica el almacenamiento bajo un nombre fijo.
- Impacto: una carga posterior con el mismo nombre puede reemplazar el contenido anterior en el directorio compartido, afectando la integridad o disponibilidad del archivo para otros usuarios autenticados.
- Prioridad propuesta: Media, sujeta a confirmar si sobrescribir archivos con nombre coincidente es el comportamiento esperado.
- Contrato potencialmente afectado: `POST /api/requirements`, su política de colisiones y los campos `fileName` y `storedAt` de la respuesta.
- Cómo validarlo: cargar dos contenidos con el mismo nombre bajo identidades distintas y verificar el comportamiento actual; acordar la política de colisión y añadir una prueba que compruebe el resultado esperado.

### H-API-10 — La política CORS permite cualquier origen con credenciales
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:68-74` configura `allow_origins=["*"]` junto con `allow_credentials=True`.
- Impacto: amplía a cualquier origen el acceso CORS con credenciales del navegador; el impacto concreto depende de los mecanismos de credenciales utilizados por el frontend y no se confirma en este hallazgo.
- Prioridad propuesta: Media, pendiente de contrastar con los orígenes y mecanismos de autenticación autorizados.
- Contrato potencialmente afectado: política de acceso cross-origin de los endpoints de la API.
- Cómo validarlo: enviar solicitudes preflight y solicitudes con `Origin` de orígenes permitidos y no permitidos; comparar los encabezados de respuesta con la política acordada y los requisitos del frontend.