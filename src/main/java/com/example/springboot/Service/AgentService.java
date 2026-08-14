package com.example.springboot.Service;

import org.springframework.http.codec.ServerSentEvent;
import reactor.core.publisher.Flux;

public interface AgentService {
    Integer ingestDocument(Long docId,String fileUrl,String fileName,String fileType,String collectionName);

    Flux<ServerSentEvent<String>> chatStream(String sessionId,Integer userId,String question,String collectionName);

}
