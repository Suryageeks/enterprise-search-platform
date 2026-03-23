package com.enterprise.document.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.enterprise.document.entity.Document;

public interface DocumentRepository extends JpaRepository<Document, Integer> {

    Optional<Document> findByDocId(UUID docId);

    List<Document> findByEmpId(String empId);
}
