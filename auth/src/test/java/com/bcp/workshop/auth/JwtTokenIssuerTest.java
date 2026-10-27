package com.bcp.workshop.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertThrows;

class JwtTokenIssuerTest {
    @Test
    void failsFastWhenPrivateKeyFileDoesNotExist() {
        Path missingKey = Path.of("no-existe", "jwt-private.pem");

        assertThrows(IllegalStateException.class,
                () -> new JwtTokenIssuer(missingKey.toString(), "workshop-auth", "workshop-api", new ObjectMapper()));
    }
}
