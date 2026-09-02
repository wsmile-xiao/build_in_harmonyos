# easyloggingpp

## 软件描述

Easylogging++ 是一个 C++ 单头（single-header）高效日志库，自 issue #445 起为
「单头 + 单一源文件」模式（需同时链接 `easylogging++.cc`）。提供日志级别过滤、
条件日志（`LOG_IF`）、频次日志（`LOG_EVERY_N`/`LOG_AFTER_N`/`LOG_N_TIMES`）、
多 logger 隔离、性能跟踪、自定义格式与 `%loc`/`%func` 等格式占位符，无任何外部依赖。

## 主要功能

- **级别体系**：`DEBUG/INFO/WARNING/ERROR/FATAL/TRACE/VERBOSE`
- **条件与频次日志**：`LOG_IF` / `LOG_EVERY_N` / `LOG_AFTER_N` / `LOG_N_TIMES`
- **多 logger**：`Loggers::getLogger("name")` 独立配置
- **配置化**：`Configurations` 按级别（Global/DEBUG/…）设置格式、文件名、输出目标
- **性能跟踪**：`PERFORMANCE_CHECKPOINT` 等，支持时间与内存指标
- **零依赖**：仅标准库，可静态链接

## 使用示例

```cpp
#include <easylogging++.h>
INITIALIZE_EASYLOGGINGPP

int main() {
    LOG(INFO) << "Hello, OHOS";
    LOG_IF(true, ERROR) << "conditional";
    for (int i = 1; i <= 4; ++i)
        LOG_EVERY_N(2, INFO) << "every n=" << i;
    return 0;
}
```

链接 `easyloggingpp::easyloggingpp`（CMake 目标）或 `-leasyloggingpp`。

## HarmonyOS 适配要点

- 配方启用 `build_static_lib=ON` 产出 `libeasyloggingpp.a`，`package_type=static-library`
- OHOS 工具链需 `compiler.libcxx=libc++`
- 注入 `CMAKE_SYSTEM_NAME=Linux`（E092 平台识别）与 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
  （上游 `cmake_minimum_required(2.8.7)` 与 CMake 4.x 不兼容）
- 日志文件须写入可写路径（OHOS `/tmp` 只读，E002）

## 版本

- 9.97.1（built，2026-09-02）

## 官方资源

- 上游仓库：https://github.com/abumq/easyloggingpp
- License：MIT
