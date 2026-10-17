# itlib 1.11.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMakeLists.txt` 只有 INTERFACE 目标；跑 CMake 是为了执行测试树，交付物仍是 header-only）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，libc++ 15.0.4）
- 设备: HarmonyOS PC aarch64，conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 软件概览

itlib（github.com/iboB/itlib，作者 Borislav Stanimirov）是一组 **std-like 单头 C++ 库**：
交付物 `include/itlib/*.hpp` 共 32 个头（归档 87 KB / 解包 1.1 MB），
上游 `CMakeLists.txt` 只声明 `add_library(itlib INTERFACE)` + `add_library(itlib::itlib ALIAS itlib)`，
**0 外部依赖**（无任何 `find_package` / 外部 `target_link_libraries`）。
测试树 `test/` 用 doctest（经 CPM.cmake 拉取）按 C++11/14/17/20 分档跑。

## W0 立项预检（生死关三关全过）

| 关 | 判据 | 实测读数 |
|---|---|---|
| W0-1 版本可得性 | `git ls-remote --tags https://github.com/iboB/itlib` | 50 个 tag / 100 行（含 annotated 解引用）全量命中：`refs/tags/v1.11.4 = a061e1dccfa3d04ee3bc36388c94745ce813d0ea`、`refs/tags/v1.11.4^{} = d51231a7a7dbbd56ff6680ea509e84a41eddfa2c`；tag 归档 URL 可下载（86904 字节） |
| W0-1 源 sha256 同源 | 本地下载实测 vs CCI | `09b155afcb9766fe36d0156294f6656956189235612eb7711903ebc22079c37e` == CCI `recipes/itlib/all/conandata.yml` 的 `"1.11.4"` 条目（**三路一致**：任务卡 / CCI / 设备实测） |
| W0-2 硬依赖 | `bash ci/scripts/preflight_check.sh itlib/1.11.4` → `✅ 预检通过（无依赖需要检查）`；`conan list itlib/* -r=ohpcd` = 0（新包无既有副本）；配方 `requirements()`/`build_requirements()` 双空 | 0 依赖，无缺失硬依赖 |
| W0-3 平台不可移植 | `grep -rInE 'altivec\.h\|3dnow\|__mmx__\|mmxintrin\|x86intrin\|immintrin\|emmintrin\|nmmintrin\|arm_neon\|_mm_\|_mm256_\|__AVX\|__SSE\|__NEON'` （整棵源码树） | **rc=1 零命中** |
| W0-3 glibc printf 钩子 | `grep -rInE 'printf\.h\|register_printf_\|__printf_function\|__printf_arginfo'` | **rc=1 零命中** |

**全新包**：`archives/i/itlib` 在 upstream/main 不存在（`git ls-tree -r --name-only upstream/main \| grep -ci itlib` = 0，
`archives/i/` 下 1661 条目无同名），`task_init.sh` 加 `--allow-unpublished` 放行；
分支 `feat/itlib-1.11.4` 去前缀 == `itlib-1.11.4` == 包目录名-版本，过 CI 分支名门禁。

## 环境事实（本轮实测，供 CI 判读）

| 事实 | 读数 |
|---|---|
| 工具链 | cmake 4.1.2 / ctest 4.1.2 / ninja 1.13.1 / clang 15.0.4 (`aarch64-unknown-linux-ohos`) |
| libc++ 版本 | `_LIBCPP_VERSION = 15004`（**< 16000** ⇒ 上游三处 `_LIBCPP_VERSION >= 16000` 守卫关闭） |
| libc++ 头探测 | `span`/`format`/`ranges`/`charconv` ✅；**`memory_resource` ❌（头文件不存在）**、`source_location` ❌ |
| `newlocale(LC_ALL_MASK, ...)` | `en_US.UTF8` / `en_US.utf8` / `C.utf8` / `en_US.ISO8859-1` → **FAIL**；`en_US.UTF-8` / `C.UTF-8` / `en_US` / `C` → OK |
| 线程 | `find_package(Threads)` → `Found Threads: TRUE`（pthread） |
| 并发 | `os.cpu_count()=20`、`sched_getaffinity()=8`、`nproc=8` ⇒ 构建传 `-c tools.build:jobs=4` |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `include/itlib/generator.hpp:223` 编译硬错误 `missing 'typename' prior to dependent type name 'pseudo_iterator::end_t'` | 从属类型名缺 `typename`。C++20 的 P0634R3「Down with typename!」在 **clang 16** 才完整落地，OHOS 工具链是 **clang 15.0.4**；上游 CI 矩阵只有 ubuntu(gcc)/windows(msvc)/macos(AppleClang≥16)，因此从未见过 | **补丁 0002**：加 `typename`（严格更符合标准的等价写法，所有编译器行为一致）。全树扫描确认仅此 1 处 |
| 2 | `include/itlib/transparent_umap.hpp:81,82` 同型硬错误（`super::iterator` / `super::const_iterator`），**11/14/17/20 四档全中** | 同 #1；`super` 是类模板内的 typedef，其嵌套名仍从属 | **补丁 0003**：两行补 `typename` |
| 3 | `test/t-time_t-11.cpp` 的 `[time_t] tm` 用例必败：`test case THREW exception: collate_byname<char>::collate_byname failed to construct for en_US.UTF8` | 上游硬编码 `std::locale("en_US.UTF8")`；bionic + ICU74 的 `newlocale(LC_ALL_MASK, "en_US.UTF8")` 返回 NULL（只认 `.UTF-8` 连字符形态，实测探针见上表） | **补丁 0001**：locale 名改 `en_US.UTF-8`。`CHECK(fmt.length()==24)`、`CHECK(fmt=="Monday 09/10/01 05:33:20")`、用例数**一字未动** |
| 4 | `test/CMakeLists.txt` 在 configure 期经 CPM.cmake 直连 GitHub 拉 3 个包（icm@1.5.1、doctest-util@0.1.2→doctest-lib@2.4.11），`test/get_cpm.cmake` 还要 `file(DOWNLOAD)` CPM.cmake 本体 | CI worker 无法直连 github.com（crow 1.3.3 / glob 0.0.1 同族先例） | **零补丁**，走 conan：① 4 个 URL 全进 `conandata.yml`（CI 的 mirror fallback + pre-download 逐条生效）；② `source()` 预下载并解包到 `<source>/_deps/`；③ `generate()` 传 `-DCPM_SOURCE_CACHE=<source>/_deps`（消掉两处 `get_cpm.cmake` 的 `file(DOWNLOAD)`）+ `-DCPM_icm_SOURCE` / `-DCPM_doctest-util_SOURCE` / `-DCPM_doctest-lib_SOURCE` 三个手工 override（CPM 的 override 分支优先级最高，走 `SOURCE_DIR` ⇒ 不进 FetchContent 下载）⇒ **configure 阶段零网络** |
| 5 | 首版 conan create 报 `'settings.compiler' value not defined`、`'settings.os.version' value not defined` | 用了 conan **default profile**（无 `compiler`、无 `os.version`） | 全链一律 `-pr:h/-pr:b = <worktree 绝对路径>/ci/conan/profiles/ohos-aarch64`（device-facts §一.17：必须绝对路径，相对名会命中 `$CONAN_HOME/profiles/` 陈旧副本）；`validate()` 改用 `settings.get_safe("compiler.cppstd")` |
| 6 | 自写反假绿断言报 `ctest 注册项 = 0` | CMake 生成的 `CTestTestfile.cmake` 用**位置参数**形态 `add_test(<name> <cmd>)`，不是 `add_test(NAME <name> ...)` | 正则改按位置参数取首参；修后读数 **47** |
| 7 | `make: jobserver mkfifo: ... Operation not permitted` | 设备 SELinux/HMMAC 拒绝 FIFO，make 4.4.1 自动退化 pipe jobserver，**并发未退化**（device-facts §一.13） | 噪声，不处理 |
| 8 | finish 内嵌 **G0 clean-verify 报「安装产物为空」** | 上游无 `install()` 规则（header-only INTERFACE 库），`cmake --install` 后 staging 无 `bin/*`/`lib/*` | **预期行为、不阻塞**：`finish.py` 对 G0 非零只 `log_warn`（`step25_g0_clean_verify` 不 `SystemExit`）。ctml 2.0.0 同型先例已记。G0 仍跑完整 configure+build（`manifest.build.build_options = -DITLIB_BUILD_TESTS=ON`，不在任何闸上关测试） |
| 9 | **W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）失败：`conan create` 报 `NotADirectoryError: …/predl_cache/bd8dbd96_itlib/archive/v1.11.4.tar.gz`，并出现 `https://gh-proxy.com/file://…` 这种畸形 URL** | CI 的 pre-download 用 `content.replace(url, 'file://…')` 对**整份 conandata.yml**（**含注释**）做字面替换。我最初在头注释里写了两行取证说明：`# 1. git ls-remote --tags https://github.com/iboB/itlib` —— 这个**短 URL 是真正源 URL 的前缀**，于是它被最先下载成一个 56660 B 的 HTML 页（文件名 `bd8dbd96_itlib`），随后把 `https://github.com/iboB/itlib/archive/v1.11.4.tar.gz` 改写成 `…/bd8dbd96_itlib/archive/v1.11.4.tar.gz`（父路径是个**文件**不是目录 ⇒ ENOTDIR），gh-proxy 那一路则变成 `https://gh-proxy.com/file://…` | **改注释不改数据**：头注释一律不写任何 `https://` 裸 URL（tag/sha 改为引用 `sources["1.11.4"].url` 与文字描述）。改后按 CI 同款「镜像改写 → URL 提取 → 逐 URL 字面替换」三步离线复算，10 个替换目标全部落到 `predl_cache` 里已存在的真实文件，零前缀碰撞 |

## 源码修改（3 个 platform 补丁，全部 `patch_type: platform`）

| 补丁 | 文件 | 性质 |
|---|---|---|
| `0001-test-t-time_t-11.cpp.patch` | `test/t-time_t-11.cpp` | locale 名 `en_US.UTF8` → `en_US.UTF-8`（bionic/ICU 规范形态）。**断言与用例数不变** |
| `0002-include-itlib-generator.hpp.patch` | `include/itlib/generator.hpp` | 补 `typename`（1 行） |
| `0003-include-itlib-transparent_umap.hpp.patch` | `include/itlib/transparent_umap.hpp` | 补 `typename`（2 行） |

- 生成方式：`refresh-patch --auto`（per-file-difflib，orig=`$HOME/ws/tmp/builds/itlib-1.11.4.orig`、
  work=`…/itlib-1.11.4.work`，orig hash `96f7931680334ed8` / work hash `3277e063ebb2fb66`），
  补丁名与 `conandata.yml` 的 `patches:` 由工具同步，manifest 记 `patch_generation`。
- **没有任何测试被删除、注释、跳过或改期望值**：CTest 程序口径 47 条、源码宏口径 130 个都一个没少（见下表）。
- **未打补丁的已知缺陷**：`include/itlib/tep_vector.hpp` 单独 `#include` 不自洽——只 `#include <cstdint>`
  却使用裸 `size_t`，在本工具链报 `unknown type name 'size_t'`（补 `#include <cstddef>` 即可）。
  该头**上游无任何测试文件**（`test/` 下无 `t-tep_vector-*`），不属于本任务的验证面 ⇒
  按 §3.3 杠杆①「文档级发现登记不修」，登记在 PR 正文「已知限制」，不改已提交文件。

## 依赖版本

0 运行依赖、0 `tool_requires`（上游带 CMakeLists.txt，设备/CI 均有 cmake；不需要 automake/autoreconf）。
`conandata.yml` 里的 `icm_sources` / `doctest_util_sources` / `doctest_lib_sources` / `cpm_source`
**不是 conan 依赖**，只是上游测试树的 CPM 依赖，在 `source()` 阶段下载，不进 conan 依赖图、不打包。

## 上游测试清点（R51 三步法·申报表；2026-09-27 返修按 §7.3「候选数法最大值」重算）

上游测试树：`test/t-*.cpp` **44** 个 doctest 用例源文件（按 C++11/14/17/20 分档）+
`test/bft-*.cpp` **3** 个 icm build-failure 用例；入口 `test/CMakeLists.txt` 的
`add_itlib_test()` / `icm_add_multiple_build_failure_tests()` → `add_test()`。
另有一个共享用例文件 `test/t-atomic_shared_ptr_storage.inl`（含 3 个 `TEST_CASE`，
被 `-11` 与 `-20` 两个 TU `#include`）——**按 `.cpp` 文件数清点时会整份漏掉它**。

### 四口径清点（单位不混用；N 取「测试用例数」同单位候选的最大值）

| 口径（单位） | 取数命令 | 清点值 |
|---|---|---|
| ① 源码宏数（doctest `TEST_CASE` 宏，**N 口径**） | `grep -rn "TEST_CASE(" <source>/test/ \| wc -l` → **130**（其中 `test/*.cpp` 127 + `t-atomic_shared_ptr_storage.inl` 3） | **130** |
| ② 框架注册数（doctest test case 注册事件） | 44 个 `itlib-test-*` 逐可执行 `--list-test-cases` 求和（与逐可执行运行期 `test cases:` 求和**同值互证**） | **128** |
| ③ CTest 注册数（程序口径） | `ctest --test-dir <build> -N` → `Total Tests: 47`（44 个 doctest 可执行 + 3 个 build-failure） | 47 |
| ④ doctest 断言数（assertion 单位，单列） | 逐可执行运行期 `assertions:` 求和 | 4487 |
| ⑤ 消费者断言数（鸿蒙特有，分栏不进上游分母） | `./test_itlib` → `ITLIB-CONSUMER checks=91` | 91 |

**N = max(①,②,③) = 130**：①②③ 里①② 同为「测试用例数」单位、③ 是「测试程序数」单位
（§7.3 明确：把「测试程序数」当 N 是最常见的致命错，zfp 2 → 712 同型）。原声明 47 即取了
③/文件口径，构成真少报，已更正。④⑤ 属别的单位，按「四口径不得混用」单列，不并入 N。

### 差额逐项归因（严格合计）

| 差 | 归因 | 数 |
|---|---|---|
| ① 130 → N′ 125（实跑） | 上游自带预处理守卫在本平台不成立，用例体被编译掉（NOT_RUN 5 项，逐项见下） | −5 |
| N′ 125 → ② 128 | `t-atomic_shared_ptr_storage.inl` 的 3 个宏被 `-11`、`-20` 两个 TU 各注册一次 | +3 |
| ① 130 → ② 128 | −5 + 3 | −2 |
| **审方实测 127 → 本设备实测 128** | 审方口径 = `grep "TEST_CASE(" test/*.cpp` = **127**（与我方逐字同值）：未含 `.inl` 的 3 个宏、未扣 5 个守卫项、也未反映 `.inl` 3 宏在 2 个 TU 的 6 次注册 ⇒ 127 − 5 + 6 = **128**（差 1 的净来源） | **+1** |
| ② 128 → ③ 47 | 44 个 doctest 可执行的 test case 合计 128 + 3 个 build-failure 用例（源码无 `TEST_CASE` 宏、单位不同，不占① 的格）= 47；一个 CTest 条目 = 一个可执行/脚本 | — |

**N′（本次实跑·源码宏口径）= 125，PASS=125 / FAIL=0 / SKIP=0 / NOT_RUN=5，
TOTAL = PASS+FAIL+SKIP+NOT_RUN = 125+0+0+5 = 130 = N；通过率 = 125/130（96%）。
同轮互证读数：框架注册口径 128/128 test case 全过、4487/4487 断言全过；
CTest 程序口径 47/47 条目全部返回 0（含 3 个 build-failure）。**

### NOT_RUN 5 项逐项（全部是上游自带守卫 → 环境限制，非跳过、非失败、不写 PASS）

| # | 文件 | 用例名 | 守卫 | 证据 |
|---|---|---|---|---|
| 1 | `test/t-any-17.cpp` | `any pmr_allocator` | `#if !defined(_LIBCPP_VERSION) \|\| _LIBCPP_VERSION >= 16000` | 本机 `_LIBCPP_VERSION = 15004` |
| 2 | `test/t-any-17.cpp` | `allocator aware`（pmr 分支体） | 同上 | 同名非 pmr 版本在 `t-any-11.cpp` 已 PASS |
| 3 | `test/t-pmr_allocator-17.cpp` | `pmr_allocator` | 同上 | `t-pmr_allocator-20.cpp` 直接 `#include` 本文件，两个 TU 都被剔除（源码宏只计 1 次） |
| 4 | `test/t-pmr_allocator-17.cpp` | `pmr_allocator ctors` | 同上 | 同上 |
| 5 | `test/t-atomic_shared_ptr_storage-20.cpp` | `std::atomic<std::shared_ptr> is not lockfree` | `#if defined(__cpp_lib_atomic_shared_ptr)` | 设备探针：`use of undeclared identifier '__cpp_lib_atomic_shared_ptr'`（clang15/libc++15 未定义） |

共同根因：OHOS libc++ **没有 `<memory_resource>` 头**（`pmr_allocator.hpp:49`
`#include <memory_resource>` → `fatal error: 'memory_resource' file not found`，
设备探针复现），上游据此在文件顶自带 libc++ 版本守卫。影响面 = `itlib::pmr_allocator` 与
依赖它的 `itlib::any` pmr 分支；替代验证 = `itlib-any-11`（非 pmr 分支）全过 +
消费者面刻意不覆盖它们（不冒充可消费）。

**原 NOT_RUN 3 项 → 新 N（130）的映射**：
- 原按 CTest 条目粒度记的 NOT_RUN 3（`itlib-any-17`、`itlib-pmr_allocator-17`、
  `itlib-pmr_allocator-20`）→ 上表第 1–4 个宏（-20 与 -17 同源文件，源码宏只计 1 次）；
- 上表第 5 个宏是**新增**的 NOT_RUN：该 CTest 条目 `itlib-atomic_shared_ptr_storage-20`
  在旧粒度下因 `.inl` 的 3 个用例通过而被计 PASS，但其自带的这 1 个宏确实没运行；
- 原 PASS 44 = 41 个 doctest 条目 + 3 个 build-failure：其中 40 个有用例条目展开为
  **PASS 125** 个源码用例（`.inl` 3 宏在两个 TU 各注册一次，源码宏只计一次），
  `itlib-transparent_umap-20` 源码 **0 个 `TEST_CASE`**、不占① 的格；
- 3 个 build-failure 用例源码无 `TEST_CASE` 宏、不占① 的格，在 ③ 口径单列且本次 3/3 实跑通过。

必须如实单列（不写假 PASS）：
1. **5 个源码用例本平台未注册未运行**（上表）——环境限制（上游自带守卫 + OHOS libc++ 缺特性），
   按 §3.5 记 NOT_RUN，**不计 PASS**，逐项给出守卫条件与设备探针证据。
2. **两个纯编译期条目**——`itlib-transparent_umap-20`（只 `#include` 两个头、无 `TEST_CASE`，
   ctest PASS 语义 = 头文件在 C++20 下可编译）与 `itlib-type_traits-11/17`
   （断言全是 `CCHECK` = `static_assert`，运行期 0 assertion 属预期），
   均**不占源码宏格**、在 ③ 口径单列，不是空跑。

**鸿蒙特有测试（不进上游分母）**：`test_package/test.cpp` 消费者断言 **91** 条
（运行期 `ITLIB-CONSUMER checks=91 failures=0`），覆盖 12 个交付头的真实 API 调用。

## 验证结果

```bash
# ① 本地 conan create（采信轮前的试跑，日志 $TASK_DIR/try-create.log）
P=$TARGET_REPO/ci/conan/profiles/ohos-aarch64
conan create "$PACKAGE_DIR" -pr:h="$P" -pr:b="$P" -c tools.build:jobs=4     # rc=0
#   source()  : 4 个 URL 全部下载 + sha256 自校验 OK + 3 个补丁逐条 apply
#   configure: -DITLIB_BUILD_TESTS=ON + CPM 三件套全部命中本地 _deps（无 file(DOWNLOAD)）
#   build()  : [upstream-tests] ctest 注册项 = 47（== CTest 程序口径清点 44+3；N 口径=源码宏 130 见上表）
#   ctest    : 100% tests passed, 0 tests failed out of 47
#   test_package: ITLIB-CONSUMER checks=91 failures=0
#
# ② 采信轮（沙箱 HOME 手工复跑证据见 reports/test-report.md）
#    HOME="$TASK_DIR/test-home" ctest --test-dir <build> -N                 → Total Tests: 47
#    HOME="$TASK_DIR/test-home" ctest --test-dir <build> --output-on-failure → 47/47
#    HOME="$TASK_DIR/test-home" ./test_itlib                                → ITLIB-CONSUMER checks=91 failures=0
```

## 知识沉淀（官方机制，§3.8）

适配全程 2 处硬错误，**逐条跑 `ohc-run.py engine` 匹配既有 E 条目，两条均命中 ⇒ 按 §3.8
「命中 ⇒ 用既有条目、不写新草稿」，本任务零草稿（零草稿是正常终态，不硬凑）**：

| 错误签名 | engine 命中 | 处置 |
|---|---|---|
| `error: missing 'typename' prior to dependent type name ...`（generator.hpp / transparent_umap.hpp） | **E397**（cxx-compiler-compat，Phase B=6；根因正是「P0634R3 typename elision，OHOS SDK clang 15.0.4 支持不完整」，推荐方案=在从属类型名前补 `typename`） | 按 E397 方案落地为补丁 0002/0003 |
| `test case THREW exception: collate_byname<char>::collate_byname failed to construct for en_US.UTF8` | **E023**（compat/posix，Phase B=2；根因「鸿蒙 locale 数据不完整，缺少 en_US.UTF-8 等常用 locale 定义」） | 按 E023 的 locale 方向处置，但**未采用其「skip-test / LC_ALL=C」回退**——上游该用例有硬期望字符串，正解是把 locale 名改成 bionic/ICU 认的 `en_US.UTF-8`（补丁 0001），用例与断言全保留 |

另：`fatal error: 'memory_resource' file not found` 被 engine **误命中 E169**（根因是 GNU `argp.h` 缺失，
与本包无关，Phase B 仅 2 分的泛化签名 `fatal error: '<头>' file not found`）——该签名属
「上游自带 `_LIBCPP_VERSION >= 16000` 守卫 + 环境限制」，未造成本任务任何构建失败，
按「宁缺勿滥」不建草稿，误命中现象记入 `feedback/pending/`（建议给 E169 收窄签名）。

## 注意事项

- 本包是**全新包**（`archives/i/itlib` 在 upstream/main 不存在），PR 标题前缀按 O16 取
  **【依赖项】**（任务来源 = 依赖项；无知识草稿时不取【知识库扩展】）。
- header-only ⇒ `package_type=header-library` + `implements=["auto_header_only_mode"]`，
  `package()` 只拷 `include/itlib/*.hpp`（32 个）+ `LICENSE.txt` → `licenses/`。
- `manifest.status = "built"`（O5：合并并确认 release upload 之前不得写 `published`）。
- 上游 `README.md` 未列出 `tep_vector` 的测试，`test/` 下也确无该文件——本任务不为它造用例。
