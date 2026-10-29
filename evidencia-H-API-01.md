# Evidencia H-API-01: token de autenticación RS256

Componentes: `auth/` (emisión) y `api/` (verificación).
Hallazgo: H-API-01, el token Base64 con secreto fijo en código se reemplaza por JWT firmado con RS256.

## Comandos y resultados

| Componente | Comando | Resultado |
|---|---|---|
| api | `& .\.venv\Scripts\python.exe -m pytest` (desde `api/`) | 48 passed, 1 failed: `tests/test_api.py::test_rejects_student_reading_trainer_tasks` (H-API-02, preexistente, fuera de alcance); 75 warnings. |
| api | `& .\.venv\Scripts\python.exe -m pytest --cov=app --cov-fail-under=85` (desde `api/`) | 48 passed, 1 failed: `tests/test_api.py::test_rejects_student_reading_trainer_tasks` (H-API-02, preexistente, fuera de alcance); cobertura total 98.55%, gate de 85% alcanzado; 75 warnings. |
| auth | `mvn -B verify` (en `auth/`) | BUILD SUCCESS, 3 pruebas pasan (`AuthResourceTest` x2, `JwtTokenIssuerTest` x1). |

Cobertura JaCoCo de clases modificadas en `auth/`: `JwtTokenIssuer` 29/33 líneas (88%).

La caracterización de H-API-01 confirma que `api/app/main.py` ya exige tokens RS256 firmados, issuer, audience y expiración válidos. No se requirió cambiar código funcional de `api/`; la discrepancia pendiente estaba en las descripciones y ejemplos obsoletos de `docs/ENDPOINTS.md`. El fallo de lectura entre owners corresponde a H-API-02 y permanece fuera de este alcance.

## Pruebas agregadas

- `api/tests/test_jwt_validation.py`: token válido, payload alterado, clave ajena, `alg=none`, emisor o audiencia incorrectos, claims requeridos faltantes, clave no configurada, y ausencia del secreto legado en `app/main.py`.
- `api/tests/test_api.py`: caracterización de `GET /api/tasks` (HTTP 200, orden y campos), `POST /api/tasks` (HTTP 201 y campos persistidos), `GET /api/summary` (campos/conteos), credenciales inválidas y rechazo entre owners (H-API-02 sigue fallando fuera de alcance).
- `auth/src/test/.../AuthResourceTest.java`: login responde 200 con `expiresIn=3600`; el token tiene `alg=RS256`, `iss`, `aud`, `sub`, `role`, `exp-iat=3600` y firma verificable con la clave pública.
- `auth/src/test/.../JwtTokenIssuerTest.java`: falla al arrancar si la clave privada no existe.

## Pendientes

- No se ejecutó el flujo completo web (login y dashboard) con servicios levantados.
- Los valores de `AUTH_JWT_PRIVATE_KEY_PATH` y `AUTH_JWT_PUBLIC_KEY_PATH` no se validaron en un despliegue real; las pruebas generan claves temporales.
- Issuer `workshop-auth` y audiencia `workshop-api` son valores por defecto no confirmados por el usuario.

No se incluyen tokens, claves ni secretos en este archivo.
