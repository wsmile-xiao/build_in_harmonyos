# boost1.84-fiber 1.84.0 适配笔记

## 软件定位

boost1.84-fiber 是 Boost.Fiber 单库拆分包（对应 Debian libboost-fiber1.84-dev）：
从 boost 1.84.0 源码树独立编译 libboost_fiber.a（16 TU），以**依赖模式**
消费已发布的 boost1.84-context/1.84.0 包提供的 fcontext 实现（libboost_context.a），
不重复编译 fcontext 汇编。与其他 boost1.84-* 拆分包并行安装互不冲突。

## 编译环境
- 构建系统: custom（手动编译，b2 在 OHOS 不兼容 E068）
- 编译日期: 2026-09-13
- 编译器: clang/clang++ 15（OHOS SDK）
- 状态: built

## 编译步骤

1. 下载 boost 1.84.0 完整 tarball（sha256 a5800f40...，与 archives/b/boost/1.84.0 同源）。
2. 打 0001 补丁（sp_thread_sleep.hpp：BOOST_SP_NO_PTHREAD_SETCANCELSTATE
   宏门控注入——上游 1.84 源码只认 __ANDROID__，OHOS musl 无
   pthread_setcancelstate；与 thread #8554 同一补丁）。
3. 手动编译 libs/fiber/src 的 16 个源 TU（对齐上游
   libs/fiber/build/Jamfile.v2 `lib boost_fiber` 源清单）：
   algo/{algorithm,round_robin,shared_work,work_stealing}.cpp +
   barrier/condition_variable/context/fiber/future/mutex/properties/
   recursive_mutex/recursive_timed_mutex/scheduler/timed_mutex/waker.cpp
4. `llvm-ar rcs libboost_fiber.a *.o`
5. 打包：完整 boost/ 头树 + libboost_fiber.a（utf/thread/chrono 为测试期
   依赖，never packaged）

关键编译参数：
```
-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -g0 -fPIC -I<boost_root>
-DBOOST_ALL_NO_LIB -DBOOST_FIBER_SOURCE -DBOOST_FIBERS_SOURCE
-DBOOST_FIBERS_STATIC_LINK -DBOOST_CONTEXT_STATIC_LINK
-DBOOST_THREAD_DONT_USE_CHRONO=1 -DBOOST_SYSTEM_NO_DEPRECATED
-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE
```

NUMA 库（boost_fiber_numa）默认 off 不打包（Jamfile numa conditional rule）；
segmented stacks 默认 off（符合 OHOS，musl 无 addcontext 族 API）。

## 依赖版本

- conan 依赖：boost1.84-context/1.84.0（已发布，fcontext 汇编 + posix
  stack_traits——libboost_fiber.a 的所有 fcontext 符号在链接期由消费者
  从该包解析，本包不携带）
- 系统库 pthread

## CMakeDeps 双包聚合实测（关键发现，conan 2.29.1）

fiber requires context 后，若两包同用 cmake_file_name="Boost"：
- CMakeDeps 聚合的 BoostConfig.cmake 只保留**一个属主包**的组件
  （实测字母序 boost1.84-context 赢，fiber 的组件被静默丢弃、无警告）
- find_package(Boost COMPONENTS fiber) 会失败（组件不存在）
- 对策（本包采用）：fiber 用独立 cmake_file_name="boost1.84-fiber"
  （boost1.84-log 先例同款），组件 requires 用全限定名
  "boost1.84-context::boost_context"（跨包组件引用，链接期正确解析）
- 消费者姿势：`find_package(boost1.84-fiber REQUIRED CONFIG)` +
  `target_link_libraries(... boost1.84-fiber::boost_fiber)`

## 上游测试集成（rule 4/5，绕 b2 手动编译）

测试面：libs/fiber/test/Jamfile.v2 注册 32 个 [ run ] 目标：
- minimal 套件（asm + native）：13 个共享测试源 x post/dispatch = 26
- extra 套件（extra-asm + extra-native）：mt 测试 3 源 x post/dispatch = 6

全部 init_unit_test_suite 模式（无自带 main），链接要求：
- boost_unit_test_framework（19 TU 本地编译，never packaged）
- boost_fiber + boost_context（依赖包 libboost_context.a）
- 6 个 mt 测试：libboost_thread.a（5 TU，thread #8554 同源集合）+
  libboost_chrono.a（3 TU，BOOST_CHRONO_SOURCE）——boost::barrier /
  boost::this_thread::sleep_for(boost::chrono::milliseconds) 需要

测试编译要点：
- 测试侧去掉 -DBOOST_THREAD_DONT_USE_CHRONO（mt 测试需要
  BOOST_THREAD_USES_CHRONO 默认开启才有 sleep_for）
- 测试编译降档 -Os -DNDEBUG -g0（context 包 CI-021 低内存教训：
  纤维模板实例化在 -O2 链接期内存峰值高；库本体保持 -O2）

运行：LD_LIBRARY_PATH 注入 SDK libc++_shared.so（clang++ -print-file-name
自省，无硬编码 SDK 版本；musl 加载器仅经 shell 启动时遵守
LD_LIBRARY_PATH，经 bash export 注入）。

结果：**32/32 PASS**（26 minimal + 6 mt 全过，含 boost::thread 宿主线程
争用 fibers::mutex 的多线程场景）。

## 验证结果

```bash
conan create archives/b/boost1.84-fiber/1.84.0 \
  -pr:h=<ohos-aarch64> -pr:b=default --build=missing
# → boost1.84-fiber/1.84.0 Package created
# → 上游测试 32/32 PASS（build() 内 _run_upstream_tests）
# → test_package: test_boost_fiber ALL OK（10 组断言）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sp_thread_sleep 引用 pthread_setcancelstate 编译失败（utf TU） | OHOS musl 不提供该 API；上游 1.84 源码宏门控只认 __ANDROID__ | 补丁 0001 把门控改为 `!defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)`（thread #8554 同款；纯 -D 宏不够，必须改源码门控） |
| 2 | test_mutex_mt 编译报 no member named 'sleep_for' in namespace 'boost::this_thread' | 库侧编译选项 -DBOOST_THREAD_DONT_USE_CHRONO 泄漏到测试 TU，禁用了 sleep_for 声明 | 测试 flags 去掉 DONT_USE_CHRONO（log #8609 先例） |
| 3 | test_mutex_mt 链接报 undefined boost::chrono::steady_clock::now() | BOOST_THREAD_USES_CHRONO 拉入 boost::chrono 符号，需 libboost_chrono.a | 测试期依赖本地编 3 TU（chrono/process_cpu_clocks/thread_clock，BOOST_CHRONO_SOURCE），never packaged |
| 4 | 双包 cmake_file_name=Boost 撞名时 fiber 组件消失 | conan 2.29.1 CMakeDeps 聚合只保留属主包组件（字母序），后者静默丢弃 | fiber 用独立 cmake_file_name=boost1.84-fiber + 组件 requires 全限定名 boost1.84-context::boost_context（probe 实测） |

## 注意事项

- 与 boost1.84-coroutine（自包含路线，包内自带 context 源）不同，本包按
  任务 #6055 要求走依赖模式：libboost_context.a 来自 boost1.84-context 包，
  消费者 conan install 时自动拉取传递依赖。
- include 树与 context 包一致为完整 boost/ 头树（Boost 库间头文件传递
  依赖强；两包头树内容相同，并行安装无冲突）。
- 消费者 CMake 目标：`boost1.84-fiber::boost_fiber`（独立 config，非
  Boost::fiber 短名）。
