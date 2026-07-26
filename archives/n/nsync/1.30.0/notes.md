# nsync 1.30.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-13
- 编译器: clang/clang++ (clang-15, aarch64-linux-ohos, libc++)
- 状态: built（本地构建容器 `conan create` + test_package 通过）

## 编译步骤

标准 conan CMake 流程：`cmake.configure()` → `cmake.build()` → `cmake.install()`。
关键 CMake 变量：`CMAKE_SYSTEM_NAME=OHOS`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、
`BUILD_SHARED_LIBS=OFF`、`NSYNC_ENABLE_TESTS=OFF`。产物：`libnsync.a`（C API）、
`libnsync_cpp.a`（同源 C++ 编译变体）、公共头 13 个、cmake config。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'linux/futex.h' file not found` | host/build profile 同为 `os=OHOS`，conan 判定非交叉编译、不写 `CMAKE_SYSTEM_NAME`，cmake 退回宿主 Linux，nsync CMakeLists 落入 `platform/linux` futex 分支；musl 不提供内核头 `<linux/futex.h>` | 在 `generate()` 显式设 `CMAKE_SYSTEM_NAME=OHOS`（+`CMAKE_SYSTEM_PROCESSOR=aarch64`），令 nsync 落入通用 POSIX 分支（`nsync_semaphore_mutex.c`，纯 pthread mutex/cond），musl 完全兼容 |
| 2 | C 库 `fatal error: 'atomic.h' file not found` | 交叉模式下 cmake 对 OHOS 探测不出 `CMAKE_C_COMPILER_ID`，nsync 的 `include_directories(platform/clang)` 分支未触发 | `tc.extra_cflags` 追加 `-I <src>/platform/clang`，显式补回编译器头目录（`atomic.h`/`compiler.h`） |

## 源码修改

无补丁，仅通过 conanfile.py 的 CMake 变量与编译参数适配。

## 依赖版本

无外部三方依赖；运行期仅依赖系统 pthread（musl 内置于 libc）。

## 验证结果

```text
libnsync.a / libnsync_cpp.a 静态库构建成功（clang-15 aarch64-linux-ohos）
test_package: 双线程 producer/consumer，经 nsync_mu_lock/nsync_cv_wait/nsync_cv_signal 握手
1/1 Test #1: test_nsync ....... Passed
test_nsync: ELF 64-bit LSB arm64, dynamic, interpreter /lib/ld-musl-aarch64.so.1
```

## 注意事项

test_package 直接静态链接被测库并真实运行，无 dlopen，故无需 .so 代码签名。

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
