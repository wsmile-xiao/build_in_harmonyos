# Crow

Crow 是一个 C++ 微型 Web 框架，灵感来自 Python 的 Flask。它提供了简洁的 API 来构建 HTTP 服务，支持路由、JSON、WebSocket、中间件等功能。

## 功能概述

- **路由系统**：支持 URL 参数、正则匹配、动态路由
- **JSON 支持**：内置 JSON 序列化与反序列化
- **WebSocket**：支持 WebSocket 长连接
- **中间件**：支持 Cookie 解析、CORS、Session 等中间件
- **模板引擎**：内置 Mustache 模板引擎
- **多部分上传**：支持 multipart/form-data 文件上传
- **SSL/TLS**：可选 SSL 支持（需 OpenSSL）
- **压缩**：可选 HTTP 压缩（需 zlib）

## OHOS 适配

### 特性
- **Header-only 库**：无需编译二进制，只需安装头文件
- **CMake INTERFACE library**：通过 CMake 安装头文件和配置文件
- **依赖 asio**：使用独立 asio（不依赖 boost）

### 已知问题
- 上游测试（unittest）在 OHOS/aarch64 上部分用例因网络/SSL 相关原因失败，当前版本仅做编译验证（CROW_BUILD_TESTS=ON），不运行 ctest，以避免阻塞 CI
- SSL 功能默认关闭（CROW_ENABLE_SSL=OFF），未经 OHOS 平台完整验证；如需启用请自行测试
- 压缩功能默认关闭（CROW_ENABLE_COMPRESSION=OFF），未经 OHOS 平台完整验证

### 与 Linux 的差异
- OHOS 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` 规避平台识别问题；Linux 使用 Conan 配置中的实际架构值

## 依赖关系

### 编译依赖
- asio（header-only，通过 conandata.yml 下载并嵌入打包，包自包含）
- Catch2 3.15.1 与 CPM.cmake 0.40.2（仅用于编译上游测试，通过 conandata.yml 预下载以避免配置阶段联网）

### 可选依赖
- OpenSSL: SSL/TLS 支持（CROW_ENABLE_SSL=ON）
- zlib: HTTP 压缩支持（CROW_ENABLE_COMPRESSION=ON）

## 使用方式

```cmake
# CMakeLists.txt
find_package(Crow REQUIRED)
target_link_libraries(my_app PRIVATE Crow::Crow)
```

```cpp
#include "crow.h"

int main() {
    crow::SimpleApp app;
    CROW_ROUTE(app, "/hello")([]() {
        return "Hello, World!";
    });
    app.port(8080).run();
    return 0;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.3.3](./1.3.3/) | built | 2026-07-14 |

## 参考资料

- 官网: https://crowcpp.org/
- GitHub: https://github.com/CrowCpp/Crow
- 文档: https://crowcpp.org/master/
