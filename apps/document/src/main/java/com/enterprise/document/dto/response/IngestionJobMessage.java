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
public class IngestionJobMessage {
    private UUID jobId;
    private UUID docId;
    private String empId;
    private String fileName;
    private String filePath;
    private String uploadType;
    private OffsetDateTime queuedAt;
}
