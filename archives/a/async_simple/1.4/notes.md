# async_simple 1.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. init-build: `ohc-run.py init-build async_simple 1.4 --url=https://github.com/alibaba/async_simple/archive/refs/tags/1.4.tar.gz`
2. 安装GTest预编译包: `googletest 1.15.2`
3. cmake配置（需在源码目录创建build子目录）:
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_COMPILER=clang \
     -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_SYSTEM_NAME=Linux \
     -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DASYNC_SIMPLE_ENABLE_TESTS=ON \
     -DASYNC_SIMPLE_ENABLE_ASAN=OFF \
     -DASYNC_SIMPLE_DISABLE_AIO=ON \
     -DASYNC_SIMPLE_BUILD_DEMO_EXAMPLE=OFF \
     -DASYNC_SIMPLE_BUILD_MODULES=OFF \
     -DGTEST_INCLUDE_DIR=$DEFAULT_PREFIX/include \
     -DGTEST_LIBRARIES="$DEFAULT_PREFIX/lib/libgtest.a;$DEFAULT_PREFIX/lib/libgtest_main.a" \
     -DGMOCK_INCLUDE_DIR=$DEFAULT_PREFIX/include \
     -DGMOCK_LIBRARIES="$DEFAULT_PREFIX/lib/libgmock.a;$DEFAULT_PREFIX/lib/libgmock_main.a" \
     -DCMAKE_CXX_FLAGS="-std=c++20 -fPIC -O2 -Wno-error -Wno-deprecated-register -Wno-mismatched-new-delete -Wno-deprecated-declarations -D_FILE_OFFSET_BITS=64 -D__STDC_LIMIT_MACROS -D_GLIBCXX_USE_CXX11_ABI=1 -Wno-uninitialized -Wno-unused-value" \
     ..
   ```
4. make: `make -j2` — 编译成功
5. ctest: `ctest --output-on-failure -j2` — **5/5全部通过**
6. make install DESTDIR: `make install DESTDIR=$TEST_PREFIX` — staging安装成功
7. package: `ohc-run.py package async_simple 1.4`
8. make install（不带DESTDIR）: 部署到$DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | v1.4 tag URL 404 | async_simple使用不带v前缀的tag格式 | URL改为 `1.4.tar.gz`（不带v前缀） |
| 2 | OHOS CMAKE_SYSTEM_NAME=HarmonyOS导致uthread禁用 | CMakeLists.txt仅检测Linux/Darwin | 设置CMAKE_SYSTEM_NAME=Linux启用uthread [E092] |
| 3 | -Werror导致编译警告变成错误 | 原始CMakeLists.txt包含-Werror | 在CMAKE_CXX_FLAGS中覆盖为-Wno-error |
| 4 | libaio不可用 | OHOS不支持libaio | ASYNC_SIMPLE_DISABLE_AIO=ON |
| 5 | CMake FindGTest自动下载失败 | CMake 4.x与旧版GTest不兼容 | 手动指定GTest路径参数，使用预编译包 [E096] |

## 测试结果（真实执行）

```
Test #1: run_async_simple_test ........... Passed  2.03 sec
Test #2: run_async_simple_util_test ...... Passed  0.04 sec
Test #3: run_async_simple_coro_test ....... Passed 17.86 sec
Test #4: run_async_simple_executor_test .. Passed  0.03 sec
Test #5: run_async_simple_uthread_test ... Passed  1.73 sec

100% tests passed, 0 tests failed out of 5
Total Test time (real) = 17.95 sec
```

- uthread测试通过，确认 aarch64 上下文切换汇编代码在 OHOS 上运行正确
- 协程测试耗时最长（17.86s），覆盖Lazy/Mutex/Semaphore/Generator等核心功能

## 源码修改

无源码修改。所有适配通过cmake参数完成，无需补丁。

## 依赖版本

- pthread（系统内置）
- googletest 1.15.2（预编译包安装）

## Staging验证

```bash
# 库文件
$ file libasync_simple.so.1.3 → ELF shared object, 64-bit LSB arm64, stripped
$ ls libasync_simple_static.a → 428KB

# 头文件
$ ls include/async_simple/*.h → 14个主头文件
$ ls include/async_simple/coro/*.h → 17个协程头文件
$ ls include/async_simple/uthread/*.h → 5个uthread头文件

# CMake配置
$ ls share/async_simple/ → async_simple-config.cmake + targets文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libasync_simple.so.1.3 | 346KB→100KB(stripped) | 共享库（含uthread aarch64汇编） |
| libasync_simple.so → .so.1 → .so.1.3 | 符号链接 | 版本化soname |
| libasync_simple_static.a | 428KB | 静态库 |
| include/async_simple/*.h | 头文件 | C++20异步框架头文件 |
| share/async_simple/*.cmake | CMake配置 | find_package支持 |

## 注意事项

- async_simple是C++20协程库，链接需确保-std=c++20
- CMAKE_SYSTEM_NAME必须设为Linux以启用uthread组件（含aarch64上下文切换汇编）
- 如需AIO支持需安装libaio并去掉ASYNC_SIMPLE_DISABLE_AIO
- 不带v前缀的tag格式：下载URL为 `1.4.tar.gz` 而非 `v1.4.tar.gz`
- 测试需安装GTest预编译包googletest 1.15.2，手动指定路径参数
---

**编译结束**: 2026-07-15 09:46
**最终状态**: built
