# pam-reattach 1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang
- 状态: built（仅 API 壳，核心功能不满足实质适配要求）

## 适配结论

**核心 API `reattach_aqua()` 在 OHOS 上不可实现。** 该函数依赖 macOS
Darwin 内核的 XPC（XNU IPC）和 Mach bootstrap port 机制，用于
重新连接到用户 Aqua GUI 会话的 bootstrap namespace。OHOS 操作
系统架构完全不同，不存在 Mach 内核、XPC 或 Aqua 会话概念。

本配方仅提供：
- 编译产物 `libreattach.a` — 包含 `reattach_aqua()` 的 ENOTSUP 桩实现
- 公开头文件 `reattach.h` — 保留完整 API 声明
- manpage `reattach_aqua.3` — 上游文档

PAM 模块和 CLI 工具在构建时关闭（`ENABLE_PAM=OFF`、`ENABLE_CLI=OFF`），
因为它们同样绑定 macOS Aqua 会话语义。

> **⛔ 不满足实质适配要求**：该库的核心功能是 macOS 平台的会话重连接，
> OHOS 无对应 API 或概念，无法提供实质功能。此配方仅作为 API 兼容
> 壳发布，供上游依赖方在编译期引用。

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build pam-reattach 1.3 --url=https://github.com/fabianishere/pam_reattach/archive/refs/tags/v1.3.tar.gz --tar=tar.gz
cmake -S . -B build-ohos -DCMAKE_BUILD_TYPE=Release -DENABLE_PAM=OFF -DENABLE_CLI=OFF
cmake --build build-ohos -j1
cmake --install build-ohos --prefix "$TEST_PREFIX"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `mach/mach.h` 不存在 | 上游核心实现依赖 Darwin Mach/XPC API | `OHOS_PLATFORM` 下让 `reattach_aqua()` 返回 `ENOTSUP`，保留可链接 API |
| 2 | PAM 模块不可构建 | OHOS 环境无上游期望的 OpenPAM/Darwin Aqua 会话语义 | Conan 配方关闭 `ENABLE_PAM`，仅发布基础库 |
| 3 | 平台检测 | 原 conanfile.py 硬编码 `CMAKE_SYSTEM_NAME=Linux` 和手工 `__OHOS__` | 移除手工定义，使用 Conan toolchain 自动映射（`os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`）和 `OHOS_PLATFORM` 预处理宏 |

## 源码修改

- `0001-include-reattach.h.patch`: 补充 `sys/types.h`，确保公开头文件中的 `uid_t` 有声明。
- `0002-src-reattach.c.patch`: 为 OHOS 增加平台保护，避免包含 Darwin Mach/XPC 头文件，并让 `reattach_aqua()` 返回 `ENOTSUP`。

## 依赖版本

无第三方 Conan 依赖。

## 验证结果

```bash
cmake --build build-ohos -j1
# 通过，生成 libreattach.a

cmake --install build-ohos --prefix "$TEST_PREFIX"
# 通过，安装 lib/libreattach.a、include/reattach.h、share/man/man3/reattach_aqua.3
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libreattach.a | OHOS 可链接静态库（API 桩） |
| include/reattach.h | 公共头文件 |
| share/man/man3/reattach_aqua.3 | 上游 manpage |

## 注意事项

`reattach_aqua()` 在 OHOS 上返回 `ENOTSUP`。上游功能面向 macOS Aqua
bootstrap namespace，OHOS 不具备等价会话语义。实质适配不可行。

### R8 平台条件编译宏豁免说明

本项目使用 `OHOS_PLATFORM` 宏（在 `conanfile.py` 中通过 `-DOHOS_PLATFORM=1` 定义）在 C 源码中区分 OHOS 平台。该宏用于在 `patches/0002-src-reattach.c.patch` 中保护 Darwin Mach/XPC 头文件引入和 `reattach_aqua()` 的桩实现。

**豁免理由**：`reattach_aqua()` 的核心功能依赖 macOS Darwin 内核的 Mach 和 XPC IPC 机制，OHOS 操作系统架构完全不同，不存在 POSIX 等价接口。`OHOS_PLATFORM` 是唯一可行的适配方式，已在 Conan 配方中通过 `settings.os` 条件控制，仅在 `os == "OHOS"` 时生效，不影响其他平台。此场景已通过 PR 评审确认，属于 R8 规则的合理例外。若后续 OHOS 平台提供等价 IPC 接口，可移除该宏并改用 POSIX 接口。---

**编译结束**: 2026-07-17 04:24
**最终状态**: built
