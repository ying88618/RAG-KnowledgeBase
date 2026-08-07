package com.example.springboot.pojo;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Document {
    @TableId(type = IdType.AUTO)
    private Long id;
    @NotEmpty
    private String title;
    @NotEmpty
    private String fileName;
    @NotEmpty
    private String fileUrl;
    private String fileType;
    private Long fileSize;
    private Integer status;
    private String collectionName;
    private Integer chunkCount;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
