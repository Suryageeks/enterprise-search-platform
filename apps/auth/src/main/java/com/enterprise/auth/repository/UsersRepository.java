package com.enterprise.auth.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.enterprise.auth.entity.Users;

@Repository
public interface UsersRepository extends JpaRepository<Users,Long>{
    Users findByEmpId(String empId);
}
