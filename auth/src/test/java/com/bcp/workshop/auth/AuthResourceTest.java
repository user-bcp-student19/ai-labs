package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@QuarkusTest
class AuthResourceTest {
    private static final String LOGIN_PATH = "/auth/login";
    private static final String CLIENT = "angular-workshop";
    private static final String WORKSHOP_USER = "student";
    private static final String WORKSHOP_PASSWORD = "Workshop123!";
    private static final String WRONG_PASSWORD = "not-the-password";
    private static final String MANIPULATIVE_VALUE = "' OR '1'='1";

    @Test
    void logsInWithWorkshopUser() {
        loginWith(WORKSHOP_USER, WORKSHOP_PASSWORD)
                .statusCode(200)
                .body("user.username", is(WORKSHOP_USER))
                .body("token", notNullValue());
    }

    // Caracterización 1.2: credenciales ordinarias inválidas ya responden 401 sin token.
    @Test
    void rejectsOrdinaryInvalidCredentials() {
        loginWith(WORKSHOP_USER, WRONG_PASSWORD)
                .statusCode(401)
                .body("token", nullValue());
    }

    // Regresión 1.3 (spec: manipulative value in username); falla hasta parametrizar la consulta.
    @Test
    void rejectsManipulativeUsername() {
        loginWith(MANIPULATIVE_VALUE, WORKSHOP_PASSWORD)
                .statusCode(401)
                .body("token", nullValue());
    }

    // Regresión 1.3 (spec: manipulative value in password); falla hasta parametrizar la consulta.
    @Test
    void rejectsManipulativePassword() {
        loginWith(WORKSHOP_USER, MANIPULATIVE_VALUE)
                .statusCode(401)
                .body("token", nullValue());
    }

    private static ValidatableResponse loginWith(String username, String password) {
        return given()
                .contentType("application/json")
                .body(String.format("{\"username\":\"%s\",\"password\":\"%s\",\"client\":\"%s\"}", username, password, CLIENT))
                .when().post(LOGIN_PATH)
                .then();
    }
}
