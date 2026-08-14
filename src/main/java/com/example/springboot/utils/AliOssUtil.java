package com.example.springboot.utils;

import com.aliyun.oss.*;
import com.aliyun.oss.common.auth.DefaultCredentialProvider;
import com.aliyun.oss.common.comm.SignVersion;
import com.aliyun.oss.model.PutObjectRequest;
import com.aliyun.oss.model.PutObjectResult;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.InputStream;

@Component
public class AliOssUtil {

    private String endpoint;
    private String accessKeyId;
    private String accessKeySecret;
    private String bucketName;
    private String region;
    private OSS ossClient;

    public AliOssUtil(
            @Value("${aliyun.oss.endpoint}") String endpoint,
            @Value("${aliyun.oss.access-key-id}") String accessKeyId,
            @Value("${aliyun.oss.access-key-secret}") String accessKeySecret,
            @Value("${aliyun.oss.bucket-name}") String bucketName,
            @Value("${aliyun.oss.region}") String region) {
        this.endpoint = endpoint;
        this.accessKeyId = accessKeyId;
        this.accessKeySecret = accessKeySecret;
        this.bucketName = bucketName;
        this.region = region;
    }

    @PostConstruct
    private void init() {

        ClientBuilderConfiguration clientBuilderConfiguration = new ClientBuilderConfiguration();
        clientBuilderConfiguration.setSignatureVersion(SignVersion.V4);
        this.ossClient = OSSClientBuilder.create()
                .endpoint(endpoint)
                .credentialsProvider(new DefaultCredentialProvider(accessKeyId, accessKeySecret))
                .clientConfiguration(clientBuilderConfiguration)
                .region(region)
                .build();
    }


    public String uploadFile(String objectName, InputStream in) throws Exception {
        String url = "";

        PutObjectRequest putObjectRequest = new PutObjectRequest(bucketName, objectName, in);

        // 上传字符串。
        PutObjectResult result = ossClient.putObject(putObjectRequest);
        String endpointHost = endpoint.substring(endpoint.lastIndexOf("/") + 1);
        url = "https://" + bucketName + "." + endpointHost + "/" + objectName;
        return url;
    }

    @PreDestroy
    public void destroy() {
        if (ossClient != null) {
            ossClient.shutdown();
        }
    }
}
