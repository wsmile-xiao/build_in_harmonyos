# rinutils 0.10.3 适配笔记

## 编译环境

- 构建系统: cmake（header-only，无编译产物；`package_type = "header-library"`）
- 编译日期: 2026-09-21
- 编译器: OHOS SDK clang 15.0.4（`$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`）
- 目标: HarmonyOS PC / aarch64（设备本机编译），Conan profile `ohos-aarch64-device`
  （os=OHOS 6.0, arch=armv8, clang 15, libc++，build_type=Release）
- 依赖: 无运行时依赖（W0 通过）；`cmocka/2.0.2` 仅 `test_requires`（上游 C 用例），
  cmocka 制品仓二进制（OHOS armv8/clang15）W0 实测存在

## 语言预检（R47）复核与反证

默认口径实测（逐字）：

```json
{"expected":"cpp","detected_language":"mixed",
 "language_evidence":{"build_system":"cmake",
   "manifest":"CMakeLists.txt PROJECT(rinutils)",
   "source_stats":"源文件 7 个（perl:5, python:1, c:1），主体占比 71%"},
 "notes":["冲突: manifest=c 但统计 perl 占 71% → mixed"]}
```

该判定不成立（同型先例：libemf 1.0.14、libcaca 0.99.beta20、cronic 3，均以反证复核后继续；
知识草稿 DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive 等为同族模式）：

- **交付物 = CMake `install(FILES ...)` 的 14 个 C 头文件**（`rinutils/include/rinutils/*.h`）
  + `librinutils.pc` + `RinutilsConfig*.cmake`；构建树中没有任何 Perl/Python 交付物。
- 被计入主体的 5 个 perl 文件全部是**测试/CI 脚手架**（协议 D.4「辅助脚本不算主体」）：
  `run-tests.pl`（测试运行器）、`t/lib/Rinutils/{InlineWrap,Paths,Paths/Base}.pm`（Inline::C
  测试辅助库）、`CI-testing/continuous-integration-testing.pl`（上游 CI 脚本）；
  `python:1` = `CI-testing/translate-travis.yml-to-github-actions.py`（CI 辅助）；
  `c:1` = `t/bit-reader-and-writer-test.c`（上游 C 测试）。
- 检测器不映射 `.t` 扩展名、未将 `.pl/.pm` 辅助脚本排除，且 `.h` 头文件按设计不计数
  （E13 中立头文件）——纯头文件库天然被测试脚手架"淹没"，属检具误报。
- **未伪造 `detected_language`**；本次运行自动写入的 `env_unsupported` 终态已用
  `result rinutils 0.10.3 --status partial --draft-milestone task_started --force`
  更正为进行中草稿（cronic 3 同型处置先例），未污染任务真实终态。

## 上游测试清点（R51 第一步，证据）

`t/` 目录（tag tarball）共 8 个测试文件 + 1 个运行器 `run-tests.pl`（用 `prove` 驱动
`t/*.{t.exe,py,t}`）：

| 文件 | 类型/断言 | OHOS 可运行性 | 本次结果 |
|------|-----------|---------------|----------|
| `t/bit-reader-and-writer-test.c` | C + cmocka，6 个 `assert_int_equal` | ✅（cmocka/2.0.2 OHOS 二进制） | ✅ 在 `conan create` build() 中真实执行，`[ PASSED ] 1 test(s)` |
| `t/unit-count.t` | Perl + Inline::C，2 断言 | ❌ 缺 Env::Path/Path::Tiny/Inline/Inline::C | 不可运行（见下） |
| `t/unit-ll-formats.t` | Perl + Inline::C，1 断言 | ❌ 同上 | 不可运行 |
| `t/unit-min-and-max.t` | Perl + Inline::C，2 断言 | ❌ 同上 | 不可运行 |
| `t/unit-str-utils.t` | Perl + Inline::C，5 断言 | ❌ 同上 | 不可运行 |
| `t/build-process.t` | Perl（cmake/make/tar 全流程），7 断言 | ❌ 缺 Path::Tiny；且需 `RINUTILS_TEST_BUILD` | 不可运行 |
| `t/style-trailing-space.t` | Perl，2 断言 | ❌ 缺 Test::TrailingSpace | 不可运行 |
| `t/tidyall.t` | Perl，需 `RINUTILS_TEST_TIDY` | ❌ 缺 Code::TidyAll/Moo 等 | 不可运行 |

设备 Perl 模块探测（逐字，perl 5.44.0 @ harmonybrew）：

```
MISS Env::Path   MISS Path::Tiny   MISS Test::Differences   MISS Inline
MISS Inline::C   MISS Test::TrailingSpace   MISS Test::Code::TidyAll
MISS Moo         OK Test::More     MISS Test::Trap          no cpanm
```

技术原因（逐项）：4 个 `unit-*.t` 依赖 `Inline::C` 在测试运行时现场编译 C 片段
（需要完整 CPAN XS 工具链：Inline + Inline::C + Parse::RecDescent + Pegex 等，
设备无 cpanm、无 CPAN 镜像配置）；`build-process.t` 依赖 Path::Tiny 并执行完整
cmake/打包流程；`style-trailing-space.t`/`tidyall.t` 依赖代码风格 CPAN 模块。
这些模块均不在 OHOS 上提供，且**与 C 库交付物无关**（上游 CI 的 cpantest 专属面）。
因此上游可运行面 = 1 个 C 用例，实测 1/1 通过（100%）；不可运行面逐项列明原因，
未做任何上游测试源修改。

## 编译步骤

```sh
# 1) 配方验证（含干净 conan create：source→patch→cmake configure/build→
#    运行上游 cmocka 用例→package→test_package 消费验证）
cd $HOME/work/kasumizawa-miyuu/rinutils-wt
python3 scripts/ohc-run.py conan-verify rinutils 0.10.3 --profile ohos-aarch64-device

# 2) 本地 CI 门禁（与平台 CI 同源脚本）
CONAN_PROFILE=ohos-aarch64-device CI_PACKAGES="archives/r/rinutils/0.10.3" \
  CI_REPO_ROOT="$PWD" zsh ci/conan/build_and_test.sh "$CI_PACKAGES"

# 3) finish（W2 结构 + R36 依赖 + W3 本地编译验证，写 .ci-result.json）
python3 scripts/ohc-run.py finish rinutils 0.10.3 built
```

配方内关键点：

- `generate()`：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`
  （Conan 对 os=OHOS 会映射 `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake 无 Platform/HarmonyOS
  模块；`cmocka/2.0.2` 等 305 个仓库配方同款显式映射为 Linux）；`WITH_TEST_SUITE=ON`
  打开上游测试面；`PkgConfigDeps` 生成 `cmocka.pc` 供上游
  `pkg_check_modules(CMOCKA REQUIRED cmocka)` 使用。
- `build()`：`apply_conandata_patches` → CMake configure/build → 直接执行
  `bit-reader-and-writer-test.t.exe`（上游 CMake 只把 perl 运行器注册进 CTest，
  cmocka 用例是 run-tests.pl 以 `t/*.t.exe` glob 收集的，故直接执行）。
- `source()`：codeload URL 末尾是裸 tag（`0.10.3`），Conan `get()` 会把它当文件名
  （无扩展名→BadZipFile），显式传 `filename="rinutils-0.10.3.tar.gz"` 选择 tar.gz 解码器
  （jattach 2.2 同款先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备/CI worker 无法直连 `github.com`（curl 15s 超时） | 出网策略限制 | 改用 GitHub 官方 tar 入口 `codeload.github.com`（`github.com/archive` 302 跳转目标，字节一致；仓库内 284 个既有配方同源），sha256 与 github.com/archive 下载件二次核对一致 |
| 2 | `conan create` G2 失败：`BadZipFile: File is not a zip file` | codeload URL 以裸 tag 结尾，`get()` 取 URL basename 作文件名（无扩展名） | `get(..., filename="rinutils-0.10.3.tar.gz")`（jattach 2.2 先例） |
| 3 | 上游 configure 期从 GitHub `FILE(DOWNLOAD)` 拉 `Shlomif_Common.cmake` 且无条件要求 perl | 上游 `shlomif_common_bootstrap.cmake` 的下载回退 + 模块 `include(FindPerl)` FATAL_ERROR | 补丁 0001 内置模块裁剪副本（保留 MIT 版权，去掉 perl 依赖与系统路径拷贝），补丁 0002 把下载分支改为 `FATAL_ERROR`；configure 完全离线 |
| 4 | `ctest` 不执行 cmocka 用例 | 上游只注册 `perl_run_tests`；cmocka 用例由 run-tests.pl 的 glob 收集 | build() 中直接执行 `bit-reader-and-writer-test.t.exe`（失败即 conan create 失败，非伪造/非空壳） |
| 5 | R47 语言预检判 `mixed`（见上节） | 检具把测试/CI 脚手架计入主体 | 反证复核 + 先例（libemf/libcaca/cronic）继续；终态草稿更正；未伪造字段 |
| 6 | `gmake: jobserver mkfifo ... Operation not permitted` 警告 | HMDFS 不允许 mkfifo（E 类平台限制） | 非致命（gmake 自动降级），构建/测试均正常，如实记录 |
| 7 | 预下载/镜像工具在归档目录留下 `conandata.yml.ghfast-bak` | 工具临时镜像注入的备份残留 | 已清理，未随归档提交（JC1 敏感模式） |

## 源码修改

`patches/` 共 2 个补丁（均无平台宏，纯构建可复现性修复）：

1. `0001-cmake-Shlomif_Common.cmake.patch` — 新增 `cmake/Shlomif_Common.cmake`
   （上游 shlomif-cmake-modules 模块的裁剪副本，保留 MIT 版权与许可原文）：
   仅保留 rinutils CMakeLists 实际用到的 4 个宏（`SHLOMIF_COMMON_SETUP` /
   `READ_VERSION_FROM_VER_TXT` / `SHLOMIF_ADD_COMMON_C_FLAGS` / `SHLOMIF_FINALIZE_FLAGS`）
   及内部辅助宏；去掉 `include(FindPerl)`+FATAL_ERROR（本项目不使用任何 perl 辅助）
   与系统路径拷贝分支。
2. `0002-cmake-shlomif_common_bootstrap.cmake.patch` — bootstrap 在模块缺失时
   直接 `FATAL_ERROR`，不再于 configure 期下载（hermetic 构建；配合 0001 生效）。

上游 C 测试源、头文件、构建脚本均未修改。

## 依赖版本

- 运行时：无（纯头文件；仅 libc 头依赖）。
- 测试：`cmocka/2.0.2`（`test_requires`，不传播给消费者；ohpcd 制品仓已有
  OHOS armv8/clang15 二进制，W0 `conan download` 实测通过）。

## 验证结果

```text
# conan-verify（G0-G4 + L2/L4/L5）
✅ G1 配方完整性 PASS    ✅ G0 预构建评估 PASS    ✅ G2 conan create PASS
✅ G3 系统同名库隔离 PASS ✅ G4 产物完整性 PASS
✅ 配方验证通过: rinutils 0.10.3

# 上游 cmocka 用例（conan create build() 内真实执行，reports/conan-create.log）
[==========] tests: Running 1 test(s).
[ RUN      ] main_tests
[       OK ] main_tests
[  PASSED  ] 1 test(s).

# test_package 消费者验证（reports/conan-create.log）
1/1 Test #1: test_rinutils ....................   Passed    0.04 sec
== TOTAL CHECKS: 36, FAILURES: 0 ==
ALL 36 CHECKS PASSED

# 产物
include/rinutils/*.h          14 个头文件
lib/pkgconfig/librinutils.pc  310 B（Version: 0.10.3）
lib/cmake/Rinutils/*.cmake    包配置（RINUTILS_INCLUDE_DIR）
licenses/LICENSE              MIT
packaging/rinutils-0.10.3-ohos-aarch64.tar.gz  43548 B
```

- conan-verify G0–G4 + L2/L4/L5：PASS（报告 `reports/conan-verify-report.md`）
- 本地 CI 门禁（与平台 CI 同源 `ci/conan/build_and_test.sh`）：PASS（`.ci-result.json`）
- 上游测试：可运行面 1/1 通过（100%）；不可运行面 7 项逐项列明技术原因（见上）
- 鸿蒙消费者测试（`test_package/`）：36/36 断言通过（含负向用例）

## 交付物

| 文件 | 说明 |
|------|------|
| `include/rinutils/*.h` | 14 个头文件（alloc_wrap/bit_rw/count/dllexport/exit_error/likely/longlong/min_and_max/portable_time/rin_cmocka/rinutils/str_utils/typeof_wrap/unused） |
| `lib/pkgconfig/librinutils.pc` | pkg-config 元数据（上游文件名 `librinutils.pc`） |
| `lib/cmake/Rinutils/` | `RinutilsConfig.cmake` + `RinutilsConfigVersion.cmake` |
| `licenses/LICENSE` | MIT 许可证原文 |
| `packaging/rinutils-0.10.3-ohos-aarch64.tar.gz` | 完整包归档（43548 B，18 个文件） |

## 注意事项

- 消费者两种接入方式：CMake `find_package(Rinutils)`（Conan CMakeDeps 提供
  `Rinutils::Rinutils`），或 pkg-config（上游 pc 文件名为 `librinutils`）。
- `rin_cmocka.h` 需要外部 cmocka 头文件，仅测试场景使用；常规消费者不要包含它
  （上游设计如此，非本适配引入）。
- 上游 `.pc` 的 `prefix` 指向 Conan 缓存绝对路径（Conan 包常态）；跨机消费请用
  Conan 依赖图或 CMakeDeps 生成文件，不要直接搬运 `.pc`。

**编译结束**: 2026-09-21 18:53
**最终状态**: built
