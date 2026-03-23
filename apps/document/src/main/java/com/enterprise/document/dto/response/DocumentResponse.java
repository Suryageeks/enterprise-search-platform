package com.enterprise.document.dto.response;

import java.time.OffsetDateTime;
import java.util.UUID;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class DocumentResponse {
    private Integer id;
    private String empId;
    private UUID docId;
    private String uploadType;
    private String fileStatus;
    private String fileName;
    private Long fileSize;
    private String filePath;
    private OffsetDateTime createdAt;
}
