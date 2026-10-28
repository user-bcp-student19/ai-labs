package com.bcp.workshop.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.test.common.QuarkusTestResource;
import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.security.Signature;
import java.util.Base64;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
@QuarkusTestResource(JwtKeyTestResource.class)
class AuthResourceTest {
    private static final String LOGIN_BODY = "{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}";

    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body(LOGIN_BODY)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("expiresIn", is(3600))
                .body("token", notNullValue());
    }

    @Test
    void issuesRs256TokenSignedWithPrivateKeyAndExpectedClaims() throws Exception {
        String token = given()
                .contentType("application/json")
                .body(LOGIN_BODY)
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .extract().path("token");

        String[] segments = token.split("\\.");
        assertEquals(3, segments.length);

        ObjectMapper mapper = new ObjectMapper();
        JsonNode header = mapper.readTree(Base64.getUrlDecoder().decode(segments[0]));
        JsonNode claims = mapper.readTree(Base64.getUrlDecoder().decode(segments[1]));

        assertEquals("RS256", header.get("alg").asText());
        assertEquals("workshop-auth", claims.get("iss").asText());
        assertEquals("workshop-api", claims.get("aud").asText());
        assertEquals("student", claims.get("sub").asText());
        assertTrue(claims.hasNonNull("role"));
        assertEquals(3600, claims.get("exp").asLong() - claims.get("iat").asLong());
        assertTrue(verifySignature(segments[0] + "." + segments[1], segments[2]));
    }

    private boolean verifySignature(String signingInput, String encodedSignature) throws Exception {
        Signature verifier = Signature.getInstance("SHA256withRSA");
        verifier.initVerify(JwtKeyTestResource.keyPair.getPublic());
        verifier.update(signingInput.getBytes(StandardCharsets.US_ASCII));
        return verifier.verify(Base64.getUrlDecoder().decode(encodedSignature));
    }
}
