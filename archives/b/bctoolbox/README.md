# bctoolbox

bctoolbox 是 Belledonne Communications（Linphone 系列）各组件共用的可移植工具箱库，提供日志、链表/映射容器、参数解析、字符编码转换、VFS 虚拟文件层与套接字辅助等基础设施。

## 功能概述

- 统一日志框架（多 handler、按域分级、线程级日志级别）
- `bctbx_list` 链表与 C++ `bctbx::map` 等容器
- 参数字符串解析（`bctbx_param_string_get_value`）
- 字符编码转换（依赖 ICU 时增强，无 ICU 时退化为 ASCII 路径）
- VFS 虚拟文件系统层（含标准实现；加密 VFS 需 mbedtls 后端）
- 可选加密/ECC 包装（mbedtls、decaf；本适配的交付配置未启用 mbedtls）

## OHOS 适配

- 构建系统 CMake，C/C++17 混合；OHOS 侧由 Conan toolchain 设定 `CMAKE_SYSTEM_NAME=HarmonyOS`，走 POSIX 代码路径（非 Android/Windows 分支）。
- 测试组件打开且**真实运行**：`ENABLE_TESTS_COMPONENT=ON` + `ENABLE_UNIT_TESTS=ON`，上游 `find_package(BCUnit 3.0.2 REQUIRED)` 由 `test_requires("bcunit/5.3.113")` 满足（仅测试用，不进消费方依赖链）；`build()` 内直接执行 `bctoolbox-tester`，退出码决定包构建成败。
  - 交付配置（mbedtls 关闭）实测 **6 suites / 20 tests / 20 passed / 0 failed / 779 asserts**；
  - 全集 35 个注册用例在「测试专用 mbedtls 3.6.6 源码包」的验证配置下实测 **8 suites / 35 tests / 35 passed / 0 failed / 103688 asserts**（见 `5.3.115/reports/upstream-test-full-feature.md`）。
- 测试框架适配补丁（均为上游在 OHOS 上的真实缺陷/环境前提）：`bctbx_freeaddrinfo(NULL)` 空指针解引用、`Addrinfo sort` 用例依赖外网 IPv6 解析、`tester` 收尾无条件调用 glibc 专有的 `mallinfo()`（本机调用即崩）。
- 加密后端关闭：5.3 的 mbedtls 包装器仅兼容 v2/v3 API，OHOS registry 仅有 mbedtls 4.1.0（上游明确警告 v4 不兼容）；`ENABLE_MBEDTLS=OFF` 后补丁提供 `bctbx_clean` 零化兜底（核心 `vfs.c` 引用该符号，上游仅在后端文件中定义）。
- ECC 关闭：decaf 未发布（上游软可选）。
- 与 Linux 的差异：无 execinfo 差异（OHOS sysroot 提供 `execinfo.h`）；`pthread`/`rt`/`dl` 探测在 OHOS musl 下全部通过。
- 构建并发：共享设备上必须显式 `-c tools.build:jobs=2`（本机 `os.cpu_count()`=20 而 affinity 仅 8，默认 20 路并发会打挂整机）。

## 依赖关系

- 编译依赖：无（CMake ≥ 3.22、clang、make）
- 测试依赖（`test_requires`，不进消费方依赖链）：`bcunit/5.3.113`
- 运行依赖：`libc++_shared.so`（C++ 运行时，OHOS 系统提供）

## 参考资料

- 上游仓库：https://gitlab.linphone.org/BC/public/bctoolbox
- 上游镜像：https://github.com/BelledonneCommunications/bctoolbox
