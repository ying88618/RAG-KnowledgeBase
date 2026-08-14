package com.example.springboot.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.springboot.Service.CategoryService;
import com.example.springboot.mapper.CategoryMapper;
import com.example.springboot.pojo.Category;
import com.example.springboot.utils.ThreadLocalUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.springboot.pojo.Result;

import java.util.List;
import java.util.Map;


@Slf4j
@Service
public class CategoryServiceImpl extends ServiceImpl<CategoryMapper, Category> implements CategoryService {
    @Autowired
    private CategoryMapper categoryMapper;

    @Override
    public Result add(Category category) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer id = (Integer) map.get("id");
        category.setCreateUser(id);
        categoryMapper.insert(category);
        log.info("分类添加成功 - category:{}", category);
        return Result.success();
    }

    @Override
    public List<Category> list() {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer id = (Integer) map.get("id");
        List<Category> list = categoryMapper.selectList(Wrappers
                .<Category>lambdaQuery()
                .eq(Category::getCreateUser, id));
        log.info("分类列表查询成功 - list:{} - count:{}", list, list.size());
        return list;
    }

    @Override
    public Category detail(Integer id) {
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Category::getId, id);
        Category category = categoryMapper.selectOne(wrapper);
        log.info("分类详情查询成功 - category:{}", category);
        return category;
    }

    @Override
    public Result update(Category category) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer userid = (Integer) map.get("id");
        Category dbcategory = categoryMapper.selectOne(new LambdaQueryWrapper<Category>()
                .select(Category::getId, Category::getCreateUser)
                .eq(Category::getId, category.getId()));
        if (dbcategory == null) {
            log.error("修改分类失败 - 分类不存在 - categoryId:{}", category.getId());
            return Result.error("分类不存在");
        }
        if (!dbcategory.getCreateUser().equals(userid)) {
            log.error("修改分类失败 - 您无权修改此分类 - categoryId:{} - userId:{}", category.getId(), userid);
            return Result.error("您无权修改此分类");
        }
        categoryMapper.updateById(category);
        log.info("分类修改成功 - categoryId:{}", category.getId());
        return Result.success();
    }

    @Override
    public Result delete(Integer id) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer userid = (Integer) map.get("id");
        Category category = categoryMapper.selectOne(Wrappers
                .<Category>lambdaQuery()
                .select(Category::getId, Category::getCreateUser)
                .eq(Category::getId, id)
                .eq(Category::getCreateUser, userid));
        if (category == null) {
            log.error("删除分类失败 - 分类不存在或无权删除 - categoryId:{} - userId:{}", id, userid);
            return Result.error("您没有创建此分类");
        }
        categoryMapper.delete(Wrappers
                .<Category>lambdaQuery()
                .eq(Category::getId, id)
                .eq(Category::getCreateUser, userid));
        log.info("分类删除成功 - categoryId:{}", id);
        return Result.success();
    }
}
