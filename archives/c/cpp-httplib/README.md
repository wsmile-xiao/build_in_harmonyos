# cpp-httplib

cpp-httplib 是一个 C++11 单头文件 HTTP/HTTPS 客户端/服务端库，功能完整且无需额外编译。

## 功能概述

- **单头文件**：只需 `#include <httplib.h>` 即可使用
- **Header-only**：无需编译二进制，直接包含头文件
- **HTTP/HTTPS**：完整客户端与服务端能力
- **流式传输**：支持 chunked、SSE、流式请求/响应
- **多平台**：支持 Linux、macOS、Windows、OHOS

## OHOS 适配

### 特性
- **Header-only 库**：无需编译二进制，只需安装头文件
- **CMake INTERFACE library**：通过 CMake 安装头文件和配置文件
- **无必需外部依赖**：OpenSSL/Zlib/Brotli 均为可选能力

### 已知问题
- 不可调试的 HarmonyOS production 虚拟机可能限制 HDC shell 进程执行
  `bind()`；按平台权限模型，应用进程应在清单申请网络权限，但本次未在应用
  身份下验证网络回环，使用方仍需在实际应用上下文确认。

### 与 Linux 的差异
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=str(self.settings.arch)` 规避 E092（CMake 不识别 OHOS 平台）

## 使用方式

```cpp
#include <httplib.h>

int main() {
    httplib::Client cli("http://example.com");
    auto res = cli.Get("/");
    return res ? 0 : 1;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.41.0](./0.41.0/) | built | 2026-09-11 |
| [0.18.0](./0.18.0/) | built | 2026-08-29 |

## 参考资料

- GitHub: https://github.com/yhirose/cpp-httplib
