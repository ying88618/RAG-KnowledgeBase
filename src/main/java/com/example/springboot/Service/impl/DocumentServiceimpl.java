package com.example.springboot.Service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.springboot.Service.AgentService;
import com.example.springboot.Service.DocumentService;
import com.example.springboot.mapper.DocumentMapper;
import com.example.springboot.pojo.Document;
import com.example.springboot.utils.AliOssUtil;
import com.example.springboot.utils.BusinessException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class DocumentServiceimpl extends ServiceImpl<DocumentMapper, Document> implements DocumentService {

    @Autowired
    private AliOssUtil aliOssUtil;

    @Autowired
    private AgentService agentService;

    @Override
    public Document create(MultipartFile file) {
        try {
            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            String objectName = "documents/" + UUID.randomUUID().toString().replace("-", "") + extension;
            String fileUrl = aliOssUtil.uploadFile(objectName, file.getInputStream());
            Document document = new Document();
            document.setTitle(originalFilename);
            document.setFileName(originalFilename);
            document.setFileUrl(fileUrl);
            document.setFileType(extension.replace(".", ""));
            document.setFileSize((long) file.getSize());
            document.setStatus(0);
            document.setCollectionName("kb_default");
            document.setCreateTime(LocalDateTime.now());
            document.setUpdateTime(LocalDateTime.now());
            baseMapper.insert(document);
            Integer chunkCount = agentService.ingestDocument(
                    document.getId(),
                    document.getFileUrl(),
                    document.getFileName(),
                    document.getFileType(),
                    document.getCollectionName()
            );
            if (chunkCount != null) {
                document.setChunkCount(chunkCount);
                document.setStatus(1);
            } else {
                document.setStatus(2);
            }
            document.setUpdateTime(LocalDateTime.now());
            baseMapper.updateById(document);
            return document;
        } catch (Exception e) {
            throw new BusinessException(e.getMessage());
        }
    }

    @Override
    public List<Document> list() {
        return baseMapper.selectList(null);
    }

}
