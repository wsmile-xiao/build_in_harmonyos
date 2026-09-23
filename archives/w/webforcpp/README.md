# WebForCPP

> Modern C++17 header-only library for web services, based on httplib and sajson.

## 简介

WebForCPP 提供现代 C++17 的头文件集合，用于快速构建 Web 客户端/服务端能力。核心包括 `httplib.h`（HTTP/HTTPS 客户端与服务器）、`sajson.h`（JSON 解析）以及 `http.hpp`/`https.hpp`/`json.hpp`/`utils.hpp` 等辅助封装。库本身为 header-only，安装后只需包含头文件即可使用，适合在 C++ 服务中集成 Web 访问与 JSON 处理。

## OHOS 适配要点

- Header-only，无需实体库；CMake 仅用于安装头文件至 `include/webforcpp` 与生成 `webforcpp.pc`。
- 依赖 OpenSSL（https 功能）与 pthread；httplib 使用 `USE_POLL` 与阻塞 I/O，在 OHOS bionic 上兼容。
- 上游测试通过 `ctest` 运行 `test_json` 与 `test_https`，无需平台补丁。
- 消费者测试需同时链接 `OpenSSL::SSL` 与 `Threads::Threads`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.6 | HTTPS/crypto 必需 |
| cmake | >=3.16 | 构建系统 |
| clang | 15 | OHOS 工具链 |

## 功能验证

```bash
conan create archives/w/webforcpp/0.2.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
ctest --output-on-failure --test-dir build  # 2/2 通过
```

## 参考

- [官方仓库](https://gitlab.com/tychosoft/webforcpp)
- [Alpine aports](https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/community/webforcpp)
