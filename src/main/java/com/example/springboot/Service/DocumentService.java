package com.example.springboot.Service;


import com.example.springboot.pojo.Document;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface DocumentService {
    Document create(MultipartFile file);
    List<Document> list();
}
