package com.enterprise.auth.service.impl;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import com.enterprise.auth.dto.request.LoginRequestDTO;
import com.enterprise.auth.dto.response.LoginResponseDTO;
import com.enterprise.auth.entity.Users;
import com.enterprise.auth.repository.UsersRepository;
import com.enterprise.auth.service.UsersService;
import com.enterprise.auth.utils.JwtUtil;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
@Slf4j
@RequiredArgsConstructor
public class UsersServiceImpl implements UsersService {

    private final UsersRepository usersRepository;
    private final JwtUtil jwtUtil;

    @Override
    public Mono<LoginResponseDTO> login(LoginRequestDTO request) {
        return Mono.fromCallable(() -> usersRepository.findByEmpId(request.getEmpId()))
                .subscribeOn(Schedulers.boundedElastic())
                .flatMap(Mono::justOrEmpty)
                .switchIfEmpty(Mono.error(new ResponseStatusException(
                        HttpStatus.UNAUTHORIZED,
                        "Invalid empId or password")))
                .flatMap(user -> validateAndGenerateToken(user, request));
    }

    private Mono<LoginResponseDTO> validateAndGenerateToken(Users user, LoginRequestDTO requestDTO) {
        if (user.getIsActive() != '1') {
            return Mono.error(new ResponseStatusException(HttpStatus.FORBIDDEN, "EmpId not active"));
        }
        if (!requestDTO.getPassword().equals(user.getPassword())) {
            return Mono.error(new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid empId or password"));
        }
        String token = jwtUtil.generateToken(user.getEmpId());
        return Mono.just(new LoginResponseDTO(token));
    }
}
