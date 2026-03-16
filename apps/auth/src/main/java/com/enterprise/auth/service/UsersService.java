package com.enterprise.auth.service;

import com.enterprise.auth.dto.request.LoginRequestDTO;
import com.enterprise.auth.dto.response.LoginResponseDTO;

import reactor.core.publisher.Mono;

public interface UsersService {
    Mono<LoginResponseDTO> login(LoginRequestDTO request);
}
