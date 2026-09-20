# cppdap

cppdap 是 Google 开源的 C++11 Debug Adapter Protocol（DAP）SDK，提供实现 DAP
客户端或服务端所需的类型安全结构与会话 API。

## 功能概述

- DAP 完整协议的类型安全 C++ 结构（请求 / 响应 / 事件）
- `dap::Session` 客户端 / 服务端会话管理（bind / send / registerHandler）
- `dap::pipe` / `dap::file` / `dap::spy` 字节流抽象与内容流编解码
- 可插拔 JSON 后端（nlohmann_json / RapidJSON / JsonCpp，本适配选用 nlohmann_json）

## OHOS 适配

### 特性

- 使用制品仓已发布的 `nlohmann_json/3.12.0` 作为外部 JSON 后端
 （`-DCPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE=ON`），不依赖发布包缺失的
  `third_party/json` 子模块
- 裸 cmake + OHOS SDK `ohos.toolchain.cmake` 自发现配置，绕开
  `CMakeToolchain` 的系统名映射问题
- 上游库目标恒为 `STATIC`，配方保留 `shared` 开关仅作 Conan 惯例透传
- 上游单测（13 个 `*_test.cpp`，gtest）通过 vendor googletest 源码后构建运行

### 已知问题

- 无已知问题

### 与 Linux 的差异

- `CMAKE_SYSTEM_NAME` 为 `HarmonyOS`/`OHOS` 时上游不再自动链接 `pthread`，
  配方的 `package_info()` 对 `Linux` 与 `OHOS` 均声明 `pthread` 系统库

## 使用方式

```cpp
#include <dap/session.h>
#include <dap/protocol.h>

int main() {
    auto session = dap::Session::create();
    session->registerHandler([](const dap::InitializeRequest&) {
        dap::InitializeResponse response;
        response.supportsConfigurationDoneRequest = true;
        return response;
    });
    return session ? 0 : 1;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.58.0a](./1.58.0a/) | built | 2026-09-10 |

## 参考资料

- GitHub: https://github.com/google/cppdap
- DAP 协议: https://microsoft.github.io/debug-adapter-protocol/
