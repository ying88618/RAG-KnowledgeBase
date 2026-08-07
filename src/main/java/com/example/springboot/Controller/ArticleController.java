package com.example.springboot.Controller;

import com.example.springboot.Service.ArticleService;
import com.example.springboot.pojo.Article;
import com.example.springboot.pojo.PageBean;
import com.example.springboot.pojo.Result;
import com.example.springboot.utils.JwtUtil;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/article")
public class ArticleController {

    @Autowired
    private ArticleService articleService;

    @GetMapping("/list")
    //验证token
    public Result<String> list() {
//        try {
//            Map<String,Object> claims = JwtUtil.parseToken(token);
//            return Result.success("所有文章数据");
//        } catch (Exception e) {
//            return Result.error("未登录");
//        }
        return Result.success("所有文章数据");
    }

    @PostMapping("/add")
    public Result add(@RequestBody @Validated Article article) {
        articleService.add(article);
        return Result.success();
    }

    @GetMapping("/pagelist")
    public Result<PageBean<Article>> list(
            Integer pageNum,
            Integer pageSize,
            @RequestParam(required = false) Integer categoryId,
            @RequestParam(required = false) String state
    ) {
        PageBean<Article> pd = articleService.list(pageNum, pageSize, categoryId);
        return Result.success(pd);
    }

    @GetMapping("/detail")
    public Result<Article> detail(Integer articleId) {
        Article article = articleService.detail(articleId);
        return Result.success(article);
    }

    @PostMapping("/update")
    public Result update(@RequestBody @Validated Article article){
        articleService.update(article);
        return Result.success();
    }

    @DeleteMapping("/delete")
    public Result delete(Integer articleId){
        articleService.delete(articleId);
        return Result.success();
    }

    @GetMapping("/search")
    public Result<List<Article>> search(String halftitle){
        List<Article> articles = articleService.search(halftitle);
        return Result.success(articles);
    }
}
