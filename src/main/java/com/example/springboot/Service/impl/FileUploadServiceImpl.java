package com.example.springboot.Service.impl;

import com.example.springboot.Service.FileUploadService;
import com.example.springboot.utils.AliOssUtil;
import com.example.springboot.utils.BusinessException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.UUID;

@Service
public class FileUploadServiceImpl implements FileUploadService {

    @Autowired
    private AliOssUtil aliOssUtil;

    @Override
    public String upload(MultipartFile file) {
        String originalFilename = file.getOriginalFilename();
        String safefilename = new File(originalFilename).getName();
        String ext = "";
        String url = "";
        int dotIndex = safefilename.lastIndexOf(".");
        if (dotIndex != -1) {
            ext = safefilename.substring(dotIndex);
        }
        String uuidFilename = UUID.randomUUID().toString() + ext;
        try {
            url = aliOssUtil.uploadFile(uuidFilename, file.getInputStream());
        } catch (Exception e) {
            throw new BusinessException(e.getMessage());
        }
        return url;
    }
}
