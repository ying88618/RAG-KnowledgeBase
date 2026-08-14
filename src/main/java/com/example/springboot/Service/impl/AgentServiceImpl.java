package com.example.springboot.Service.impl;

import com.example.springboot.Service.AgentService;
import com.example.springboot.utils.BusinessException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.util.Map;


@Service
public class AgentServiceImpl implements AgentService {

    @Autowired
    private RestClient restClient;

    @Autowired
    private WebClient webClient;

    @Override
    public Integer ingestDocument(Long docId, String fileUrl, String fileName, String fileType, String collectionName) {
        try {
            Map<String, Object> body = Map.of(
                    "doc_id", docId,
                    "file_url", fileUrl,
                    "file_name", fileName,
                    "file_type", fileType,
                    "collection_name", collectionName
            );
            Map response = restClient.post()
                    .uri("documents/ingest")
                    .body(body)
                    .retrieve()
                    .body(Map.class);
            if (response != null && Boolean.TRUE.equals(response.get("success"))) {
                return (Integer) response.get("chunk_count");
            }
            return null;
        } catch (Exception e) {
            throw new BusinessException("调用python文档入库失败：" + e.getMessage());
        }
    }

    @Override
    public Flux<ServerSentEvent<String>> chatStream(String sessionId, Integer userId, String question, String collectionName) {
        Map<String, Object> body = Map.of(
                "session_id", sessionId,
                "user_id", userId,
                "question", question,
                "collection_name", collectionName
        );
        return webClient.post()
                .uri("chat/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(body)
                .retrieve()
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {
                })
                .onErrorResume(e -> {
                    return Flux.just(ServerSentEvent.<String>builder()
                            .event("error")
                            .data("调用python接口失败：" + e.getMessage())
                            .build());
                });
    }
}
