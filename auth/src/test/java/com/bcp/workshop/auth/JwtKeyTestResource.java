package com.bcp.workshop.auth;

import io.quarkus.test.common.QuarkusTestResourceLifecycleManager;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.Base64;
import java.util.Map;

public class JwtKeyTestResource implements QuarkusTestResourceLifecycleManager {
    static KeyPair keyPair;

    private Path privateKeyFile;

    @Override
    public Map<String, String> start() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
            generator.initialize(2048);
            keyPair = generator.generateKeyPair();
            privateKeyFile = Files.createTempFile("auth-test-jwt", ".pem");
            String body = Base64.getMimeEncoder(64, "\n".getBytes())
                    .encodeToString(keyPair.getPrivate().getEncoded());
            Files.writeString(privateKeyFile, "-----BEGIN PRIVATE KEY-----\n" + body + "\n-----END PRIVATE KEY-----\n");
            return Map.of("auth.jwt.private-key-path", privateKeyFile.toAbsolutePath().toString());
        } catch (Exception error) {
            throw new IllegalStateException("No se pudo generar la clave de prueba", error);
        }
    }

    @Override
    public void stop() {
        try {
            if (privateKeyFile != null) {
                Files.deleteIfExists(privateKeyFile);
            }
        } catch (IOException ignored) {
            // El archivo temporal se elimina en el siguiente reinicio del sistema si falla.
        }
    }
}
