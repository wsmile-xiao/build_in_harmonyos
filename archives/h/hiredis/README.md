# hiredis

## 简介
hiredis 是 Redis 的极简 C 客户端库，提供同步和异步 API，支持 Redis 协议的完整实现。

## OHOS 适配
- 标准 autotools 项目，需要 config.guess/config.sub 补丁识别 HarmonyOS 系统
- 编译和安装流程与 Linux 基本一致

## 依赖
- 编译依赖：clang, make
- 运行依赖：libc

## 功能验证
```bash
# 验证库安装
ls -la $HOME/usr/local/lib/libhiredis*
```

## 参考
- 官网：https://github.com/redis/hiredis
- 许可证：BSD-3-Clause
