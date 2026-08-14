package com.example.springboot.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.StringUtils;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.springboot.Service.UserService;
import com.example.springboot.mapper.UserMapper;
import com.example.springboot.pojo.Result;
import com.example.springboot.pojo.User;

import com.example.springboot.utils.JwtUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import com.example.springboot.utils.ThreadLocalUtil;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Autowired
    private UserMapper userMapper;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired
    private JwtUtil jwtUtil;

    @Override
    public void register(String username, String password) {
        //加密
        log.info("用户注册 - username:{}", username);
        String encodedPassword = passwordEncoder.encode(password);
        //添加
        User user = new User();
        user.setUsername(username);
        user.setPassword(encodedPassword);
        userMapper.insert(user);
        log.info("用户注册成功 - username:{}", username);
    }

    @Override
    public User findByUsername(String username) {
        log.info("查询用户 - username:{}", username);
        LambdaQueryWrapper<User> wrapper = Wrappers.lambdaQuery();
        wrapper.select(User::getId, User::getUsername, User::getPassword, User::getUserPic, User::getEmail, User::getNickname)
                .eq(User::getUsername, username);
        User user = userMapper.selectOne(wrapper);
        log.info("查询用户成功 - username:{},found:{}", username, user != null);
        return user;
    }

    @Override
    public Result judge(User u, String password) {
        log.info("用户登录 - username:{}", u.getUsername());
        if (passwordEncoder.matches(password, u.getPassword())) {
            Map<String, Object> claims = new HashMap<>();
            claims.put("id", u.getId());
            claims.put("username", u.getUsername());
            String token = jwtUtil.genToken(claims);
            //保存token到redis
            ValueOperations<String, String> operation = stringRedisTemplate.opsForValue();
            operation.set(token, token, 14, TimeUnit.DAYS);
            //保存用户的token到redis
            String userTokensKey = "user_tokens:" + u.getId();
            stringRedisTemplate.opsForSet().add(userTokensKey, token);
            stringRedisTemplate.expire(userTokensKey, 14, TimeUnit.DAYS);
            log.info("用户登录成功 - username:{}", u.getUsername());
            return Result.success(token);
        }
        log.error("用户登录失败 - 密码错误 - username:{}", u.getUsername());
        return Result.error("密码错误");
    }

    @Override
    public void update(User user) {
        userMapper.updateById(user);
    }

    @Override
    public void updateAvatar(String avatarUrl) {
        Map<String, Object> map = ThreadLocalUtil.getThreadLocal();
        Integer id = (Integer) map.get("id");
        userMapper.update(null,
                Wrappers.<User>lambdaUpdate()
                        .set(User::getUserPic, avatarUrl)
                        .eq(User::getId, id)
        );
    }

    @Override
    public Result updatePwd(Map<String, String> map, String token) {
        String oldPwd = map.get("old_pwd");
        String newPwd = map.get("new_pwd");
        String rePwd = map.get("re_pwd");
        if (StringUtils.isEmpty(oldPwd) || StringUtils.isEmpty(newPwd) || StringUtils.isEmpty(rePwd)) {
            log.error("用户修改密码失败 - 缺少必要参数");
            return Result.error("缺少必要参数");
        }
        if (newPwd.length() < 5 || newPwd.length() > 16) {
            log.error("用户修改密码失败 - 密码长度应在5-16之间");
            return Result.error("密码长度应在5-16之间");
        }
        if (!newPwd.equals(rePwd)) {
            log.error("用户修改密码失败 - 两次输入密码不一样");
            return Result.error("两次输入密码不一样");
        }
        Map<String, Object> usermap = ThreadLocalUtil.getThreadLocal();
        Integer id = (Integer) usermap.get("id");
        User user = userMapper.selectOne(Wrappers.<User>lambdaQuery()
                .select(User::getPassword, User::getUsername)
                .eq(User::getId, id));

        if (!passwordEncoder.matches(oldPwd, user.getPassword())) {
            log.error("用户修改密码失败 - 原密码错误");
            return Result.error("原密码错误");
        }
        userMapper.update(null,
                Wrappers.<User>lambdaUpdate()
                        .set(User::getPassword, passwordEncoder.encode(newPwd))
                        .eq(User::getId, id));
        log.info("用户修改密码成功 - username:{}", user.getUsername());
        //清除所有token
        String userTokensKey = "user_tokens:" + id;
        Set<String> userTokens = stringRedisTemplate.opsForSet().members(userTokensKey);
        if (userTokens != null && !userTokens.isEmpty()) {
            stringRedisTemplate.delete(userTokens);
        }
        stringRedisTemplate.delete(userTokensKey);
        return Result.success();
    }

    @Override
    public boolean exist(String username) {
        Long count = userMapper.selectCount(Wrappers.<User>lambdaQuery()
                .eq(User::getUsername, username));
        return count > 0;
    }
}