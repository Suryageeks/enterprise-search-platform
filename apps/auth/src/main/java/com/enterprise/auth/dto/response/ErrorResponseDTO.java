package com.enterprise.auth.dto.response;

import java.time.Instant;

import lombok.Builder;
import lombok.Value;

@Value
@Builder
public class ErrorResponseDTO {
    Instant timestamp;
    int status;
    String error;
    String message;
    String path;
}
