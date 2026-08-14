package com.example.springboot.pojo;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ChatRequest {
    @NotNull
    private String sessionId;
    @NotEmpty
    private String question;
    private String collectionName;
}
