package com.enterprise.document.dto.response;

import java.time.OffsetDateTime;
import java.util.UUID;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IngestionUploadResponse {
    private UUID jobId;
    private UUID docId;
    private String status;
    private String fileName;
    private OffsetDateTime receivedAt;
}
