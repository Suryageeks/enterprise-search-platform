package com.enterprise.auth.utils;

import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.time.Duration;
import java.util.Date;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.WeakKeyException;
import io.jsonwebtoken.security.Keys;

@Component
public class JwtUtil {

    @Value("${jwtSecret}")
    private String jwtSecret;
    
    @Value("${jwtExpiry}")
    private long jwtExpiry;
    
    public String generateToken(String empId) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + Duration.ofSeconds(jwtExpiry).toMillis());

        return Jwts.builder()
                .setHeaderParam("kid", "auth-hs256")
                .setSubject(empId)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    private Key getSigningKey() {
        try {
            return Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
        } catch (WeakKeyException ex) {
            throw new IllegalStateException("JWT secret must be at least 32 bytes for HS256. Update jwtSecret/JWT_SECRET.", ex);
        }
    }
}
