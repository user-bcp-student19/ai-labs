# Design

## Context

See `proposal.md` for the motivation and scope, and `specs/auth-login/spec.md` for the required observable behavior.

The affected flow is contained in `auth/`: `AuthResource.login` validates the JSON request, delegates credential lookup to `LegacyDatabase.findByCredentials`, returns `401` when no user is found, and returns `200` with a token and user data on success. The current `LegacyDatabase` query incorporates both credential strings into SQL text. `AuthResourceTest` currently characterizes only a successful login with the seeded workshop user.

`docs/ENDPOINTS.md` documents that `api/` consumes a Bearer token returned by auth, but it does not define `POST /auth/login` directly. The protected login behavior therefore comes from Issue #22 and the existing auth test. The issue explicitly requires parameterized credential values; this design does not change the token or response contract.

## Goals / Non-Goals

**Goals:**
- Prevent username or password input from changing the credential lookup decision.
- Preserve the existing successful login response and the endpoint's mapping of unmatched credentials to `401`.
- Keep the change and its tests within `auth/`.

**Non-Goals:**
- Redesigning authentication layers or changing `AuthResource` request validation and response construction.
- Changing token format, token lifetime, password storage, or credential policy.
- Modifying `api/`, `web/`, or the general endpoint documentation.

## Contracts Protected

- `POST /auth/login` continues to accept the current JSON request shape and preserve its existing validation responses.
- Valid workshop credentials continue to return `200`, `user.username`, and a non-empty `token`; other existing success fields are not intentionally changed.
- Unmatched credentials continue to return `401` without a token.
- The `api/` Bearer-token flow remains unchanged; no token format or authentication contract for downstream endpoints is changed.
- The new rejection behavior is limited to the Issue #22 requirement: manipulative values in either credential field return `401` without a token.

## Components Affected

- `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`: the credential lookup is the security-critical decision point.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: characterization and endpoint-level regression coverage.
- `AuthResource` is an observed contract boundary, not a planned change; its request validation, response mapping, and token creation remain untouched unless implementation evidence shows this is unavoidable. Any such scope change requires review before proceeding.

No files in `api/`, `web/`, or general documentation are in scope.

## Decisions

1. **Bind both credential values as query parameters.** The issue explicitly requires `PreparedStatement` parameters for username and password. This keeps credential values as data while preserving the existing lookup predicate and returned user fields. Manual escaping, string filtering, or a denylist were rejected because they are fragile and do not reliably preserve the security boundary. Reworking the auth architecture is unnecessary for this bounded change.
2. **Verify behavior at the login endpoint.** Keep the existing Quarkus endpoint test as the compatibility baseline and add separate regression scenarios for a manipulative username and password. A repository-only test would not verify the required HTTP statuses or the absence of a token in the response.
3. **Keep response behavior outside the changed decision unchanged.** Preserve `AuthResource`'s successful response generation and the existing unmatched-credentials status. Changing messages, token contents, or response fields was rejected as unrelated to Issue #22.

## Incremental Strategy

1. Before changing the credential lookup, run and retain the current successful-login characterization: status `200`, `user.username == student`, and a non-empty `token`. Add or confirm characterization for ordinary unmatched credentials returning `401` without a token. Run `mvn test` from `auth/` to establish the baseline.
2. Add endpoint-level regression tests for the Issue's manipulative value in `username` and in `password`, each requiring `401` and no `token`. Run them against the unchanged behavior and record the expected failure as evidence of the defect; do not weaken the expected outcome to make the baseline pass.
3. Make the smallest change at the credential lookup boundary, parameterizing both supplied values while leaving request validation, response generation, token creation, and other components unchanged.
4. Run `mvn test` from `auth/`; confirm the valid-login characterization and both regression cases pass together. Review the diff to confirm only `auth/` implementation and tests changed.

Tests must use deterministic workshop credentials and avoid dependence on stale shared SQLite state. Prefer the test harness's isolated database configuration; if unavailable, establish controlled test data without changing the production/default database.

## Risks / Trade-offs

- **A shared SQLite database can make login tests order-dependent.** Use an isolated test database or a controlled fixture and verify the seeded workshop user before asserting behavior.
- **The pre-fix injection regression tests are expected to fail.** Keep them scoped to the test environment, capture the failing baseline, and do not use production credentials or data.
- **The current `401` message includes the submitted username.** The spec requires no token, not a new error-body contract. Preserve the message in this change to avoid scope expansion; treat any separate output-encoding or disclosure concern as follow-up work.
- **A regression in the normal login flow would block release.** The valid-login characterization must remain green alongside the new rejection tests; do not trade away the existing successful-login contract.

## Rollback

If the change breaks valid logins, stop rollout and revert only the isolated credential-lookup change while retaining the characterization and regression tests. Reverting reopens the Issue #22 vulnerability, so it is a temporary recovery measure, not an acceptable final state; resolve forward before release whenever possible. No database migration or downstream API rollback is expected.