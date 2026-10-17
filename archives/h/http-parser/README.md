# http-parser

## 简介
http-parser 是 Node.js 官方的 C 语言 HTTP 消息解析器，解析 HTTP 请求与响应，无系统调用、无内存分配、可随时中断，每个连接仅需约 40 字节状态，广泛用于高性能 HTTP 应用中（Node.js、haproxy、restinio 等）。

## 功能概述
- 解析 HTTP 请求与响应（HTTP_REQUEST / HTTP_RESPONSE / HTTP_BOTH）
- 流式回调驱动：message_begin / url / status / header_field / header_value / headers_complete / body / message_complete
- URL 解析（schema/host/path/query/fragment/userinfo 字段）
- 严格模式（HTTP_PARSER_STRICT）与快速模式
- 不进行系统调用、不分配内存、可暂停恢复

## OHOS 适配
- 纯 Makefile 构建，无 configure 脚本，无外部依赖，HNP clang (aarch64-linux-ohos) 直接编译通过
- `-Wall -Wextra -Werror` 下无告警，无需补丁
- 静态库对象以 `-fPIC` 编译（CFLAGS_FAST_EXTRA=-fPIC），便于下游（如 restinio）链入共享库
- 上游测试套件 `make test`（test_g + test_fast）在 OHOS 上完整通过
- 编译器路径从 Conan conf 获取 (R33)，不使用 shell 环境变量

## 依赖
- 无编译依赖、无运行依赖

## 功能验证
```bash
# 消费者测试（test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 上游官方测试
make test   # test_g + test_fast，test.c 内含完整断言
```

## 参考
- 上游仓库: https://github.com/nodejs/http-parser
- 上游版本: v2.9.4（tag 源码）
- 许可证: MIT (LICENSE-MIT)
