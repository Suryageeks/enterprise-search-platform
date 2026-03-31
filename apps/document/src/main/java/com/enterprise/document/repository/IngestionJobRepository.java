package com.enterprise.document.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.enterprise.document.entity.IngestionJob;

public interface IngestionJobRepository extends JpaRepository<IngestionJob, Integer> {

    Optional<IngestionJob> findByJobId(UUID jobId);

    List<IngestionJob> findByEmpId(String empId);

    List<IngestionJob> findByDocId(UUID docId);
}
