# boost1.84-nowide 1.84.0 适配笔记

## 编译开始时间
2026-09-05 16:20

## 组件包形态选型结论

选型：方案 A —— 独立裁剪编译（同 boost1.84-atomic，选型论证见其
notes.md「组件包形态选型结论」章节，适用于本包：元包无 nowide 组件
声明、无 libboost_nowide.a 产物、Nowide 非 header-only）。

## 编译系统
手动编译（b2 在 OHOS 不兼容，E068；与底稿 boost/1.84.0 元包配方同构）

## 源码下载
- 来源：Boost 官方（archives.boost.io + SourceForge 双镜像，与底稿 conandata.yml 一致）
- SHA256：a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724

## 环境信息
- 平台：OpenHarmony (aarch64)
- 编译器：clang 15.0.4
- 构建系统：手动 clang++/llvm-ar（绕过 b2）

## 源码清单（权威依据：libs/nowide/build/Jamfile.v2）
```
local SOURCES = console_buffer cstdio cstdlib filebuf iostream stat ;
lib boost_nowide : $(SOURCES).cpp : <include>../src ;
```
aarch64 Linux/OHOS 全部 6 个 TU 编译（console_buffer 在 POSIX 分支为空实现，
上游同款构建，无需平台条件排除）。

## 编译命令（R33 合规——编译器从 conf 取）
```bash
clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC \
  -DBOOST_ALL_NO_LIB -DBOOST_NOWIDE_NO_LIB \
  -I<boost_root> -I<boost_root>/libs/nowide/src \
  -c libs/nowide/src/<each>.cpp -o <each>.o
llvm-ar rcs libboost_nowide.a <6 个 .o>
```

## 上游测试（绕过 b2 手动编译运行，26 目标全注册口径）

目标清单对齐 libs/nowide/test/Jamfile.v2（boost-1.84.0，与官方 release
tarball 比对一致，2026-09-06 实测）：**26 个注册测试目标（25 run + 1
compile）**。变体是独立注册的测试目标，不折叠计数——同一 .cpp 以不同
requirement（宏/构建库/launcher）多次注册即多次编译运行。

### 目标分类与执行结果（TOTAL 26: 22 passed / 0 failed / 1 known-platform-diff / 3 platform-na）

**实执行 23 项**（22 run PASS + benchmark compile PASS）：

| 目标 | requirement 要点 | 结果 |
|------|------------------|------|
| test_codecvt / test_convert / test_env / test_stackstring / test_stat | 单文件 + boost_nowide | PASS |
| test_env_win | test_env.cpp + `BOOST_NOWIDE_TEST_INCLUDE_WINDOWS=1`；源码守卫 `#if defined(...) && defined(BOOST_WINDOWS)` 在 POSIX 为空分支，退化为与 test_env 相同断言集 | PASS |
| test_fs | `<library>/boost/filesystem//boost_filesystem`；本配方测试期即时编译 9 个 POSIX TU | PASS |
| test_filebuf / test_ifstream / test_ofstream / test_fstream / test_fstream_special / test_iostream | +file_test_helpers.cpp | PASS |
| test_filebuf_internal / test_ifstream_internal / test_ofstream_internal / test_fstream_internal / test_fstream_special_internal | +`BOOST_NOWIDE_USE_FILEBUF_REPLACEMENT=1`；Jamfile requirement `<target-os>windows:<build>no` = **非 Windows 才构建**，POSIX 上游真实构建（宏强制启用 nowide 自带 filebuf 替换实现而非 std::filebuf 别名） | PASS |
| test_iostream_passthrough | `BOOST_NOWIDE_TEST_INTERACTIVE=1` + cmake launcher；等效复现：stdin 管道喂 "Hello Boost Nowide" → passthrough 子命令 → stdout 校验回显 + 断言重定向流未用 nowide filebuf | PASS |
| test_system_n | `BOOST_NOWIDE_TEST_USE_NARROW=1`（POSIX 侧 system 变体） | PASS |
| test_stdio | 单文件 | FAIL→known-diff（见下） |
| test_traits | `BOOST_NOWIDE_TEST_BFS_PATH` + boost_filesystem（Jamfile 仅此一次注册，BFS_PATH 即默认 requirement） | PASS |
| benchmark_fstream | `BOOST_NOWIDE_USE_WIN_FSTREAM=1` + `cxx11_hdr_chrono`；compile 型目标（性能跑批非断言型，编译通过即达成上游目标语义） | PASS (compile-only) |

**平台不适用 3 项**（Windows-only，计入 N、标注原因、不编译）：
test_system_w / test_system_use_windows_h / test_system_use_windows_h_lean ——
Jamfile 条件 `<conditional>@require-windows`：非 Windows 目标平台 b2 直接
`<build>no`（上游 Linux 构建同样只实际构建 23 个）。requirement 依赖
`_wputenv`/`_wsystem`（MSVC CRT 宽字符 API）与 shell32 库，POSIX/musl
无此 API，无法在本平台编译执行。

### libboost_filesystem 测试依赖的处理

test_fs 与 test_traits 的 requirement 是
`<library>/boost/filesystem//boost_filesystem`。本独立组件包产物不含该
库，但目标已注册且 Linux 可构建 → build() 测试阶段即时编译
libs/filesystem/src 的 9 个 POSIX TU（跳过 windows_file_codecvt.cpp），
宏与 boost/1.84.0 元包配方一致（`BOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF` /
`NO_CXX20_CHAR8_T`：C++17 无 std::atomic_ref 时的上游官方回退，
boost::atomic_ref 的指针/整型特化为 lock-free 头文件内联实现，无需额外
链接 libboost_atomic）。该库仅用于测试链接，不进入 package() 产物。

### test_stdio 平台差异（唯一未通过项，非适配缺陷）

- 失败断言：`TEST(std::fputs("not-written\n", f) < 0)`（对"r"模式流写）
- 根因：POSIX 标准未定义 fputs 对只读流的行为；glibc/MSVC 返回负值，
  musl libc 返回 0。OHOS 用 musl → 断言不成立。
- 验证 nowide 功能本身无缺陷：同一测试中 freopen 切换模式、fgets 读回
  两条内容（"test\n"/"foobar\n"）的断言全部通过（输出顺序在失败断言前）。
- 处理：未修改上游测试；配方以 diff_tag="musl-stdio-semantics" 豁免该
  已知差异——如实计入报告（known-platform-diff 类别，TOTAL 行单独计数），
  不计入 hard-fail（其余 22 项全 PASS 才放行；任何非豁免测试失败即
  conan create 失败）。

最终：**26 项注册目标：22 PASS / 0 FAIL / 1 known-platform-diff /
3 platform-na（Windows-only）**。

## 遇到的问题

### 问题 1: BOOST_NOWIDE_SOURCE 宏重定义 warning
- 症状：`warning: 'BOOST_NOWIDE_SOURCE' macro redefined`
- 根因：每个 src/*.cpp 第一行已 `#define BOOST_NOWIDE_SOURCE`，命令行
  再传会触发 -Wmacro-redefined
- 解决：配方 cxxflags 不传该宏（与 atomic 的 BOOST_ATOMIC_SOURCE 不同，
  atomic 的 lock_pool.cpp 不自带 define）

### 问题 2: 测试运行时 libc++_shared.so 缺失
- 同 atomic 问题 3，用编译器自省 + LD_LIBRARY_PATH 注入（配方内置）

## 知识提取记录
- nowide 拆分包模式：6 TU 全编（无平台条件源文件），无 patch 需求
- musl fputs 只读流语义差异是 OHOS 适配常见 libc 差异模式（可复用于
  其他 stdio 语义断言类测试）

## 编译结束
**编译结束**: 2026-09-05 16:30
**最终状态**: built
---

**编译结束**: 2026-09-05 17:12
**最终状态**: built

---

**2026-09-06 rule4 修订**（N=14→26）：
- 人工审核发现 PR 初版按"POSIX 侧 run 目标"口径报 14，遗漏变体目标
  （同源多次注册不折叠）与 benchmark compile 目标。重列
  libs/nowide/test/Jamfile.v2 全量 26 注册目标逐一处置。
- 新增实执行：test_env_win、test_fs（含即时编译 libboost_filesystem
  9 TU）、5 个 *_internal 变体（FILEBUF_REPLACEMENT=1）、
  test_iostream_passthrough（等效复现 cmake launcher）、
  benchmark_fstream（compile-only）、test_traits 改为 BFS_PATH 变体
  （Jamfile 唯一注册形态）。
- 3 个 Windows-only system 变体（@require-windows）如实计入 N、
  标注原因不执行。
- conan create 重跑 EXIT=0：TOTAL 26: 22 passed / 0 failed /
  1 known-platform-diff / 3 platform-na。
