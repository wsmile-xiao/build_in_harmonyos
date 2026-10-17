# boost1.84-stacktrace_basic 1.84.0 适配笔记

## 任务背景

- **任务**：积分赛 #6070 — boost 1.84 组件拆分包（stacktrace_basic）
- **认领人**：calbee21
- **平台分支**：feat/boost1.84-stacktrace_basic-1.84.0
- **底稿**：仓库 main 的 archives/b/boost/1.84.0/ 元包（filesystem/regex/program_options/iostreams 四库手动编译）
- **开始时间**：2026-09-06

## 形态选型（组件包形态评估）

**结论：独立裁剪包（自编译 libboost_stacktrace_basic.a + 完整头文件树），不 requires 元包。**

### 方案 A：requires 元包（boost/1.84.0）——否决

1. **元包不含 stacktrace**：`archives/b/boost/1.84.0/conanfile.py` 只编译
   filesystem/regex/program_options/iostreams 四个库，无
   libboost_stacktrace_basic.a，也未声明 boost_stacktrace_basic 组件——
   requires 元包拿不到 `Boost::stacktrace_basic` 目标。
2. **cmake_file_name 冲突**：元包声明 "Boost"。组件包用独立包名
   boost1.84-stacktrace_basic 即可共存（atomic/timer/contract 同款结论）。

### 方案 B：独立裁剪包（选定）

- 上游 `libs/stacktrace/build/Jamfile.v2` 定义 6 个库变体
  （noop/backtrace/addr2line/basic/windbg/windbg_cached）。
  **basic**（本包）：`lib boost_stacktrace_basic : ../src/basic.cpp`，
  requirements 仅 `<target-os>linux:<library>dl`——**无 libbacktrace、
  无 addr2line 子进程、无 WinDbg 依赖**，是 OHOS 上依赖面最干净的可编译形态。
- aarch64 Linux/OHOS 上只需编译 **basic.cpp 一个翻译单元**。

## OHOS musl 平台能力实测（2026-09-06，clang 15 / aarch64-linux-ohos）

任务要求"backtrace/backtrace_symbols 可用性要实测——无 ptrace/dladdr 等
限制项，实测什么可用用什么模式"。逐项实测结果：

| 能力 | 实测结果 | 证据 |
|------|---------|------|
| `backtrace()`（execinfo.h） | ✅ 可用，返回 3 帧 | t2.cpp 探测程序 rc=0 |
| `dladdr()` | ✅ 可用，`dli_sname` 返回 "main" | t2.cpp 探测程序 |
| `_Unwind_Backtrace`（basic 帧收集路径） | ✅ 可用 | t1/t3 探测程序捕获 4-6 帧 |
| 帧名解析（dladdr + -rdynamic） | ✅ 可读函数名（foo()/main/_start_c） | t3.cpp 输出 |
| ptrace | 未使用（basic 模式不需要） | — |
| backtrace_symbols | 未使用（basic 模式用 dladdr + boost::core::demangle） | — |

**结论：basic 模式在 OHOS 上完全可用。** header-only 消费
（默认，`#include <boost/stacktrace.hpp>`）与链接库消费
（`-lboost_stacktrace_basic`）均实测通过。

## 编译过程

- 源码：boost_1_84_0.tar.gz（SHA256 与元包 conandata.yml 一致：
  a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724，
  官方 archives.boost.io URL——单 URL 纪律，多 URL 会关掉 CI mirror fallback #8512）
- 方式：手动编译（b2 在 OHOS SHELL 执行机制不兼容 E068；Boost CMake 是
  superproject 模式不支持独立构建——底稿 notes.md 已验证）
- 编译命令：clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC -I<root>
  -DBOOST_ALL_NO_LIB -c libs/stacktrace/src/basic.cpp →
  llvm-ar rcs libboost_stacktrace_basic.a
- 打包：完整 boost/ 头文件树 + libboost_stacktrace_basic.a
- 无需额外补丁：basic.cpp 不使用 OHOS 缺失 API（_Unwind_*/dladdr 均在）；
  0001 patch 是下游消费 boost/thread 头文件时的守卫（与元包同款）。

## 上游测试（N=23，绕 b2 手动编译运行；2026-09-07 rule4 复核修订 17→23）

b2 不可用，沿用元包"手动编译上游测试源文件并真实运行"的做法。

上游 `libs/stacktrace/test/Jamfile.v2`（boost-1.84.0 实测）test-suite
stacktrace_tests 注册 74 个 run 目标，按 6 种实现变体 × 3 种链接形态 ×
2 种调试符号展开。**OHOS musl 上可跑的实现变体共两种：basic + noop，
合计 23 个目标**（初版仅按"本包交付形态=basic"口径报 17，人工审核
#8653 rule4 判少报，2026-09-07 扩测 noop 6 目标修订为 23）：

| # | 测试目标 | 上游注册名 | 类型 | 结果 |
|---|---------|-----------|------|------|
| 1 | test.cpp+test_impl.cpp | basic_ho | run（dbg on） | PASS |
| 2 | test.cpp+test_impl.cpp（NO_DEBUG_AT_ALL） | basic_ho_empty | run | PASS |
| 3 | test_trivial.cpp | trivial_basic_ho | run | PASS |
| 4 | test.cpp+test_impl.cpp+basic.cpp | basic_lib | run | PASS |
| 5 | test_trivial.cpp（链接库） | trivial_basic_lib | run | PASS |
| 6 | test.cpp+test_impl.cpp（dbg off） | basic_ho_no_dbg | run | PASS |
| 7 | test.cpp+test_impl.cpp（lib+off） | basic_lib_no_dbg | run | PASS |
| 8 | thread_safety_checking.cpp | basic_lib_threaded | run | PASS |
| 9 | thread_safety_checking.cpp（off） | basic_lib_no_dbg_threaded | run | PASS |
| 10 | test_void_ptr_cast.cpp | test_void_ptr_cast | run | PASS |
| 11 | test_num_conv.cpp | test_num_conv | run | PASS |
| 12 | example/assert_handler.cpp | basic_assert_handler | run | PASS |
| 13 | example/debug_function.cpp | basic_debug_function | run | PASS |
| 14 | example/terminate_handler.cpp | basic_terminate_handler | run | PASS |
| 15 | example/throwing_st.cpp | basic_throwing_st | run | PASS |
| 16 | example/trace_addresses.cpp | basic_trace_addresses | run | PASS |
| 17 | example/user_config.cpp | basic_user_config | run | PASS |

（example 的 dbg on/off 两个注册折叠为 1 项/例计数，标签 basic_<name>。）

noop 变体 6 目标（2026-09-07 扩测新增）：

| # | 测试目标 | 上游注册名 | 类型 | 结果 |
|---|---------|-----------|------|------|
| 18 | test_noop.cpp+test_impl.cpp | noop_ho | run（NOOP 宏） | PASS |
| 19 | test_trivial.cpp | trivial_noop_ho | run | PASS |
| 20 | test_noop.cpp（链接 noop 库） | noop_lib | run | PASS |
| 21 | test_trivial.cpp（链接 noop 库） | trivial_noop_lib | run | PASS |
| 22 | test_noop.cpp（dbg off） | noop_ho_no_dbg | run | PASS |
| 23 | test_noop.cpp（库+off） | noop_lib_no_dbg | run | PASS |

noop 库形态链接辅助库 libboost_stacktrace_noop.a（libs/stacktrace/src/
noop.cpp 就地编译，上游 lib boost_stacktrace_noop 等价物；不随包交付）。

**实测结果：23/23 通过（100%）**，conan create 全绿（2026-09-07，
日志 ~/tmp/st-create2.log，TOTAL 23: 23 passed / 0 failed）。

**不纳入的变体（三选一理由）**：
- backtrace/addr2line/windbg/windbg_cached 变体（约 50 目标）：
  **非本包交付形态**——backtrace 需 libbacktrace 系统库（OHOS 无此库，
  且上游 `check-target-builds libbacktrace` 检测失败会 `<build>no` 跳过）；
  addr2line 需运行时子进程调用外部 binutils 工具；windbg 系 Windows 专用。
- torture_basic_*（4 目标）：上游 `explicit stacktrace_torture`——
  "Very long tests"（torture.cpp 循环 1000 万次），上游默认也不跑。
- noop 变体（约 8 目标）：属 boost_stacktrace_noop 库（另一个编译库），
  非本包（basic）范围。

### 辅助库处理（测试期构建，不随包交付）

- thread_safety_checking 需 `/boost/thread` + `/boost/timer`：源码树
  libs/thread/src（pthread/once.cpp+thread.cpp）与 libs/timer/src
  （auto_timers_construction.cpp+cpu_timer.cpp）就地编译为辅助静态库
  （文件集与 boost1.84-thread/timer 组件包一致，timer 包同款做法）。
- terminate_handler example 需 filesystem+system：源码树
  libs/filesystem/src 9 个 TU 就地编译（文件集与元包一致）。
- package() 只打包 libboost_stacktrace_basic.a。

## 遇到的问题与平台修复

### 问题 1：-O2 内联吞帧（basic_ho/basic_lib 5 断言失败）

- **症状**：test.cpp 的 `ss1.str().find("function_from_library")` 等 5 处断言失败
- **根因**：Release 配方 cxxflags 是 -O2，test_impl.cpp 的
  function_from_library 被内联进调用者，帧缺失
- **修复**：测试编译固定 `-O0 -g`——上游 b2 测试目标默认 debug 变体
  （-O0），这是上游语义的忠实复刻，不是修改测试

### 问题 2：no_dbg 变体栈展开提前终止（2 断言失败）

- **症状**：basic_ho_no_dbg 运行 rc=2：`ns1 != return_from_nested_namespaces()`
  与 `min_size > 2` 失败；stdout 显示 ns1 只收集到 1 帧
- **根因**：OHOS clang 15 在 `-O0` 且无 `-g` 时生成的 .eh_frame 不完整，
  _Unwind_Backtrace 提前终止（对照实验：同参数加 -g 即完整 19 帧；
  llvm-readelf 确认两二进制符号表均无 ICF 合并）
- **修复**：no_dbg 变体加 `-fasynchronous-unwind-tables`（强制完整异步
  展开表，等价上游 gcc 默认行为），保持无 -g（上游"无调试符号"语义）
- **实测**：加 flag 后 no_dbg 变体 rc=0

### 问题 3：thread 辅助库编译失败（pthread_setcancelstate）

- **症状**：libs/thread/src/pthread/thread.cpp 报 use of undeclared
  identifier 'pthread_setcancelstate'
- **根因**：配方 cxxflags 漏了 -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE
  （元包/atomic/timer 均带此宏，R8 特性检测宏由 patch 0001 消费）
- **修复**：cxxflags 补上该 define

### 问题 4：terminate_handler 链接失败

- **症状**：ld.lld undefined symbol: boost::filesystem::...
- **根因**：上游 Jamfile additional_dependency 是 filesystem+system+rt，
  但 boost_system 1.84 是 header-only（无 libboost_system.a，-l 链接失败）；
  rt 已并入 musl libc
- **修复**：只链接辅助 libboost_filesystem.a（源码树 9 个 TU 就地编译，
  文件集与元包一致）；system 头文件随源码树，rt 省略

## W0 依赖检查（R36）

- boost/1.84.0 元包：已发布（conan download --only-recipe 确认，本包最终未 requires）
- zlib/1.3.1：已发布（stacktrace 不依赖 zlib，仅底稿参考）
- **本包 requirements：无**（basic.cpp 仅依赖 unwind + dl，均系统提供）

## 结论

独立裁剪包形态，手动编译 libboost_stacktrace_basic.a，上游测试 23/23
通过（basic 17 + noop 6，OHOS musl 可跑变体全量；2026-09-07 rule4 复核
修订），test_package smoke test 18 断言通过。适配完成于 2026-09-06，
扩测修订于 2026-09-07。
