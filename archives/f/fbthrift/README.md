# fbthrift

> Facebook Thrift — 高性能跨语言 RPC 框架的编译器和运行时库

## 简介

fbthrift 是 Facebook 的 Thrift 实现，提供了 Thrift IDL 编译器 (thrift1) 和 C++ 运行时库。Thrift 是一种跨语言的 RPC 框架，允许定义数据类型和服务接口，然后生成代码在不同语言间通信。

## OHOS 适配要点

- cmake 构建系统，需设置 `CMAKE_SYSTEM_NAME=OHOS`
- cmake 4.1.2 移除了 FindBoost 模块，使用 `find_package(Boost CONFIG)` + CMakeDeps 替代
- 仅编译 thrift compiler (`compiler_only=ON`)，完整库需要 folly、wangle 等更多依赖
- 需要 ELF 签名

## 排除与替代

- 完整 fbthrift C++ 运行时库需 folly + wangle 依赖链，暂不编译
- 仅提供 thrift1 compiler 用于生成代码

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 1.1.1w | TLS 支持 |
| boost | 1.84.0 | C++ 工具库 (filesystem) |
| flex | 2.6.4 | 词法分析 (tool_requires) |
| bison | 3.8.2 | 语法分析 (tool_requires) |

## 功能验证

```bash
thrift1 --version
```

## 参考

- [官方文档](https://github.com/facebook/fbthrift)
- [源码仓库](https://github.com/facebook/fbthrift)
