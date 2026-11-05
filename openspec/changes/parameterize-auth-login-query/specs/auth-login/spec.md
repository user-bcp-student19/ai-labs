# Spec Delta

## Purpose

Define el comportamiento observable del inicio de sesión para preservar el acceso válido y rechazar credenciales que intenten eludir la autenticación.

## ADDED Requirements

### Requirement: Valid login remains compatible
The login endpoint MUST preserve the successful response for valid workshop credentials.

#### Scenario: Successful login with valid credentials
- **WHEN** a client sends `POST /auth/login` with JSON credentials `student` and `Workshop123!`
- **THEN** the response status is `200` and the response contains `user.username` equal to `student` and a non-empty `token`

### Requirement: Credential input cannot bypass authentication
The login endpoint MUST reject credential values that attempt to alter the authentication decision.

#### Scenario: Manipulative value in username
- **WHEN** a client sends `POST /auth/login` with `' OR '1'='1` as the username
- **THEN** the response status is `401` and the response contains no `token`

#### Scenario: Manipulative value in password
- **WHEN** a client sends `POST /auth/login` with `' OR '1'='1` as the password
- **THEN** the response status is `401` and the response contains no `token`