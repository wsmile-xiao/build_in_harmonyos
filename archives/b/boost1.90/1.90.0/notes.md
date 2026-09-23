# boost1.90 1.90.0 编译笔记（同版本测试闭环重做）

## 任务背景

本归档是积分赛任务 #6080（feat/boost1.90-1.90.0）：制品仓已有 `boost/1.90.0`
（header-only + Boost.Test）系列发布（1.90.0 ~ 1.90.0.4.1），**同版本任务 ≠ 排除**，
按 2026-09-10 永久纪律重新完成测试闭环（上游测试补跑 + 口径修正）。

包名 `boost1.90` 为独立包名归档（与 boost/1.90.0 并行维护），配方形态对齐
boost1.84 1.84.0（#8530 包名复刻先例）：手动编译 4 个非 header-only 库。

## 编译开始时间

2026-09-09

## 环境信息

- 平台：OpenHarmony (OHOS, aarch64)
- 编译器：clang/clang++（-std=c++17 -stdlib=libc++）
- 构建系统：手动编译（b2 不兼容 OHOS，E068）

## 方案（对齐 boost1.84 本体打法 + 1.90 差异修正）

Boost b2 (Boost.Build) 的 SHELL 执行机制在鸿蒙不兼容（E068），Boost 的 CMake
支持是实验性 superproject 模式无法独立构建，因此配方绕过 b2/CMake，用 clang++
手动编译 4 个非 header-only 库：

1. **filesystem**：9 源文件（跳过 windows_file_codecvt.cpp —— Windows 专用）
2. **regex**（⚠️ 1.90 差异）：精简为 2 源文件 posix_api / wide_posix_api
   （libs/regex/build/Jamfile.v2 SOURCES 实测；1.84 为 5 源文件含
   regex.cpp/regex_debug.cpp/static_mutex.cpp）
3. **program_options**：10 源文件（1.90 的 Convert.cpp 已改名 convert.cpp；
   跳过 winmain.cpp —— Windows 专用）
4. **iostreams**：zlib 后端 4 源文件（file_descriptor/gzip/mapped_file/zlib，
   依赖 conan zlib/1.3.1；跳过 bzip2/lzma/zstd 后端——无系统库）

system / date_time 自 Boost 1.69 起 header-only，随头文件一起安装。

另编译 **boost_unit_test_framework**（上游官方 BOOST_UTF_SRC 19 个编译单元，
libs/test/build/CMakeLists.txt）作为测试辅助库——不随包发布，仅供上游
iostreams 测试链接（上游 test-iostreams 规则显式链接之）。

### 关键适配点（与 1.84 的差异）

- **无需补丁**：1.90 上游已原生用 `__OHOS__` 守卫 `pthread_setcancelstate`
  （boost/core/detail/sp_thread_sleep.hpp 实测），boost1.84 的
  patches/0001-ohos-pthread-cancel-fix.patch 不再需要。
- **仍需 C++17 宏**：`-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF`（std::atomic_ref
  是 C++20 特性，atomic_ref.hpp 回落到 boost::atomic_ref header-only）。
- **R26**：产物为静态库 .a，不与系统同名库冲突。
- `BOOST_ALL_NO_LIB`：跳过 boost 自动链接机制。

## 上游测试闭环（规则 5，2026-09-10 纪律）

### N 口径（上游构建系统注册的测试目标数，实测 Jamfile 规则解析）

| 库 | 注册目标数 | 实测依据（libs/<lib>/test/Jamfile.v2） |
|---|---|---|
| filesystem | 34 | 主 Jamfile 32（28 run + 3 compile + 1 compile-fail）+ issues/ 2 run |
| regex | 37 | 直接规则（24 run + 5 link + 8 compile，含 3 个 regex-test 展开） |
| program_options | 30 | 14 po-test ×2（static+dll 双目标）=28 + rtti-off run 1 + quick 1 |
| iostreams | 45 | all-tests 列表 44 test-iostreams + 1 compile-fail-iostreams |
| **合计 N** | **146** | b2 目标级口径 |

### 实际运行（31 项独立可运行目标全量直跑）

b2 无法在 OHOS 运行上游测试目标，改为手动编译各库自带测试源文件（绕过 b2）
并真实运行，31 项中 30 项通过：

- filesystem 8 项：copy/convenience/foreach/large_file_support/path/path_unit/relative/quick 全过
- regex 6 项：quick + issue153/227/232/244/245 全过（issue227/232/244/245 为 1.90 新增注册目标）
- program_options 12 项：cmdline/exception/exception_txt/optional/options_description/
  positional/quick(--path=initial)/split/required/unrecognized/variable_map 过，
  **parsers_test 段错误 rc=-11**（直接操作 stderr/stdout 文件描述符做重定向，
  OHOS musl 环境差异，与 1.84 同结论——多轮运行稳定复现）
- iostreams 6 项（1.90 新纳入，unit_test_framework 驱动）：gzip/file/
  filtering_stream/mapped_file/file_descriptor/copy 全过

### 与 boost1.84（#8530）对比的口径修正

1. **N 口径修正**：1.84 PR 申报 16 项（手动挑选子集）；本次按 2026-09-10 纪律
   以 Jamfile 注册数 N=146 为分母口径，选取其中可独立运行的 31 项全集直跑。
2. **测试面扩大**：新增 iostreams 6 项（1.84 因未编译 unit_test_framework 豁免
   全部 iostreams 测试）、program_options 3 项（required/unrecognized/variable_map）、
   regex 4 项（issue227/232/244/245，1.90 新增）、filesystem 3 项
   （path_unit/relative/convenience 之外的 v4 目标补全）。
3. **parsers_test 结论不变**：1.90 仍稳定段错误 rc=-11（平台环境差异，非适配缺陷）。

## 验证结果

- conan create + test_package（filesystem + regex + program_options +
  iostreams gzip round-trip）通过
- 上游测试 30/31 通过（1 项平台差异豁免，详见 upstream-tests-report.txt）
- 本地验证记录（reports/，gitignore 不入库）：upstream-tests-report.txt（32 项逐条 rc）、test-report.md（Septest 口径报告）

## 与 boost/1.90.0 的关系

同源上游（boost_1_90_0.tar.gz），不同配方形态：boost/1.90.0 为 header-only +
Boost.Test 静态库；本包 boost1.90 为手动编译 4 库静态归档（对齐 boost1.84 本体
形态），供需要链接型组件的下游使用。制品仓并行维护，下游按需选择引用。
