package com.bcp.workshop.auth;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.inject.Inject;
import jakarta.inject.Singleton;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

@Singleton
public class JwtTokenIssuer {
    public static final long TOKEN_LIFETIME_SECONDS = 3600;

    private static final String HEADER_JSON = "{\"alg\":\"RS256\",\"typ\":\"JWT\"}";
    private static final String SIGNATURE_ALGORITHM = "SHA256withRSA";
    private static final String KEY_ALGORITHM = "RSA";

    private final PrivateKey privateKey;
    private final String issuer;
    private final String audience;
    private final ObjectMapper objectMapper;

    @Inject
    public JwtTokenIssuer(
            @ConfigProperty(name = "auth.jwt.private-key-path") String privateKeyPath,
            @ConfigProperty(name = "auth.jwt.issuer") String issuer,
            @ConfigProperty(name = "auth.jwt.audience") String audience,
            ObjectMapper objectMapper) {
        this.privateKey = loadPrivateKey(Path.of(privateKeyPath));
        this.issuer = issuer;
        this.audience = audience;
        this.objectMapper = objectMapper;
    }

    public String issue(String username, String role) {
        long issuedAt = Instant.now().getEpochSecond();
        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put("iss", issuer);
        claims.put("aud", audience);
        claims.put("sub", username);
        claims.put("role", role);
        claims.put("iat", issuedAt);
        claims.put("exp", issuedAt + TOKEN_LIFETIME_SECONDS);

        String signingInput = encodeSegment(HEADER_JSON.getBytes(StandardCharsets.UTF_8))
                + "." + encodeSegment(serialize(claims));
        return signingInput + "." + encodeSegment(sign(signingInput));
    }

    private byte[] serialize(Map<String, Object> claims) {
        try {
            return objectMapper.writeValueAsBytes(claims);
        } catch (JsonProcessingException error) {
            throw new IllegalStateException("No se pudieron serializar los claims del token", error);
        }
    }

    private byte[] sign(String signingInput) {
        try {
            Signature signature = Signature.getInstance(SIGNATURE_ALGORITHM);
            signature.initSign(privateKey);
            signature.update(signingInput.getBytes(StandardCharsets.US_ASCII));
            return signature.sign();
        } catch (GeneralSecurityException error) {
            throw new IllegalStateException("No se pudo firmar el token", error);
        }
    }

    private static PrivateKey loadPrivateKey(Path path) {
        try {
            String pem = Files.readString(path, StandardCharsets.UTF_8);
            String base64Body = pem.replaceAll("-----[A-Z ]+-----", "").replaceAll("\\s", "");
            byte[] der = Base64.getDecoder().decode(base64Body);
            return KeyFactory.getInstance(KEY_ALGORITHM).generatePrivate(new PKCS8EncodedKeySpec(der));
        } catch (IOException | GeneralSecurityException error) {
            throw new IllegalStateException("No se pudo cargar la clave privada JWT", error);
        }
    }

    private static String encodeSegment(byte[] data) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(data);
    }
}
