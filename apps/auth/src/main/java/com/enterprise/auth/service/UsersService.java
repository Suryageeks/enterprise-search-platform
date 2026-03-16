package com.enterprise.auth.service;

import com.enterprise.auth.dto.request.LoginRequestDTO;

import reactor.core.publisher.Mono;

public interface UsersService {
    Mono<String> login(LoginRequestDTO request);
}
