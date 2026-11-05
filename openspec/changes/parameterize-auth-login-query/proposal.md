# Proposal

## Why

El Issue [#22](https://github.com/user-bcp-student19/ai-labs/issues/22), asociado al hallazgo `H-AUTH-01`, informa que ciertos valores de credenciales pueden alterar la consulta de autenticación y permitir un inicio de sesión no autorizado. Corregirlo es importante porque una entrada de login no debe poder sustituir la verificación de credenciales.

## What Changes

### Dentro del alcance
- Rechazar como credenciales inválidas los valores manipuladores recibidos en `username` o `password`, respondiendo `401` sin emitir un token.
- Preservar el resultado observable del login válido: `200`, `user.username` y `token`.
- Definir escenarios verificables para el login válido y los intentos manipuladores en ambos campos.

### Fuera del alcance
- Cambios a rutas, formatos de respuesta o autenticación de `api/` y `web/`.
- Cambios en el repositorio, título o descripción del Issue #22.
- Refactorizaciones generales, cambios de formato del token o nuevos requisitos de credenciales.
- Decisiones sobre la implementación técnica.

El contrato publicado en `docs/ENDPOINTS.md` describe el uso del token de auth por parte de `api/`, pero no documenta directamente `POST /auth/login`. Por ello, la compatibilidad del login se contrasta con el comportamiento comprometido en el Issue #22 y el escenario existente de login válido: `200` con `user.username` y `token`. Rechazar entradas que intentan evitar la comprobación de credenciales no cambia ese contrato válido; concreta el resultado esperado para intentos inválidos que el Issue busca corregir.

## Capabilities

### New Capabilities
- `auth-login`: comportamiento observable del inicio de sesión y rechazo de credenciales inválidas.

### Modified Capabilities
- Ninguna.

## Impact

- Componente afectado: `auth/`.
- Interfaz observable: `POST /auth/login`; se preserva el éxito de credenciales válidas y se exige `401` sin `token` para los valores manipuladores descritos en el Issue.
- Fuente de alcance: Issue #22, `H-AUTH-01`.
- Sin impacto planificado en los endpoints documentados de `api/` ni en `web/`.