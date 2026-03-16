package com.enterprise.auth.controller;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.enterprise.auth.dto.request.LoginRequestDTO;
import com.enterprise.auth.dto.response.LoginResponseDTO;
import com.enterprise.auth.service.UsersService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

@RestController
@RequiredArgsConstructor
@Slf4j
@RequestMapping("/auth")
@Validated
@Tag(name = "Authentication", description = "Authentication endpoints for enterprise users")
public class AuthController {

    private final UsersService usersService;

    @PostMapping("/login")
    @Operation(
        summary = "Authenticate user",
        description = "Validates the employee ID and password, then returns a JWT token when authentication succeeds."
    )
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Login successful",
            content = @Content(
                mediaType = "application/json",
                schema = @Schema(implementation = String.class),
                examples = @ExampleObject(value = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJFTVAwMDEiLCJpYXQiOjE3MDAwMDAwMDAsImV4cCI6MTcwMDAwMzYwMH0.signature")
            )
        ),
        @ApiResponse(responseCode = "400", description = "Invalid request payload"),
        @ApiResponse(responseCode = "401", description = "Invalid employee ID or password"),
        @ApiResponse(responseCode = "403", description = "Employee is not active")
    })
    public Mono<LoginResponseDTO> login(
        @Valid @RequestBody LoginRequestDTO requestDTO
    ) {
        return usersService.login(requestDTO);
    }
}
