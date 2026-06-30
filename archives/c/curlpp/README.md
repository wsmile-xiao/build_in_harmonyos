# curlpp

curlpp 是一个 C++ 少封装层（thin wrapper）库，封装了 libcurl 的 C API，提供面向对象的接口简化 HTTP/HTTPS 请求操作。

## 功能

- 提供 curlpp::Easy 类封装单个 HTTP 请求
- 提供 curlpp::Multi 类封装并发 HTTP 请求
- 支持 HTTP GET/POST/PUT 等全部 libcurl 支持的操作
- 支持回调函数（写入、进度、调试等）
- 支持 HTTPS/SSL/TLS
- 同时提供动态库（libcurlpp.so）和静态库（libcurlpp.a）

## 已编译版本

- 0.8.1 (2026-06-17) — 状态: published

## 依赖

- libcurl (curl 8.19.0 或更高版本)
- C++11 编译器

## 注意事项

- curlpp 0.8.1 与 curl 8.x 存在多处 API 废弃兼容问题（CURLOPT_CLOSEPOLICY 等），编译时产生大量 deprecation warnings（不影响功能）
- 需设置 PKG_CONFIG_PATH 包含 `$DEFAULT_PREFIX/lib/pkgconfig` 以确保 cmake FindCURL 能找到 libcurl
- 无 make check 测试套件

## 安装

通过 cmd-pkgs 预编译包安装:
bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- curlpp 0.8.1
