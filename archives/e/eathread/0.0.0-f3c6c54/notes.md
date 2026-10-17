# eathread 0.0.0-f3c6c54 适配笔记

## 编译环境
- 构建系统: cmake（EAThread 为 CMake 库；conan-init 误判 autotools，配方手写重写）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（finish 后转 published）

## 编译步骤

1. 环境核验：python3 3.12.9 / conan 2.29.1 / clang 15.0.4；依赖 eabase/0699a15 已在 ohpcd 发布（conan download --only-recipe 验证 revision 5f0ae7b6…）。
2. 官方源码：https://github.com/electronicarts/EAThread 提交 f3c6c54d19699639a5edcf5237ea8b71aca6842c（UPstream 主题 commit "Replace submodules with CMake's FetchContent"）。
   - github.com 直连超时，经官方 codeload.github.com 下载 archive tarball，SHA-256 = 242cc6cb078bba9d2b943336d23179d23cb64e9654f80851c53da424eccb3506。
3. conandata.yml 使用官方 HTTPS URL（https://github.com/electronicarts/EAThread/archive/<sha>.tar.gz），无 file:///缓存/代理污染。
4. 库构建：`conan create archives/e/eathread/0.0.0-f3c6c54 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`
   - 生成的 libEAThread.a + include/eathread/* 头文件，安装规则由补丁补充。
5. 上游测试：独立工程（test/ 为根，EATHREAD_BUILD_TESTS=ON），6 个 EA 子模块（EABase/EAAssert/EAStdC/EAMain/EATest/EASTL）用官方固定提交 tarball 解压到 test/packages/ 并以 FETCHCONTENT_SOURCE_DIR_#### 指向本地，FETCHCONTENT_FULLY_DISCONNECTED=ON 避免网络；EAThreadTest 18 个 AddTest 注册套件全部 PASSED（RETURNCODE=0）。
6. test_package：消费者测试（Mutex/AutoMutex/Semaphore/Thread/ThreadFactory/AtomicInt32，真实 API 调用+可观察结果断言）+ 鸿蒙专项测试（屏障、affinity 路径、callstack 便携回退），conan create 内 2/2 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 配方 | init_build 按 URL 猜 `{BUILD_SYSTEM}` 误判 | 手写 CMake 配方（apply_conandata_patches + CMakeToolchain） |
| 2 | 上游 CMakeLists FetchContent 拉 EABase | EA 家族循环子模块；网络不可达 | 补丁 0001：改 find_package(eabase REQUIRED) + eabase::eabase，并补充 install 规则（上游没有） |
| 3 | eabase include 目录未传播到 test_package | eabase 二进制包元数据（conaninfo.txt 为空）在传递依赖场景下不提供 includedirs | test_package 显式 `requires("eabase/0699a15")`，CMakeDeps 直接为消费者求值配方 include 目录 |
| 4 | pthread_setcancelstate / pthread_setaffinity_np 未声明 | OHOS musl sysroot 不提供这两个 glibc 扩展 | 补丁 0002：取消态调用跳过；affinity 改 syscall(__NR_sched_setaffinity)（与 EA 上游 Android 分支同思路），eabase 笔记已记载同类平台限制 |
| 5 | OHOS 专项测试挂起 | 测试自身信号量消费后未再 Post | 修正测试代码（补充 Post），验证通过 |

## 源码修改

- patches/0001-CMakeLists.txt.patch：
  - CMakeLists.txt：移除 FetchContent，find_package(eabase) 链接 eabase::eabase；新增 install(TARGETS EAThread / DIRECTORY include/eathread / FILES LICENSE)
- patches/0002-source-unix-eathread_barrier_unix.cpp.patch：
  - source/unix/eathread_barrier_unix.cpp：`#if defined(PTHREAD_CANCEL_DISABLE) && !defined(__OHOS__)`（两处）
- patches/0003-source-unix-eathread_thread_unix.cpp.patch：
  - source/unix/eathread_thread_unix.cpp：新增 `#elif defined(__OHOS__)`，用 syscall(__NR_sched_setaffinity)
- patches/0004-source-unix-eathread_unix.cpp.patch：
  - source/unix/eathread_unix.cpp：affinity 分支排除 `__OHOS__`，落入 "other Unix platforms" no-op 分支

## 上游测试双口径台账

见 reports/test-report.md。统计口径说明：
- source_declared_total = 18：test/CMakeLists.txt file(GLOB "thread/source/*.cpp") 收录 18 个测试源文件，各对应 TestThread.cpp 中 1 个 AddTest 注册套件（Atomic/Barrier/Callstack/Condition/EnumerateThreads/Futex/Misc/Mutex/RWMutex/RWSemaphore/RWSpinLock/Semaphore/SmartPtr/SpinLock/Storage/Sync/Thread/ThreadPool）。
- test/dllsafety、test/interprocess_test 无独立 CMakeLists，未纳入上游主测试目标（非独立注册用例，台账中列出但按【框架/独立子目录】分类）。
- 上游测试框架所需 6 个 EA 子模块均未发布到 ohpcd（eatest/eastdc/eamain/eaassert/eastl 复核 Recipe not found），故测试框架以官方固定提交 tarball 本地组装（nose 视为 scratch，不进入交付物）。

## 鸿蒙专项测试

test_package/test_eathread_ohos.cpp：屏障构造、affinity 路径、callstack 便携回退、线程+互斥+信号量握手，全部 PASSED。与上游 18 套件、消费者测试分别计数。

## 非 CLI 库

构建产物仅 libEAThread.a + 头文件，无可执行文件 → 不需要 commands.json（R38）。
---

**编译结束**: 2026-09-16 14:00
**最终状态**: built
