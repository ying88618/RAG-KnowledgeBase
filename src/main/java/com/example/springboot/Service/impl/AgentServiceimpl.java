package com.example.springboot.Service.impl;

import com.example.springboot.Service.AgentService;
import com.example.springboot.utils.BusinessException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;


@Service
public class AgentServiceimpl implements AgentService {

    @Autowired
    private RestClient restClient;

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
}
