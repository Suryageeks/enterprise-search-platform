package com.enterprise.document.services;

import java.io.InputStream;
import java.net.URL;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import com.enterprise.document.config.S3Properties;
import com.enterprise.document.dto.response.IngestionUploadResponse;
import com.enterprise.document.entity.Document;
import com.enterprise.document.entity.IngestionJob;
import com.enterprise.document.exception.DocumentNotFoundException;
import com.enterprise.document.exception.FileStorageException;
import com.enterprise.document.repository.DocumentRepository;
import com.enterprise.document.repository.IngestionJobRepository;
import com.enterprise.document.util.fileStatus;

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
    private final IngestionJobRepository ingestionJobRepository;
    private final StringRedisTemplate redisTemplate;

    @Value("${app.redis.stream.ingestion-stream}")
    private String ingestionStreamName;

    public IngestionUploadResponse uploadFile(String empId, String uploadType, MultipartFile file){
        String originalFileName = StringUtils.cleanPath(file.getOriginalFilename());
        UUID docId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        String key = buildS3Key(empId, docId, originalFileName);

        try (InputStream inputStream = file.getInputStream()) {
            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                                            .bucket(s3Properties.getBucketName())
                                            .key(key)
                                            .contentType(file.getContentType())
                                            .contentLength(file.getSize())
                                            .build();

            s3Client.putObject(putObjectRequest, RequestBody.fromInputStream(inputStream, file.getSize()));
            log.info("File {} uploaded to S3 with key {}", originalFileName, key);

            Document savedDocument = documentRepository.save(Document.builder()
                                            .empId(empId)
                                            .docId(docId)
                                            .uploadType(uploadType)
                                            .fileName(originalFileName)
                                            .fileSize(file.getSize())
                                            .fileStatus(fileStatus.QUEUED.name())
                                            .filePath(key)
                                            .updatedAt(LocalDateTime.now())
                                            .build());

            IngestionJob savedIngestionJob = ingestionJobRepository.save(IngestionJob.builder()
                                            .jobId(jobId)
                                            .empId(empId)
                                            .docId(docId)
                                            .fileName(originalFileName)
                                            .status(fileStatus.QUEUED.name())
                                            .streamName(ingestionStreamName)
                                            .build());

            try {
                RecordId recordId = publishToIngestionStream(savedIngestionJob, savedDocument);
                log.info(
                    "Document {} with jobId {} queued for ingestion as Redis record {}",
                    savedDocument.getDocId(),
                    savedIngestionJob.getJobId(),
                    recordId.getValue()
                );
            } catch (Exception redisException) {
                markQueueFailure(savedDocument, savedIngestionJob, redisException);
                throw redisException;
            }

            log.info("File upload and ingestion job creation successful for jobId {}", savedIngestionJob.getJobId());

            return IngestionUploadResponse.builder()
                                        .jobId(savedIngestionJob.getJobId())
                                        .docId(savedDocument.getDocId())
                                        .status(savedIngestionJob.getStatus())
                                        .fileName(savedDocument.getFileName())
                                        .receivedAt(savedIngestionJob.getCreatedAt() != null
                                            ? savedIngestionJob.getCreatedAt()
                                            : OffsetDateTime.now())
                                        .build();

        } catch (Exception e) {
            throw new FileStorageException("Failed to upload file and queue ingestion job", e);
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

    private RecordId publishToIngestionStream(IngestionJob ingestionJob, Document document) {
        Map<String, String> payload = Map.of(
            "jobId", ingestionJob.getJobId().toString(),
            "docId", document.getDocId().toString(),
            "empId", document.getEmpId(),
            "fileName", document.getFileName(),
            "filePath", document.getFilePath(),
            "uploadType", document.getUploadType(),
            "queuedAt", OffsetDateTime.now().toString()
        );

        RecordId recordId = redisTemplate.opsForStream().add(MapRecord.create(ingestionStreamName, payload));
        if (recordId == null) {
            throw new IllegalStateException("Redis stream publish returned null record id");
        }

        log.info("Published ingestion job {} to Redis stream {}", ingestionJob.getJobId(), ingestionStreamName);
        return recordId;
    }

    private void markQueueFailure(Document document, IngestionJob ingestionJob, Exception redisException) {
        document.setFileStatus(fileStatus.QUEUE_FAILED.name());
        ingestionJob.setStatus(fileStatus.QUEUE_FAILED.name());
        ingestionJob.setErrorMessage(redisException.getMessage());

        documentRepository.save(document);
        ingestionJobRepository.save(ingestionJob);

        log.error("Failed to queue ingestion job {} to Redis", ingestionJob.getJobId(), redisException);
    }
}
