# websocketpp 0.8.2 适配笔记

## 编译环境
- 构建系统: cmake (header-only library)
- 编译日期: 2026-06-23
- 编译器: clang 18.1.8 / clang++ 18.1.8
- 状态: published

## 编译步骤

1. `init-build websocketpp 0.8.2 --url=file:///storage/Users/currentUser/.opendesk-tmp/websocketpp-0.8.2.tar.gz`
2. `source .build-context-websocketpp-0.8.2`
3. `cd $BUILD_SRC_DIR && mkdir build && cd build`
4. `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
5. `make` (header-only, no compilation needed)
6. `make install DESTDIR=$TEST_PREFIX`
7. `make check` → No target (BUILD_TESTS=OFF, header-only library)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.8.8) incompatible with CMake 4.1.2 | CMake 4.x removed compatibility with <3.5 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | CXX compiler test fails: `unable to find library -lc++` | HarmonyOS clang++ cannot link C++ executables (libc++/libc++abi not in default linker search path) | `-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` (header-only library, no linking needed) |
| 3 | `make -j2` fails: `jobserver mkfifo: Operation not permitted` | HMDFS/platform restriction on FIFO creation | Use `make` without -j flag (single-threaded) |
| 4 | `make check` no target | BUILD_TESTS=OFF (default), header-only library | Skipped, documented in test-report.md |

## 源码修改

无源码修改。所有兼容性问题通过 CMake 命令行参数解决，不涉及源文件改动。

## 依赖版本

- cmake 4.1.2
- clang/clang++ 18.1.8
- 无运行时依赖（header-only 库）

## 验证结果

```bash
# 头文件验证
$ find $TEST_PREFIX/$DEFAULT_PREFIX/include/websocketpp/ -type f -name "*.hpp" | wc -l
93

# cmake config 验证
$ ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/cmake/websocketpp/
websocketpp-config.cmake
websocketpp-configVersion.cmake

# 本地安装验证
$ ls $DEFAULT_PREFIX/include/websocketpp/
(base64/ client.hpp close.hpp common/ concurrency/ config/ ...)
```

## 交付物

| 文件 | 说明 |
|------|------|
| websocketpp-0.8.2-ohos-aarch64.tar.gz | 预编译包（header-only） |

## 注意事项

1. websocketpp 是 header-only 库，无需编译任何二进制文件
2. CMake 4.x 兼容性需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. HarmonyOS clang++ 链接器缺少 libc++/libc++abi，使用 `-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过编译器链接测试
4. `-j2` 并行编译在 HarmonyOS 上不可用（FIFO 限制），使用单线程 make
5. BUILD_TESTS=OFF 时无 test 目标，make check 跳过
---

**编译结束**: 2026-06-23 15:57
**最终状态**: published
