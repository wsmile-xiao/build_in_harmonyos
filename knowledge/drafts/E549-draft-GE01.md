# E549 — CMake 平台枚举缺少 OHOS 时的无 x86 平台配置与 Conan 绑定

## 问题现象

有些 CMake 库不是按 `CMAKE_SYSTEM_NAME` 选择平台，而是加载
`cmake/platforms/<枚举>/config.cmake`。当目标是 OHOS、上游没有 OHOS 枚举
时，配置阶段会找不到平台文件；直接复用 `Linux64-clang` 又可能把 `-m64`
这样的 x86 标志注入 arm64 编译。仅在 Windows/x86 上构建通过不能证明目标配置
正确。

## 根因

平台选择器的枚举与 CMake 的系统识别是两套机制。Geogram 1.10.1 的
`geo_detect_platform.cmake` 没有 OHOS 分支，而 `Linux64-clang/config.cmake`
显式追加 `-m64`。另一方面，该 release asset 已经包含第三方源码；把问题归因
为 Conan 依赖会错误扩大 W0 闭包。

## 通用修复

1. 先确认官方 release asset、目标工具链和实际 vendored 目录；用
   `conan download --only-recipe`/`conan install --build=never` 证明真正的外部
   依赖闭包。
2. 若上游缺少目标平台枚举，增加只在目标系统使用的配置文件，复用已验证的
   Linux/clang 能力选项，但移除架构专属标志（例如 `-m64`）。不要把目标编译器
   路径写死到主机环境。
3. 在 Conan `build()` 中显式绑定 `CMAKE_TOOLCHAIN_FILE`、目标架构、平台枚举
   和最小功能开关；配置后读取缓存和生成构建文件，确认平台文件命中且没有目标
   不接受的标志。
4. 让消费者通过 Conan 生成的 CMake target 编译并调用真实公开 API，不能只检查
   头文件存在。

## Geogram 实例

本次适配增加 `OHOS-clang/config.cmake`，设置 64 位目标并复用
`Linux-clang.cmake`，不引入 `-m64`。配方关闭 graphics、TBB 和 legacy numerics；
HLBFGS、TetGen、Triangle、Lua 仍由完整 release asset 内置。`test_package`
通过 `geogram::geogram` 链接，调用 `GEO::initialize` 和 `GEO::vec3` 算术。

## 验证与边界

- 验证必须包括配置缓存、编译器参数、产物架构以及真实消费者编译/链接；本地
  MinGW smoke 只能覆盖主机构建，不代替 OHOS W3。
- 仅当第三方源码确实随官方 release 提供、并且逐项检查不存在目标二进制依赖
  时，才能将 W0 记录为无 Conan 依赖。
- 如果上游平台文件包含目标 ABI、sysroot 或运行时特有逻辑，不能简单复用
  Linux-clang；应改为官方适配或 fail closed。

## 无效方案

- 把 `CMAKE_SYSTEM_NAME=OHOS` 当作已自动选择上游平台枚举。
- 复用带 `-m64` 的 x86 配置，或仅用 `-Wno-unknown-warning-option` 掩盖标志错误。
- 使用 GitHub 自动生成的 source tarball 替代 release asset，忽略上游明确的
  submodule 缺失说明。

