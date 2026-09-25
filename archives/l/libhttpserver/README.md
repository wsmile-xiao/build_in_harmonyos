# libhttpserver

## 简介
libhttpserver 是 GNU libmicrohttpd 的 C++ 封装库，提供面向对象的嵌入式 HTTP 服务
构建能力（webserver/resource/response 抽象、注册路由、线程池管理）。

## OHOS 适配
- **构建系统**: autotools（tarball 无 configure，构建期 autoreconf -fi）
- **依赖链**: libmicrohttpd（≥1.0.0）
- **上游仓库**: https://github.com/etr/libhttpserver
- **版本索引**:
  - 0.19.0 — 2026-09-20 适配（C++17；2.0.0 因 C++20 std::pmr 超出 OHOS libc++ 15004
    支持范围判 env_unsupported，详见该版本 notes.md 证据链）
