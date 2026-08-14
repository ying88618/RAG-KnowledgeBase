package com.example.springboot.Controller;

import com.example.springboot.Service.AgentService;
import com.example.springboot.pojo.ChatRequest;
import com.example.springboot.utils.ThreadLocalUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

import java.util.Map;

@RestController
@RequestMapping("/chat")
public class AgentController {
    @Autowired
    private AgentService agentService;

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> stream(@RequestBody ChatRequest chatRequest) {
        Map<String, Object> claims = ThreadLocalUtil.getThreadLocal();
        Integer userId = (Integer) claims.get("id");
        return agentService.chatStream(
                chatRequest.getSessionId(),
                userId,
                chatRequest.getQuestion(),
                chatRequest.getCollectionName()
        );
    }
}
