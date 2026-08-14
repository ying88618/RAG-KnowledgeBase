package com.example.springboot.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.springboot.Service.ArticleService;
import com.example.springboot.mapper.ArticleMapper;
import com.example.springboot.mapper.CategoryMapper;
import com.example.springboot.pojo.Article;
import com.example.springboot.pojo.Category;
import com.example.springboot.pojo.PageBean;
import com.example.springboot.utils.BusinessException;
import com.example.springboot.utils.ThreadLocalUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class ArticleServiceImpl extends ServiceImpl<ArticleMapper, Article> implements ArticleService {

    @Autowired
    private ArticleMapper articleMapper;
    @Autowired
    private CategoryMapper categoryMapper;

    @Override
    public void add(Article article) {
        Integer categoryid = article.getCategoryId();
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getId, categoryid));
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer userid = (Integer) map.get("id");
        if (count == 0) {
            log.error("新增文章失败 - 该分类不存在 - categoryid:{}", categoryid);
            throw new BusinessException("该分类不存在");
        }
        article.setCreateUser(userid);
        articleMapper.insert(article);
        log.info("新增文章成功 - article:{},userid:{},title:{}", article, userid, article.getTitle());
    }

    @Override
    public PageBean<Article> list(Integer pageNum, Integer pageSize, Integer categoryId) {
        log.debug("文章列表查询 - pageNum:{},pageSize:{},categoryId:{}", pageNum, pageSize, categoryId);
        PageBean<Article> pb = new PageBean<>();
        Page<Article> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Article> wrapper = new LambdaQueryWrapper<>();
        wrapper.select(Article::getId, Article::getTitle, Article::getCategoryId, Article::getCreateTime, Article::getCreateUser, Article::getCoverImg)
                .eq(categoryId != null, Article::getCategoryId, categoryId)
                .eq(Article::getState, "已发布")
                .orderByDesc(Article::getCreateTime);
        Page<Article> result = articleMapper.selectPage(page, wrapper);
        pb.setTotal(result.getTotal());
        pb.setItems(result.getRecords());
        log.debug("文章列表查询成功 - pageNum:{},pageSize:{},total:{}", pageNum, pageSize, pb.getTotal());
        return pb;
    }

    @Override
    public Article detail(Integer articleId) {
        Article article = articleMapper.selectById(articleId);
        if (article == null) {
            log.error("文章详情查询失败 - 该文章不存在 - articleId:{}", articleId);
            throw new BusinessException("该文章不存在");
        }
        return article;
    }

    @Override
    public void update(Article article) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer userId = (Integer) map.get("id");
        Article article1 = articleMapper.selectOne(new LambdaQueryWrapper<Article>()
                .select(Article::getId, Article::getCreateUser)
                .eq(Article::getId, article.getId()));
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getId, article.getCategoryId()));
        if (article1 == null) {
            log.error("修改文章失败 - 该文章不存在 - articleId:{}", article.getId());
            throw new BusinessException("该文章不存在");
        }
        if (count == 0) {
            log.error("修改文章失败 - 该分类不存在 - categoryId:{}", article.getCategoryId());
            throw new BusinessException("该分类不存在");
        }
        if (!article1.getCreateUser().equals(userId)) {
            log.error("修改文章失败 - 无权修改 - articleId:{} - userId:{}", article.getId(), userId);
            throw new BusinessException("您无权修改此文章");
        }
        log.info("修改文章成功 - articleId:{} - userId:{}", article.getId(), userId);
        articleMapper.updateById(article);
    }

    @Override
    public void delete(Integer articleId) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer userId = (Integer) map.get("id");
        Article article = articleMapper.selectOne(new LambdaQueryWrapper<Article>()
                .select(Article::getId, Article::getCreateUser)
                .eq(Article::getId, articleId));
        if (article == null) {
            log.error("删除文章失败 - 该文章不存在 - articleId:{}", articleId);
            throw new BusinessException("该文章不存在");
        }
        if (!article.getCreateUser().equals(userId)) {
            log.error("删除文章失败 - 您无权删除此文章 - articleId:{} - userId:{}", articleId, userId);
            throw new BusinessException("您无权删除此文章");
        }
        log.info("删除文章成功 - articleId:{} - userId:{}", articleId, userId);
        articleMapper.deleteById(articleId);
    }

    @Override
    public List<Article> search(String halftitle) {
        if (halftitle == null) {
            log.error("搜索文章失败 - 标题不能为空");
            throw new BusinessException("标题不能为空");
        }
        log.info("搜索文章 - title:{}", halftitle);
        LambdaQueryWrapper<Article> wrapper = new LambdaQueryWrapper<>();
//        wrapper.select(Article::getTitle, Article::getCategoryId)
//                .like(Article::getTitle, halftitle);
        wrapper.select(Article::getId, Article::getTitle, Article::getCategoryId, Article::getCreateTime, Article::getCreateUser, Article::getCoverImg)
                .like(Article::getTitle, halftitle);
        List<Article> articles = articleMapper.selectList(wrapper);
        log.info("搜索文章成功 - keyword:{} - count:{}", halftitle, articles.size());
        return articles;
    }
}
