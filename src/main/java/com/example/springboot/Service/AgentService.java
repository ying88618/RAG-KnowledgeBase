package com.example.springboot.Service;

public interface AgentService {
    Integer ingestDocument(Long docId,String fileUrl,String fileName,String fileType,String collectionName);
}
