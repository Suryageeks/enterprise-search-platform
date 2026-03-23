package com.enterprise.document.exception;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(DocumentNotFoundException.class)
    public ResponseEntity<Map<String, String>> handleDocumentException(DocumentNotFoundException ex){
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                            .body(Map.of("message",ex.getMessage()));
    }

    @ExceptionHandler(FileStorageException.class)
    public ResponseEntity<Map<String, String>> handleFileStorageException(FileStorageException ex){
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(Map.of("message",ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, String>> handleGenericException(Exception ex){
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(Map.of("message",ex.getMessage()));
    }
}
