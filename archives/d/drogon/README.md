# drogon

## 简介
drogon 是一个基于 C++17 的异步 HTTP Web 应用框架，运行于 Linux/macOS/Unix/Windows。支持 HTTP/1.1、HTTP/2（h2）、WebSocket、HTTPS（OpenSSL），内置 ORM、模板引擎（CSP）、JSON 序列化等，是高性能 C++ 后端开发的主流框架之一。

- 上游：https://github.com/drogonframework/drogon
- 许可证：MIT
- 网络层：trantor（drogon 官方异步网络库）

## 版本
- 1.9.13（2025-08 发布）：适配 HarmonyOS PC（aarch64）

## 依赖
- trantor/1.5.26（仓内）
- jsoncpp/1.9.8（仓内）
- openssl（经 trantor 传递）
- zlib（仓内）
- uuid/2.40.1（util-linux libuuid，仓内）

## 裁剪说明
数据库客户端、Redis 客户端、brotli、yaml-cpp、drogon_ctl、示例与文档均关闭（上游为软依赖，缺失时自动编译 stub/跳过）。
