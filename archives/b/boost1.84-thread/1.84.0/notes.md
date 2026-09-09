# boost1.84-thread 1.84.0 适配笔记

## 软件定位

boost1.84-thread 是 Debian 风格的 Boost.Thread 单库拆分包（对应 Debian
libboost-thread1.84-dev）：不重复打包完整 boost 元包，而是从 boost 1.84.0
源码树独立裁剪编译出 libboost_thread.a 并只携带 Thread 组件所需头文件，
与其他 boost1.84-* 拆分包并行安装互不冲突。

## 编译环境
- 构建系统: custom（手动编译，b2 在 OHOS 不兼容 E068）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15（OHOS SDK）
- 状态: built

## 编译步骤

1. 下载 boost 1.84.0 完整 tarball（sha256 a5800f40...，与 archives/b/boost/1.84.0 同源）。
2. 打 0001 补丁（sp_thread_sleep.hpp：BOOST_SP_NO_PTHREAD_SETCANCELSTATE
   feature-detection 宏绕开 OHOS musl 缺失的 pthread_setcancelstate）。
3. 手动编译 libs/thread/src 下 5 个源文件（对齐上游
   libs/thread/build/CMakeLists.txt 的 boost_thread_src 清单）：
   future.cpp、tss_null.cpp、pthread/once.cpp、pthread/once_atomic.cpp、
   pthread/thread.cpp
4. `llvm-ar rcs libboost_thread.a *.o`
5. 打包：boost/thread/** 头文件 + Thread 传递依赖头文件集 + libboost_thread.a

关键编译参数：
```
-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC -I<boost_root>
-DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED
-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE
```

## 依赖版本

无 conan 依赖（Thread 编译不依赖 zlib 等外部库；chrono/system 为
header-only 使用形态）。系统库 pthread。

## 验证结果

```bash
conan create archives/b/boost1.84-thread/1.84.0 \
  -pr:h=<ohos-aarch64> -pr:b=default --build=missing
# → boost1.84-thread/1.84.0 Package created
# → 上游测试 30/30 PASS（子集，覆盖 Thread 核心功能面）
# → test_package: test_boost_thread PASSED
```

上游测试子集（30 项，绕过 b2 手动编译运行）：
- test/test_thread、test_thread_id、test_thread_launching、test_thread_move、
  test_thread_move_return、test_thread_mf、test_thread_exit、
  test_hardware_concurrency、test_physical_concurrency
- test_mutex、test_once、test_tss、test_condition*（4 项）、test_futures、
  test_generic_locks、test_lock_concept、test_move_function、
  test_shared_mutex*（2 项）
- example/thread、mutex、condition、once、future_then、producer_consumer、
  thread_guard、scoped_thread

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sp_thread_sleep 引用 pthread_setcancelstate 链接失败 | OHOS musl 不提供该 API | 补丁 0001 + BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏（R8：feature-detection 而非平台宏） |
| 2 | 测试可执行文件运行 rc=127 | 动态链接的 libc++_shared.so 不在默认搜索路径 | clang++ -print-file-name 自省注入 LD_LIBRARY_PATH（先例 boost/1.85.0） |
| 3 | b2 无法运行上游测试 | b2 SHELL 执行机制 OHOS 不兼容（E068） | 手动编译测试源文件直接运行，统计通过率写报告 |

## 注意事项

- 与 boost1.84 本体（archives/b/boost1.84/1.84.0）关系：不同包名，前者为
  Thread 单库拆分形态；两者可并行安装（include 路径同为 include/boost，
  lib 仅 libboost_thread.a，无文件冲突）。
- Thread 的传递依赖头文件集取自上游 CMakeLists 的
  target_link_libraries 清单，未打包的组件头文件（filesystem/regex 等）
  不在本包内。
---

**编译结束**: 2026-09-06 01:41
**最终状态**: built
