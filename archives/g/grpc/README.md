# grpc

## 简介

gRPC 是一个高性能、开源的通用 RPC（远程过程调用）框架，由 Google 开发。基于 HTTP/2 协议传输，使用 Protocol Buffers 作为接口描述语言，支持多种语言。

## 版本

- **1.49.2** (2026-05-25) - 部分编译成功，提供插件工具和无SSL版本的库

## 编译状态

### 1.49.2 - built (部分成功)

**编译产物**：
- ✅ grpc_cpp_plugin：C++ 代码生成插件
- ✅ grpc_unsecure：无SSL的核心库
- ✅ grpc++_unsecure：无SSL的C++包装库
- ✅ 其他插件工具（csharp、node、objective_c、php、python、ruby）
- ❌ grpc 完整库（缺少 re2 子模块）

**限制说明**：
- 缺少 re2 子模块导致完整 grpc 库编译失败
- 网络连接问题无法下载 re2 源码
- 仅提供无SSL版本的库和插件工具

**依赖**：
- protobuf 21.12
- c-ares 1.34.6
- abseil-cpp 20260107.1
- boringssl（内置编译）

**适用场景**：
- gRPC 代码生成（使用 grpc_cpp_plugin）
- 无需SSL的gRPC通信场景
- protoc 插件开发

## 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- grpc 1.49.2

# 使用插件生成代码
grpc_cpp_plugin --help

# 在项目中链接无SSL库
# 需要手动链接 libgrpc++_unsecure.a、libgrpc_unsecure.a 等静态库
```

## 注意事项

1. 此版本仅提供无SSL版本的 gRPC 库
2. 如需完整功能（带SSL支持），需要解决 re2 子模块下载问题
3. 网络问题严重，建议使用 git clone --recursive 方式获取完整源码

## 许可证

Apache 2.0 License

## 官网

https://grpc.io