package com.enterprise.document.services;

import java.net.URL;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import com.enterprise.document.config.S3Properties;
import com.enterprise.document.dto.response.DocumentResponse;
import com.enterprise.document.entity.Document;
import com.enterprise.document.entity.IngestionJob;
import com.enterprise.document.exception.DocumentNotFoundException;
import com.enterprise.document.exception.FileStorageException;
import com.enterprise.document.repository.DocumentRepository;
import com.enterprise.document.repository.IngestionJobRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentService {

    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    private final S3Properties s3Properties;
    private final DocumentRepository documentRepository;
    private final IngestionJobRepository ingestionJobService;
    private final StringRedisTemplate redisTemplate;

    @Value("app.redis.stream.ingestion-stream")
    private String ingestionStreamName;

    public DocumentResponse uploadFile(String empId, String uploadType, MultipartFile file){
        try {
            String originalFileName = StringUtils.cleanPath(file.getOriginalFilename());
            UUID docId = UUID.randomUUID();
            UUID jobId = UUID.randomUUID();
            String key = buildS3Key(empId, docId, originalFileName) ;

            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                                                .bucket(s3Properties.getBucketName())
                                                .key(key)
                                                .contentType(file.getContentType())
                                                .contentLength(file.getSize())
                                                .build();

            s3Client.putObject(putObjectRequest,RequestBody.fromBytes(file.getBytes()));

            Document document = Document.builder()
                                .empId(empId)
                                .docId(docId)
                                .uploadType(uploadType)
                                .fileName(originalFileName)
                                .fileSize(file.getSize())
                                .fileStatus("QUEUED")
                                .filePath(key)
                                .updatedAt(LocalDateTime.now())
                                .build();
            
            IngestionJob ingestionJob = IngestionJob.builder()
                                        .jobId(jobId)
                                        .empId(empId)
                                        .docId(docId)
                                        .fileName(originalFileName)
                                        .status("QUEUED")
                                        .streamName(ingestionStreamName)
                                        .build();

            Document saveDocument = documentRepository.save(document);
            IngestionJob saveIngestionJob = ingestionJobService.save(ingestionJob);

            publishToIngestionStream(saveIngestionJob, saveDocument);
            
            return mapToResponse(saveDocument);

        } catch (Exception e) {
            throw new FileStorageException("Failed to upload file to s3", e);
        }
    }

    public String generateDownloadUrl(UUID docId, Duration expiry){
        Document document = documentRepository.findByDocId(docId).orElseThrow(
            () -> new DocumentNotFoundException("Document Not Found "+ docId)
        );

        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                                            .bucket(s3Properties.getBucketName())
                                            .key(document.getFilePath())
                                            .build();
        
        // Presigned Url
        GetObjectPresignRequest getObjectPresignRequest = GetObjectPresignRequest.builder()
                                                            .signatureDuration(expiry)
                                                            .getObjectRequest(getObjectRequest)
                                                            .build();
        
        URL url = s3Presigner.presignGetObject(getObjectPresignRequest).url();
        return url.toString();
    }

    private String buildS3Key(String empId, UUID docId, String fileName){
        return s3Properties.getBaseDir() + "/" + empId + "/" + docId + "/" + fileName;
    }

    private DocumentResponse mapToResponse(Document document) {
        return DocumentResponse.builder()
            .id(document.getId())
            .empId(document.getEmpId())
            .docId(document.getDocId())
            .uploadType(document.getUploadType())
            .fileStatus(document.getFileStatus())
            .fileName(document.getFileName())
            .fileSize(document.getFileSize())
            .filePath(document.getFilePath())
            .createdAt(document.getCreatedAt())
            .build();
    }

    private void publishToIngestionStream(IngestionJob ingestionJob, Document document) {
        Map<String, String> payload = Map.of(
            "jobId", ingestionJob.getJobId().toString(),
            "docId", document.getDocId().toString(),
            "empId", document.getEmpId(),
            "fileName", document.getFileName(),
            "filePath", document.getFilePath(),
            "uploadType", document.getUploadType(),
            "queuedAt", OffsetDateTime.now().toString()
        );

        redisTemplate.opsForStream().add(MapRecord.create(ingestionStreamName, payload));

        log.info("Published ingestion job {} to Redis stream {}", ingestionJob.getJobId(), ingestionStreamName);
    }
}
