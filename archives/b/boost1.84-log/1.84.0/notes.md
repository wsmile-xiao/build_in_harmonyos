# boost1.84-log 1.84.0 编译笔记

## 任务信息
- 开始时间：2026-09-05 14:00 (UTC)
- 认领人：2404_87638649
- 平台分支：feat/boost1.84-log-1.84.0
- 底稿：仓库 main 的 archives/b/boost/1.84.0/（元包）

## 选型与形态（独立评估）
boost 组件拆分包任务，并行任务 boost1.84-atomic/url/datetime/logsetup/serialization 在打样但
均未产出成品（worktree 为空、remote 无分支）。独立评估选定形态：

- **包名**：boost1.84-log/1.84.0（与并行任务命名系列一致）
- **依赖**：boost/1.84.0 元包（在仓，提供全部 boost headers + libboost_filesystem/regex/
  program_options/iostreams）
- **产物**：4 个静态库
  - libboost_log.a（35 对象：31 公共源 + syslog_backend + posix/object_name + posix/ipc_reliable_message_queue）
  - libboost_log_setup.a（9 对象：settings/filter/formatter 解析器）
  - libboost_atomic.a（lock_pool.cpp——log 的 event/once_block 需要 lock_pool 符号）
  - libboost_thread.a（pthread/thread.cpp + once.cpp + future.cpp——log 的 thread_specific 需要 tss 符号）
- **静态库理由**：与元包一致（package_type=static-library；b2 不兼容 OHOS 无法产 .so）

## 编译系统
Boost b2 在 OHOS 不兼容（E068，元包已记录），沿用元包手动编译模式：
逐 .cpp 编译（clang++）→ llvm-ar rcs 打包。

## 关键技术点
1. **平台补丁**：复用元包 0001-ohos-pthread-cancel-fix.patch（BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
   OHOS musl 无 pthread_setcancelstate）。
2. **x86 SIMD 排除**：dump_avx2.cpp/dump_ssse3.cpp 引 immintrin.h 在 aarch64 直接 #error；
   上游 b2 也按架构排除（select-arch-specific-sources），故不编译，与上游行为一致。
3. **目录内 include**：libs/log/src 根、setup/、posix/ 相互 include 同目录 .hpp，需
   -Ilibs/log/src；atomic 的 lock_pool.cpp include 同目录 lock_pool_init1.ipp，需 -Ilibs/atomic/src。
4. **regex 不需要**：符号分析确认 log/log_setup 未引用 boost::re_detail/basic_regex 符号
   （Jamfile 的 select-regex-backend 实际用 Spirit header-only 解析）。元包 regex 仍在链接命令中
   （保守起见），实际未使用也可不链。
5. **版本 ABI 陷阱（重要）**：本地 conan 缓存中曾存在旧版 boost/1.84.0 二进制（含
   absolute_v3/v4 版本化符号，1.85+ 机制），与 1.84.0 源码（非版本化 detail::absolute）不一致，
   导致链接 undefined symbol。`conan remove boost/1.84.0 -c` 重拉后符号正确。CI 干净环境无此问题。
6. **ABI tag**：v2s_mt_posix（多线程 posix），与元包一致。

## 上游测试（rule4 修复：真跑上游 57 个测试目标，替代 tutorial 示例）
- 2026-09-06 人工审核（Septest）打回：上游 N=54 但 PR 只报 tutorial 示例 2/2——示例不算测了上游。
- 修复：build() 内 `_run_upstream_tests` 直接真跑 libs/log/test/Jamfile.v2 注册的全部测试目标（绕过 b2，
  clang++ 直编直跑，模式同 boost1.84-atomic 的 _run_upstream_tests）：
  - **[ run ] × 52**：run/*.cpp 每文件一个测试目标（不折叠、不变体合并），链接
    log_setup + log + filesystem（元包）+ thread + atomic + unit_test_framework（测试期编）+ chrono（测试期编）
    - filt_matches_boost_regex 额外链元包 libboost_regex.a；spirit/xpressive/std_regex 后端 header-only
    - 3 个 IPC 测试（util_ipc_object_name / util_ipc_reliable_mq / sink_text_ipc_mq_backend）在 OHOS
      musl 真实运行通过：shm_open/mman.h 有声明，boost.log.pgid.* 共享段挂载可用；
      ipc_sync_wrappers 不走 robust mutex 路径（OHOS musl 无 pthread_mutexattr_setrobust 声明，
      上游本就有 #if 守卫，b2 configure 探测失败时自动降级，非平台阻塞）
  - **[ compile ] × 4**：compile/*.cpp（self_contained_header.cpp 除外——它是 b2 glob-tree 按
    每个公共头展开的模板，不是独立注册目标），-fsyntax-only 判定
  - **[ compile-fail ] × 1**：attr_functor_void_return.cpp，编译失败才算通过
- 测试期依赖（编译不打包）：boost_unit_test_framework（19 TU）+ boost_chrono（3 TU，
  BOOST_CHRONO_SOURCE——util_ipc_reliable_mq.cpp 用 boost::this_thread::sleep_for(chrono)，
  元包无 libboost_chrono.a；DONT_USE_CHRONO 是库 TU 编译宏，测试消费端须启用 chrono 路径）
- 超时控制：_run_cmd 进程组 SIGKILL（编译 600s / 运行 300s），libc++_shared.so 用
  `clang++ -print-file-name` 自省注入 LD_LIBRARY_PATH
- **实测结果：57/57 通过（run 52 + compile 4 + compile-fail 1），0 失败**
- 报告文件：build_folder/upstream-tests-report.txt
- test_package：自写 8 断言功能测试（trivial/sink/formatter/setup/filesystem 联动/文件 sink）8/8 通过

## 验证结果
- 38+5 编译单元全部通过（clang 15.0.4, aarch64-unknown-linux-ohos, -O2 -DNDEBUG）
- 上游测试 57/57 全过（2026-09-06 conan create 实测，RC=0）
- 功能测试程序本地（鸿蒙 PC）运行通过：EXIT=0
  - trivial 全 6 级别日志 ✅
  - 自定义同步 sink + LineID counter + smessage formatter ✅
  - named_scope 属性 ✅
  - init_from_stream 解析 ini 设置 + 创建 console sink ✅
  - text_file_backend 文件写入 ✅

## 组件依赖方向
- log → atomic + thread + boost::filesystem（元包）+ headers
- log_setup → log
- thread → atomic + headers
- atomic → 自含
---

**编译结束**: 2026-09-05 17:41（首轮）
**rule4 修复**: 2026-09-06（上游测试 57/57 真跑通过）
**最终状态**: published
