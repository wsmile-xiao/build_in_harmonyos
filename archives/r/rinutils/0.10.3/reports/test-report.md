# rinutils 0.10.3 测试报告

> **项目**: rinutils 0.10.3（header-only C11 工具库）
> **测试日期**: 2026-09-21
> **测试环境**: HarmonyOS 6.1.0（HongMeng Kernel 1.12.0 aarch64，HAD-W32/W24）
> **测试类型**: 上游 cmocka 用例（conan create build() 内真实执行）+ 消费者测试
>   （`test_package/`，鸿蒙特有）+ 上游 Perl 用例不可运行性逐项说明
> **编译工具链**: OHOS SDK clang 15.0.4（aarch64-linux-ohos），Conan 2.29.1

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试文件总数 | 8 | 100% |
| 上游可运行用例（OHOS） | 1（C/cmocka） | 12.5% |
| 上游可运行用例通过 | 1 | 100% |
| 上游不可运行用例（Perl/CPAN） | 7 | —（逐项技术原因见 §3.3） |
| 消费者测试断言（鸿蒙特有） | 36 | 100% |
| 消费者测试断言通过 | 36 | 100% |

**可运行面通过率**: ✅ **100%**（上游 C 用例 1/1；消费者 36/36）

> 上游测试面为混合形态：1 个 C/cmocka 用例 + 7 个 Perl 用例（4 个用 Inline::C 现场
> 编译、1 个全流程构建、2 个代码风格）。OHOS 无 CPAN Inline::C 工具链（无 cpanm、
> 相关模块全部缺失，逐字探测见版本目录 `notes.md`），Perl 用例与 C 库交付物无关，
> 属上游 CI 的 cpantest 专属面；本适配以 36 项消费者断言补足鸿蒙侧验证（R51）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。rinutils 0.10.3 在 HarmonyOS PC（aarch64）上经 CMake 完整构建、
打包（14 头文件 + pc + CMake 配置）；上游 cmocka 用例在 `conan create` 的
`build()` 中真实编译执行并通过；消费者经 `find_package(Rinutils)` 消费全部
13 个可用头文件，36 项运行时断言（含负向用例）全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 Perl 用例依赖 CPAN Inline::C 体系 | 7/8 上游测试文件在 OHOS 不可运行 | 🟡（平台生态限制，与 C 交付物无关，如实记录） |
| 上游 configure 期 GitHub 下载 + perl 强制依赖 | 构建不可离线复现 | 🟢 已修复（补丁 0001/0002 内置模块 + 取消下载） |
| HMDFS 不允许 mkfifo（gmake jobserver 警告） | 无功能影响（gmake 自动降级） | 🟢（平台限制，构建/测试正常） |

### 2.3 可用功能清单

```
✅ CMake 构建 + 安装：14 个头文件、librinutils.pc、RinutilsConfig*.cmake
✅ 上游 cmocka 用例（bit 读写器写入/覆盖/读取）：1 test(s) PASSED（6 断言）
✅ 消费者测试（CMakeDeps: find_package(Rinutils) + Rinutils::Rinutils）：36/36 PASS
✅ COUNT/LAST、min/max、string_starts_with/try_str_prefix（含负向）
✅ SMALLOC/SREALLOC（内容保留）、bit_writer/reader 往返 + overwrite/skip
✅ RIN_LL_FMT/RIN_LL9_FMT、portable_time（秒/微秒）、likely/unlikely
✅ typeof_wrap（var_AUTO/const_AUTO）、GCC_UNUSED、DLLEXPORT、rinutils 聚合头
⚠️ rin_cmocka.h：需外部 cmocka 头，由上游 cmocka 用例覆盖（消费者不直接包含）
❌ 上游 Perl 用例（7 项）：OHOS 无 CPAN Inline::C 工具链，不可运行（非适配缺陷）
```

### 2.4 已知限制

1. **Perl 测试面不可运行**：4 个 `unit-*.t` 需要 `Inline::C` 在测试运行时现场编译
   C 片段；`build-process.t` 需要 Path::Tiny 并执行完整打包流程；`style-trailing-space.t`
   与 `tidyall.t` 需要代码风格 CPAN 模块。设备 perl 5.44.0 仅有核心模块
   （Test::More OK；Env::Path/Path::Tiny/Test::Differences/Inline/Inline::C/
   Test::TrailingSpace/Test::Code::TidyAll/Moo/Test::Trap 全部 MISS；无 cpanm）。
2. **上游 configure 期网络依赖**：上游会从 GitHub 下载 `Shlomif_Common.cmake`；
   本适配已内置模块并取消下载，构建完全离线（补丁 0001/0002）。
3. HMDFS 的 mkfifo 限制使 gmake jobserver 输出警告并降级为串行作业，无功能影响。

---

## 三、测试详情

### 3.1 上游 cmocka 用例（`t/bit-reader-and-writer-test.c`，1/1 PASS）

在 `conan create` 的 `build()` 中真实编译执行（证据：`reports/conan-create.log`）：

```text
[ 50%] Building C object CMakeFiles/bit-reader-and-writer-test.t.exe.dir/t/bit-reader-and-writer-test.c.o
[100%] Linking C executable bit-reader-and-writer-test.t.exe
rinutils/0.10.3@ohpcd/stable: running upstream cmocka test: .../bit-reader-and-writer-test.t.exe
[==========] tests: Running 1 test(s).
[ RUN      ] main_tests
[       OK ] main_tests
[==========] tests: 1 test(s) run.
[  PASSED  ] 1 test(s).
```

| # | 断言（上游源） | 结果 |
|---|----------------|------|
| 1 | `buffer[0] == (5 \| (1 << 4))` 写入 | ✅ |
| 2 | `buffer[0] == (5 \| (1 << 4) \| (2 << 6))` 追加写 | ✅ |
| 3 | `buffer[1] == 3` 跨字节写 | ✅ |
| 4 | reader 4bit == 5 | ✅ |
| 5 | reader 2bit == 1 | ✅ |
| 6 | reader 4bit == (2 \| (3 << 2)) | ✅ |

### 3.2 消费者测试（`test_package/test.c`，36/36 PASS）

经 `find_package(Rinutils)` + `Rinutils::Rinutils`（CMakeDeps）构建消费，
ctest 1/1 Passed + 直接运行（证据：`reports/conan-create.log`）：

```text
== rinutils consumer test (13 of 14 installed headers) ==
...（36 行 PASS，含负向用例）...
== TOTAL CHECKS: 36, FAILURES: 0 ==
ALL 36 CHECKS PASSED
```

| 分组 | 断言数 | 覆盖 |
|------|:------:|------|
| count.h | 2 | COUNT/LAST |
| min_and_max.h | 2 | min/max |
| str_utils.h | 6 | 前缀判断 3 正/负例、try_str_prefix 成功/失败 |
| alloc_wrap.h | 4 | SMALLOC/SREALLOC、realloc 内容保留 |
| bit_rw.h | 11 | 上游同款写入/读取 + overwrite/skip/roundtrip |
| longlong.h | 2 | RIN_LL_FMT、RIN_LL9_FMT |
| portable_time.h | 2 | 秒（>2001）、微秒范围 |
| likely/typeof/unused/dllexport | 7 | 宏语义与导出符号 |
| **合计** | **36** | 13 个头文件（rin_cmocka.h 由上游用例覆盖） |

### 3.3 不可运行的上游用例（7 项，逐项技术原因）

| 用例 | 依赖 | 技术原因 |
|------|------|----------|
| unit-count.t | Inline::C, Env::Path, Path::Tiny, Test::Differences | 设备无 Inline/Inline::C 及依赖链（Parse::RecDescent/Pegex 等），无 cpanm 与 CPAN 镜像；Inline::C 需为目标 perl 构建 XS 扩展 |
| unit-ll-formats.t | 同上 | 同上 |
| unit-min-and-max.t | 同上 | 同上 |
| unit-str-utils.t | 同上 | 同上 |
| build-process.t | Path::Tiny + cmake/make/tar + `RINUTILS_TEST_BUILD` | Path::Tiny 缺失；且该用例执行完整 dist/打包流程（上游发布验证面） |
| style-trailing-space.t | Test::TrailingSpace | 模块缺失 |
| tidyall.t | Code::TidyAll, Moo, Test::Code::TidyAll + `RINUTILS_TEST_TIDY` | 模块缺失 |

> 未对上述测试源做任何修改；未以任何方式伪造其运行结果。

---

## 四、关键问题分析

### 问题1: 上游 configure 期 GitHub 下载 + perl 强制依赖

**现象**：上游 `cmake/shlomif_common_bootstrap.cmake` 在找不到
`Shlomif_Common.cmake` 时 `FILE(DOWNLOAD)` GitHub raw；且该模块
`include(FindPerl)` 后 `FATAL_ERROR "perl must be installed"`。

**根因**：上游对非 CMake 生态工具的隐式依赖；构建不可离线复现。

**解决方案**：补丁 0001 内置模块裁剪副本（仅保留 4 个被用到的宏，保留 MIT 版权），
补丁 0002 将下载分支改为 `FATAL_ERROR`。conan-verify G2 与本地 CI 均通过，
configure 全程无网络访问。

### 问题2: `get()` 对 codeload URL 的文件名推断

**现象**：`BadZipFile: File is not a zip file`（source() 失败）。

**根因**：codeload URL 以裸 tag（`0.10.3`）结尾，Conan `get()` 用 URL basename
作为保存文件名，无扩展名导致按 zip 解码。

**解决方案**：`get(..., filename="rinutils-0.10.3.tar.gz")`（jattach 2.2 同款）。

### 问题3: R47 语言预检 `mixed` 误报

**现象**：`detected_language=mixed`（`source_stats: perl:5, python:1, c:1, 71%`）。

**根因**：检具将 Perl 测试/CI 脚手架计入主体、不映射 `.t`、`.h` 按设计不计数。

**解决方案**：反证复核（交付物 = 14 个 C 头文件，全部 perl/python 文件为测试/CI
脚手架）后按同型先例继续（libemf/libcaca/cronic）；未伪造字段；自动写入的
`env_unsupported` 终态已更正为进行中草稿。详见版本目录 `notes.md`。

---

## 五、测试环境

```text
OS:        HarmonyOS 6.1.0.117 / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
SDK:       OHOS SDK 26.0.0.18 native (clang 15.0.4, aarch64-unknown-linux-ohos)
Conan:     2.29.1 (OHOS-adapted), profile ohos-aarch64-device
构建:      conan create（CMake 4.4.3；WITH_TEST_SUITE=ON；cmocka 2.0.2 test_requires）
产物:      include/rinutils/*.h ×14 + librinutils.pc + RinutilsConfig*.cmake + LICENSE
           packaging/rinutils-0.10.3-ohos-aarch64.tar.gz (43548 B)
```

---

*报告生成时间: 2026-09-21*
