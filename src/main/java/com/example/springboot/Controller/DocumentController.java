package com.example.springboot.Controller;

import com.example.springboot.Service.DocumentService;
import com.example.springboot.pojo.Document;
import com.example.springboot.pojo.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/document")
public class DocumentController {
    @Autowired
    private DocumentService documentService;

    @PostMapping("/upload")
    public Result<Document> upload(@RequestParam("file") MultipartFile file,String collectionName) {
        return Result.success(documentService.create(file,collectionName));
    }

    @GetMapping("/list")
    public Result<List<Document>> list() {
        return Result.success(documentService.list());
    }
}
