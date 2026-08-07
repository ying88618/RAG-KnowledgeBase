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

        // 填写Object完整路径，完整路径中不能包含Bucket名称，例如exampledir/exampleobject.txt。
        // 填写Bucket所在地域。以华东1（杭州）为例，Region填写为cn-hangzhou。
        // 创建OSSClient实例。
        // 当OSSClient实例不再使用时，调用shutdown方法以释放资源。
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
