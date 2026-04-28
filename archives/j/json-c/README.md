# json-c

## 简介
json-c 是一个 C 语言的 JSON 库，提供 JSON 对象的创建、解析、操作和序列化功能。

## OHOS 适配
- 标准autotools 项目，需要 config.guess/config.sub 补丁识别 HarmonyOS 系统
- 需要小补丁修复 json_util.c 中的平台兼容问题

## 依赖
- 编译依赖：clang, make
- 运行依赖：libc

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libjson-c*
```

## 参考
- 源码：https://github.com/json-c/json-c
