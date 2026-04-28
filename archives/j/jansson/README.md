# Jansson

## 简介
Jansson 是一个 C 语言 JSON 库，提供 JSON 的编码、解码和操作功能，API 简洁，符合 RFC 8259 标准。

## OHOS 适配
- 同时支持 autotools 和 CMake，缺少 automake 时使用 CMake 构建
- 所有 215 个测试通过，无平台兼容性问题
- 无需任何补丁

## 依赖
- 编译依赖：cmake, clang
- 运行依赖：libc

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libjansson*
```

## 参考
- 源码：https://github.com/akheron/jansson
