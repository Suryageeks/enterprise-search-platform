package com.enterprise.document.controller;

import java.util.UUID;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.enterprise.document.dto.response.DownloadUrlResponse;
import com.enterprise.document.dto.response.IngestionUploadResponse;
import com.enterprise.document.services.DocumentService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/document")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<IngestionUploadResponse> uploadFile(
        @RequestParam String empId,
        @RequestParam("file") MultipartFile file
    ){
        return ResponseEntity.ok(documentService.uploadFile(empId, "AWS S3", file));
    }


    @GetMapping("/download-url/{docId}")
    public ResponseEntity<DownloadUrlResponse> getDownloadUrl(
        @PathVariable UUID docId
    ){
        String url = documentService.generateDownloadUrl(docId, java.time.Duration.ofMinutes(10));
        return ResponseEntity.ok(new DownloadUrlResponse(url));
    }
}
