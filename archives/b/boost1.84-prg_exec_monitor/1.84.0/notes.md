# boost1.84-prg_exec_monitor 1.84.0 适配笔记

## 组件定位

Boost.ProgramExecutionMonitor（boost_prg_exec_monitor 库）是 Boost.Test
家族中最轻量的执行监控入口：为简单测试程序提供 `cpp_main` 入口，捕获
非零返回值、未捕获异常、系统信号（SIGFPE/SIGSEGV 等）、assert 失败，
统一转译为结构化错误报告（"errors detected; see standard output for
details"）与非零退出码。不含 unit_test_framework 的测试树/日志框架。

本包以独立包名 `boost1.84-prg_exec_monitor` 归档（积分赛任务 6065），
与 `boost/1.84.0` 元包、`boost1.84-container`/`boost1.84-date_time`
同系列组件包并行维护。

## 编译环境
- 构建系统: manual-clang（b2 在 OHOS 不兼容 E068，手动 clang++ 编译）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## W0b 历史经验核验（底稿 boost/1.84.0 notes.md）

底稿关键结论逐项核验：
1. **b2 构建系统失败**（clang++ --version SHELL 执行错误，E068）→
   属实。上游构建走 manual-clang 路线，与同系列 container/date_time 一致。
2. **pthread_setcancelstate 不可用**（OHOS musl）→ 属实，实测编译
   test 库源码时经 smart_ptr 头链引入 sp_thread_sleep.hpp 报
   `use of undeclared identifier 'pthread_setcancelstate'`，复用元包
   0001 补丁 + BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏解决。
3. 环境语义可迁移性：本包全部命令（clang++/llvm-ar/shell）在 CI 环境
   均存在（CI 能力矩阵 gcc/clang/make/cmake ✅），无 Rust/OCaml 类
   工具链缺口。

## 形态

- `package_type = "static-library"`：产出 libboost_prg_exec_monitor.a
  （上游 PRG_EXEC_MON_SOURCES 同源集合：execution_monitor.cpp +
  debug.cpp + cpp_main.cpp，均为 BOOST_TEST_SOURCE 转发翻译单元）
- 安装完整 boost/ 头树（库间传递 include 强依赖，与同系列一致）
- 依赖：无 conan 依赖（zlib 仅元包 iostreams 需要，本包不涉及）

## 上游测试集成（4/4 全绿，run-fail 语义）

上游测试套件位于 `libs/test/test/prg_exec_monitor-ts/`，实测 4 个
.cpp 测试源（与 boost_1_84_0.tarball 一致，人工审核可 clone 复核）。
**全部为 run-fail 型**（上游 Jamfile L220-225 以
`[ boost.test-self-test run-fail : ... ]` 注册）：

| 测试 | 触发条件 | 上游注册模式 | 实测退出码 |
|------|---------|-------------|-----------|
| result-code-test | cpp_main 返回 -1 | run-fail, 静态链接 | 1（报告 error return code: -1） |
| system-exception-test | 整数除零（SIGFPE） | run-fail, 静态链接 | 1（信号转译非零） |
| uncatched-exception-test | 抛 C 字符串异常 | run-fail, included 单头 | 200（exception 205） |
| user-fatal-exception-test | NDEBUG 下返回 1 | run-fail, 静态链接 | 1 |

run-fail 语义说明：测试程序**故意**触发错误条件，验证 PEM 把错误
正确转译为非零退出码——退出码非零 = 测试通过（判定逻辑与普通测试
相反，与上游 b2 run-fail 判定一致）。

b2 在 OHOS 不可用（E068），本包在 conanfile.py `build()` 中：
1. 编译 PRG_EXEC_MON_SOURCES 同源集合归档 libboost_prg_exec_monitor.a
2. 逐个编译运行 4 个上游测试源（3 个静态链接 + 1 个 included 模式，
   与上游 Jamfile 注册一一对应），run-fail 判定：rc != 0 → PASS
3. 统计写入 `build_folder/upstream-tests-report.txt`

实测结果：**4/4 PASS（全部非零退出，符合 run-fail 预期）**

### 平台能力实测（为什么 PEM 信号处理在 OHOS 可用）

- `sigaltstack`/`SA_SIGINFO`/`siginfo_t`：OHOS musl 实测可用
  （SIGSTKSZ=12288，MINSIGSTKSZ=6144），无需 BOOST_TEST_DISABLE_ALT_STACK
- `debug.ipp` BOOST_LINUX_BASED_DEBUG 分支（sys/ptrace.h + /proc）：
  可编译；attach_debugger 的 fork/ptrace 路径仅在显式请求调试器时执行，
  正常测试不触发
- system-exception-test 的 SIGFPE 捕获路径实测工作（除零 → PEM 捕获 →
  非零退出而非裸崩溃）

### 运行时环境

OHOS 测试二进制动态依赖 SDK libc++_shared.so：通过
`clang++ -print-file-name=libc++_shared.so` 自省定位目录注入
LD_LIBRARY_PATH（无硬编码 SDK 版本路径）；musl 加载器仅在经 shell
启动时遵守该变量，故用 `export ...; ./exe` 形式运行（与
boost1.84-date_time/container 同款实测结论）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译 execution_monitor.cpp 报 `use of undeclared identifier 'pthread_setcancelstate'` | OHOS musl 无该函数；smart_ptr 头链引入 sp_thread_sleep.hpp | 复用元包 0001 补丁 + BOOST_SP_NO_PTHREAD_SETCANCELSTATE 宏（R8 特性检测宏，非平台宏） |
| 2 | run-fail 测试判定方向 | 上游 Jamfile 注册为 run-fail（非零退出=通过），与普通测试相反 | _run_upstream_tests 按 rc != 0 判定 PASS，MANIFEST/notes 注明语义 |
| 3 | uncatched-exception-test 链接方式 | 上游注册为 included（boost/test/included/prg_exec_monitor.hpp 单头自带实现），不链接库 | 按测试名单独走 included 编译（不 -lboost_prg_exec_monitor） |
| 4 | 运行报 Error loading shared library libc++_shared.so | 测试二进制动态依赖 SDK libc++ | 编译器自省定位 + LD_LIBRARY_PATH + bash export 形式运行 |
| 5 | 是否需要 zlib 依赖 | boost_prg_exec_monitor 三个源文件不涉及 iostreams | 无 conan requires（zlib 仅元包 iostreams 组件需要） |

## 源码修改
无补丁修改上游源码（含测试源，4 个 .cpp 逐字节未动）；0001 补丁为
元包已验证的 OHOS 平台适配补丁（sp_thread_sleep.hpp 三处宏守卫），
与上游 1.84.0 原始文件的最小差异。

## 依赖版本
- 无 conan 依赖
- 运行时依赖：libc++（OHOS sysroot）
