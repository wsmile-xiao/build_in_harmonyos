# libdispatch 5.10.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published
- 源码来源: https://github.com/apple/swift-corelibs-libdispatch/archive/refs/tags/swift-5.10.1-RELEASE.tar.gz

## 编译步骤

1. **初始化**: `ohc-run.py init-build libdispatch 5.10.1 --url=...`
2. **CMake configure**:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
         -DENABLE_SWIFT=OFF -DENABLE_DTRACE=OFF \
         -DENABLE_INTERNAL_PTHREAD_WORKQUEUES=ON \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_C_FLAGS="-D__OHOS__" -DCMAKE_CXX_FLAGS="-D__OHOS__" \
         $BUILD_SRC_DIR
   ```
3. **编译**: `make -j1`
4. **安装**: `make install DESTDIR=$TEST_PREFIX` (R20 DESTDIR 模式)
5. **测试**: `ctest` — 22/22 PASS (30.89s)
6. **本地安装**: `make install` (不带 DESTDIR)
7. **验证**: 编写使用 libdispatch API 的测试程序，编译链接成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `getprogname(3) is not available on this platform` | OpenHarmony musl libc 不提供 `getprogname()` 和 `program_invocation_name`，但提供 `__progname` | 在 `src/shims/getprogname.h` 中添加 `#ifdef __OHOS__` 守卫，使用 `__progname` (与 Android 方案类似) |
| 2 | `sys/poll.h` 重定向到 `poll.h` 导致 -Werror 失败 | OpenHarmony musl libc 的 `sys/poll.h` 是一个 redirect warning，`#include <sys/poll.h>` 会被重定向到 `<poll.h>` | 在 `tests/dispatch_test.c` 中添加 `#ifdef __OHOS__` 守卫，直接使用 `#include <poll.h>` |
| 3 | `const char *` vs `char *` 类型不匹配 | `__progname` 是 `const char *` 类型，但 `getprogname()` 返回 `char *`，-Werror 导致编译失败 | 使用 `(char *)__progname` 显式类型转换 |

## 源码修改

### 文件 1: src/shims/getprogname.h
- 添加 `#ifdef __OHOS__` 声明 `extern const char *__progname;`
- 在 `getprogname()` 函数中添加 `#elif defined(__OHOS__)` 返回 `(char *)__progname`

### 文件 2: tests/dispatch_test.c
- 将 `#include <sys/poll.h>` 替换为 `#ifdef __OHOS__` 守卫下使用 `#include <poll.h>`

## 依赖版本

- clang 15.0.4
- cmake 4.1.2
- make 4.4.1
- pthread (系统自带)

## 验证结果

```bash
# ctest 结果
22/22 tests passed, 0 tests failed, Total Test time = 30.89s

# 本地安装验证
ls -la $DEFAULT_PREFIX/lib/libdispatch.so   # 399744 bytes
ls -la $DEFAULT_PREFIX/lib/libBlocksRuntime.so  # 22848 bytes

# 链接验证
编写 test_dispatch.c (使用 dispatch_queue_create/dispatch_release)
clang -fblocks -D__OHOS__ -I$DEFAULT_PREFIX/include test_dispatch.c \
  -L$DEFAULT_PREFIX/lib -ldispatch -o test_dispatch
# ✅ 编译链接验证成功
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdispatch-5.10.1-ohos-aarch64.tar.gz | 853KB | 预编译包 |

## 注意事项

1. libdispatch 是 Apple GCD (Grand Central Dispatch) 的开源实现，主要作为库（.so），没有 bin/ 目录的可执行文件
2. 编译需要 `-fblocks` 选项（clang Blocks 特性），CMakeLists.txt 已自动添加
3. 需要添加 `-D__OHOS__` 编译标志来启用 OpenHarmony 平台适配代码
4. CMake 不识别 OpenHarmony 平台（System is unknown），但编译仍然成功
5. `ENABLE_INTERNAL_PTHREAD_WORKQUEUES=ON` 是必要的，因为 OpenHarmony 没有 pthread workqueue 支持
6. libdispatch.so 链接 libBlocksRuntime.so (相对路径 `$ORIGIN/../libBlocksRuntime.so`)
---

**编译结束**: 2026-06-02 19:41
**最终状态**: published
