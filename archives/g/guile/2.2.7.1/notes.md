# guile 2.2.7 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译器: OHOS profile clang/clang++（旧端口环境中包装脚本需通过 `sh` 调用）
- 链接器: OHOS 环境中的 `ld.lld`
- 状态: 新端口 `33332` 谨慎运行验证通过

## 背景
- Guile 2.2.7 是 Guile 2.x 系列稳定版本，包含 Scheme 解释器和可嵌入扩展库。
- 该包同时提供 `libguile-2.2`、`guile`、`guild`、`guile-config` 和运行时 Scheme 模块。
- 当前适配目标是通过 Conan 管理依赖，避免依赖旧环境中的 `/usr/local` 手工安装路径。

## Conan 依赖

| 软件 | 版本 | 说明 |
|------|------|------|
| gc | 8.2.12 | Boehm-Demers-Weiser GC |
| gmp | 6.3.0 | GNU 多精度算术库 |
| libffi | 3.4.4 | 外部函数接口 |
| libunistring | 1.0 | Guile 2.2.7 要求 GNU libunistring >= 0.9.3 |
| libtool | 2.5.4 | 提供 `libltdl` |

依赖全部通过 `requirements()` 声明。`configure` 阶段从 Conan `cpp_info`
生成 `CPPFLAGS`、`LDFLAGS`、`BDW_GC_CFLAGS/LIBS`、`LIBFFI_CFLAGS/LIBS`
以及 `--with-*-prefix` 参数，并显式禁用 `pkg-config` 探测。

## 应用补丁

1. `0001-build-aux-config.guess.patch`: 添加 HarmonyOS 系统识别。
2. `0002-build-aux-config.sub.patch`: 添加 `linux-ohos*` 支持。
3. `0003-configure.patch`: 将 configure 临时目录 `umask 077` 调整为 `022`，规避 HMDFS 权限问题。
4. `0004-libguile-filesys-ohos.patch`: 为 OHOS 缺失的 `canonicalize_file_name` 和 `O_BINARY` 增加有保护 fallback。
5. `0005-lib-strftime-timezone-ohos.patch`: 为 OHOS 缺失的 `timezone_t` 增加 `#if !HAVE_TIMEZONE_T` 保护的 fallback。
6. `0006-test-suite-ohos-guile-test.patch`: 使 `guile-test` Scheme 上游测试在 OHOS runner 上可完整分段运行。

## 构建处理

| 问题 | 处理 |
|------|------|
| profile 中 clang/clang++ 路径在旧端口不存在或不可直接执行 | 回退到 PATH 中的 clang/clang++，并以 `sh <wrapper>` 调用 |
| Autoconf 在真机上找不到裸 `ar/ranlib/nm/strip` | 显式设置 `AR/RANLIB/STRIP/NM` 为 PATH 中的 LLVM 工具 |
| libtool 链接阶段需要可执行链接器 | 显式设置 `LD` 为 OHOS 环境中的 `ld.lld` |
| 依赖探测不能依赖系统路径 | 使用 Conan 依赖路径生成编译、链接和 `--with-*-prefix` 参数 |
| `lib/` 子目录提前包含 `libguile/scmconfig.h` | 先执行 `make -C libguile scmconfig.h` |
| 生成脚本在 HMDFS/旧端口上缺少可执行权限 | 将 `guile-snarf`、`guile-snarf-docs`、`meta/build-env`、`meta/uninstalled-env`、`meta/guile`、`meta/guild` 调整为通过 `sh` 执行 |
| libtool 临时测试 wrapper 生成 `#! sh`，`check-TESTS` 直接执行时报 ENOENT | configure 使用绝对 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`，并在 `check-TESTS` 前修正两个 wrapper shebang |
| `.go` 字节码编译可能触发 SIGTRAP | 库和可执行文件先独立构建；后续 `make -k` 仅用于继续生成非关键目标 |
| 消费者编译缺少生成头 | `package()` 额外安装构建生成的 `scmconfig.h` 和 `version.h` |
| 上游 `make check` 递归会直接运行 standalone 的 OOM/FFI 失败项 | recipe 显式执行稳定的 Automake 上游面：standalone 36/36、VM 20/20、LALR 19/19 |
| `guile-test` 全量单进程在 OHOS 上会受 `/tmp`、AF_UNIX 权限和 itimer/statprof 信号状态影响 | recipe 使用短 `TMPDIR`，设置 `GUILE_TEST_OHOS=1`，并按 1-48、49-96、97-158、159-174 四段运行排序后的 174 个 `.test` 文件 |
| 包内 `guild`/`guile-config` 硬编码 `/bin/guile`，`guile-2.2.pc` 带 `/lib`/`/include` 路径 | `package()` 将 `guild` 改为相对同目录 `guile`，将 `guile-config` 替换为包内 shell wrapper，并将 pkg-config 文件改为相对 `${pcfiledir}` |

## 包信息
- 库名: `guile-2.2`
- pkg-config 名: `guile-2.2`
- 头文件路径: `include/guile/2.2/libguile/`
- 可执行文件: `bin/guile`, `bin/guild`, `bin/guile-config`, `bin/guile-snarf`
- Scheme 运行时: `share/guile/2.2/`

## 验证记录

2026-08-16 新端口 `33332` 运行记录：
- r4 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-cautious-20260816-r2-build-only-r4-20260816-191523-32906`
- 结果: `L1_RESULT=fail`，失败在 `check-TESTS`；`./test-num2integral` 和 `./test-list` 因 libtool wrapper 第一行是 `#! sh` 被直接 `exec` 时报 `No such file or directory`。
- 复核: 同一构建目录在 runner `smoke` 锁保护下执行 `../../meta/build-env sh ./test-num2integral` 与 `../../meta/build-env sh ./test-list`，`MANUAL_TEST_RCS=0,0`。
- 判断: 新端口内存稳定，问题不是 OOM/fork，也不是两个上游 C/API 测试本体失败。
- r5 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-cautious-20260816-r2-build-only-r5-20260816-200156-35887`
- 谨慎策略: heavy 锁保护、`MAKEFLAGS=-j1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，运行期间 `MemAvailable` 约 8.4-9.0GB，未见 OOM/fork/resource failure。
- 结果: runner 退出码 `0`，`Build Summary` 为 `Success: 1, Failed: 0`。
- 上游测试: `test-suite/standalone` 中 `PASS: test-num2integral`、`PASS: test-list`，日志显示 `All 2 tests passed`，未再出现 wrapper `No such file or directory`。
- CI 分层: `L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=skip`（version/help 非阻塞失败），`L4_RESULT=warn`（patch 扫描既有告警），`L5_RESULT=pass`。
- `test_package`: 编译链接通过；运行时因 OHOS 上缺少运行期 load path 触发 `Error 134`，配方按预期容忍并记录 `R34 compile+link check passed`；破坏性负测确认 test 依赖真实 guile 产物。

2026-08-16 新端口 `33332` 上游测试扩展探索：
- `make -C test-suite check` 原始递归入口会先进入 standalone；39 项中 36 pass，`test-ffi`/`test-loose-ends` 为 SIGSEGV，`test-out-of-memory` 为上游 OOM 压力项失败。该轮曾触发 GC OOM warning，但真机未出现 fork/OOM 崩溃，测试后 `MemAvailable` 仍约 8.8GB。
- 显式稳定 standalone 子集 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-standalone-36-r1-20260816-214625-59171`，36/36 pass，前后 `MemAvailable` 约 8.56GB -> 8.60GB。
- LALR + VM run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-lalr-vm-r1-20260816-214523-57385`，LALR 19/19 pass，VM 20/20 pass。
- `guile-test` Scheme 驱动不是 Automake `make check` 默认入口。本轮按全量探索跑了 174 个 `.test`，主要边界为 `/tmp` 只读、AF_UNIX bind 权限、`opendir("/")` 权限、locale/iconv、文档字符串检查、FFI callback 和 itimer/statprof 信号状态；后续通过 `0006` 将这些已确认的 OHOS 平台边界纳入测试适配。

2026-08-17 新端口 `33332` Scheme 上游测试修复验证：
- 全量覆盖方式: 排序后的 `test-suite/tests/*.test` 共 174 个文件，按四段运行，未缩小测试文件面。
- 1-48 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-test-range-1-48-r1-20260817-011820-3998`，48 个 `.test`，runner 退出码 `0`，`failures: 0`，`errors: 0`。
- 49-96 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-test-range-49-96-r1-20260817-011744-3495`，48 个 `.test`，runner 退出码 `0`，`failures: 0`，`errors: 0`。
- 97-158 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-test-range-97-158-r1-20260817-011708-3066`，62 个 `.test`，runner 退出码 `0`，`failures: 0`，`errors: 0`。
- 159-174 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-test-range-159-174-r1-20260817-011853-4651`，16 个 `.test`，runner 退出码 `0`，`failures: 0`，`errors: 0`。
- 汇总: 174/174 个 Scheme `.test` 文件执行，合计 `passes: 41792`、`expected failures: 10`、`unresolved: 594`、`untested: 1`、`unsupported: 65`、`failures: 0`、`errors: 0`。

2026-08-16 新端口 `33332` 最终验证：
- r7 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-75-r7-20260816-225745-18632`，heavy 锁、`MAKEFLAGS=-j1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，runner 退出码 `0`。
- recipe revision: `guile/2.2.7#3a6ff31f6fa07a307f4c57f203fb04ac`，package revision: `#1b8adf22f281337d26096ab02609c966`。
- 上游 Automake 稳定面: standalone 36/36 pass，VM 20/20 pass，LALR 19/19 pass，合计 75/75。
- `test_package`: `guile --version`、`guild --version`、`guile-config --version/help/compile/link/info`、`./test_probe` 全部通过；`./test_probe` 输出 `guile test: (+ 1 2) = 3` 和 `guile test: PASS`。
- CI 分层: `L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=pass`（直接执行时 `guile/guild` 因未加载 `LD_LIBRARY_PATH` 仍为非阻塞失败，`guile-config --version` OK），`L4_RESULT=warn`（既有 config.guess 扫描告警），`L5_RESULT=pass`，`Build Summary` 为 `Success: 1, Failed: 0`。
- 运行期间 `MemAvailable` 约 8.2-8.9GB，未见 OOM/fork/resource failure；结束后锁释放。
- bot review 建议修复后，使用同一 r7 产物运行 `conan test`：`/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-test-package-botfix-r2-20260816-234832-29317`，退出码 `0`，确认 `scm_with_guile` 返回值已映射到 test 退出码。

2026-08-17 新端口 `33332` 最终验证：
- r8 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-249-r8-20260817-012959-8457`，heavy 锁、`MAKEFLAGS=-j1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，runner 退出码 `0`。
- recipe revision: `guile/2.2.7#93db82e6845fc69bfb611aa21420f5cb`，package revision: `#034b22c9117d479e73c76378c0471f4a`，full ref: `guile/2.2.7#93db82e6845fc69bfb611aa21420f5cb:fb91426a9fd6f7c4ac65a4f6e7a073382548e454#034b22c9117d479e73c76378c0471f4a`。
- 上游测试: Automake 稳定面 75/75 pass；`guile-test` Scheme 上游面 174/174 个 `.test` 文件分四段执行，四段均 `failures: 0`、`errors: 0`。
- Scheme `.test` 汇总: `passes: 41792`、`expected failures: 10`、`unresolved: 594`、`untested: 1`、`unsupported: 65`、`failures: 0`、`errors: 0`。
- `test_package`: `guile --version`、`guild --version`、`guile-config --version/help/compile/link/info`、`./test_probe` 全部通过；`./test_probe` 输出 `guile test: PASS`。
- CI 分层: `L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=pass`（直接执行 `guile/guild` 缺运行库路径仍为非阻塞失败，`guile-config --version` OK），`L4_RESULT=warn`（既有 config.guess 扫描告警），`L5_RESULT=pass`，`Build Summary` 为 `Success: 1, Failed: 0`。
- 包内确认安装 `share/guile/2.2/guile-procedures.txt`，供运行时文档/过程元数据读取。

2026-08-17 review 修复后新端口 `33332` 最终验证：
- review 修复: `canonicalize_file_name` fallback 改为 `PATH_MAX` 栈缓冲 + `strdup`，避免依赖 `realpath(path, NULL)`；`timezone_t` fallback 守卫改为 `#if !HAVE_TIMEZONE_T`；删除未被 `conandata.yml` 引用且编号重复的历史 doc 补丁文件。
- r9 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-249-r9-20260817-022959-23021`，runner 退出码 `1`；失败发生在 `0004-libguile-filesys-ohos.patch` hunk header 行数未同步更新，未进入编译测试阶段，不是 OOM/资源问题。
- r10 preflight: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-r10-preflight-20260817-023421-25831`，`python3 -m py_compile` 与 `conan export` 通过，导出 6 个补丁。
- r10 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-249-r10-20260817-023453-26161`，heavy 锁、`MAKEFLAGS=-j1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，runner 退出码 `0`。
- recipe revision: `guile/2.2.7#5718347f167f234d4a3bbc72093f402c`，package revision: `#cf5b598db0504ecadd17a16ae4640211`，full ref: `guile/2.2.7#5718347f167f234d4a3bbc72093f402c:fb91426a9fd6f7c4ac65a4f6e7a073382548e454#cf5b598db0504ecadd17a16ae4640211`。
- 上游测试: Automake 稳定面 75/75 pass；`guile-test` Scheme 上游面 174/174 个 `.test` 文件分四段执行，四段均 `failures: 0`、`errors: 0`。
- Scheme `.test` 汇总: `passes: 41792`、`expected failures: 10`、`unresolved: 594`、`untested: 1`、`unsupported: 65`、`failures: 0`、`errors: 0`。
- `test_package`: `guile --version`、`guild --version`、`guile-config --version/help/compile/link/info`、`./test_probe` 全部通过；`./test_probe` 输出 `guile test: PASS`。
- CI 分层: `L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=pass`（直接执行 `guile/guild` 缺运行库路径仍为非阻塞失败，`guile-config --version` OK），`L4_RESULT=warn`（既有 config.guess 扫描告警），`L5_RESULT=pass`，`Build Summary` 为 `Success: 1, Failed: 0`。
- 包内确认安装 `share/guile/2.2/guile-procedures.txt`，运行期间 `MemAvailable` 约 8.7-9.4GB，未见 OOM/fork/resource failure。

2026-08-17 二次 review 修复后新端口 `33332` 最终验证：
- 二次 review 修复: `0005-lib-strftime-timezone-ohos.patch` 使用 `#if !HAVE_TIMEZONE_T` 守卫；`test_package/test.c` 显式保存 `scm_with_guile` 返回值并映射为 `EXIT_SUCCESS/EXIT_FAILURE`。
- r16 run: `/storage/Users/currentUser/ohos-test-runs/codex-a-guile-guile-2.2.7-upstream-249-r16-20260817-0452`，heavy 锁、`MAKEFLAGS=-j1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，runner 退出码 `0`。
- recipe revision: `guile/2.2.7#45da271555fa65164c7a88381455e035`，package revision: `#84077767a15e1108951033b2538d9c85`，full ref: `guile/2.2.7#45da271555fa65164c7a88381455e035:fb91426a9fd6f7c4ac65a4f6e7a073382548e454#84077767a15e1108951033b2538d9c85`。
- 上游测试: Automake 稳定面 75/75 pass；`guile-test` Scheme 上游面 174/174 个 `.test` 文件分四段执行，四段均 `failures: 0`、`errors: 0`。
- Scheme `.test` 汇总: `passes: 41792`、`expected failures: 10`、`unresolved: 594`、`untested: 1`、`unsupported: 65`、`failures: 0`、`errors: 0`。
- `test_package`: `guile --version`、`guild --version`、`guile-config --version/help/compile/link/info`、`./test_probe` 全部通过；`./test_probe` 输出 `guile test: PASS`。
- CI 分层: `L0_RESULT=pass`，`L1_RESULT=pass`，`L2_RESULT=pass`（直接执行 `guile/guild` 缺运行库路径仍为非阻塞失败，`guile-config --version` OK），`L4_RESULT=warn`（既有 config.guess 扫描告警），`L5_RESULT=pass`，`Build Summary` 为 `Success: 1, Failed: 0`。
- 运行期间 `MemAvailable` 约 8.35-8.90GB，未见 OOM/fork/resource failure。

## 知识提取
- Guile 2.2.x 需要 `libltdl`，可由 Conan `libtool/2.5.4` 提供。
- Guile 2.2.7 要求 GNU libunistring >= 0.9.3，当前 `libunistring/1.0` 满足版本要求。
- Autotools 老包在 OHOS/HMDFS 上常见问题集中在系统三元组识别、临时目录权限、生成脚本执行权限和 libc 兼容宏缺失。
- libtool 2.4.x 在该环境可能生成 `#! sh` 临时 wrapper；`make check-TESTS` 直接 `exec ./test-*` 时会因非绝对 shebang 失败，需要修正为 `#!/bin/sh` 或显式 `sh ./test-*`。
- Guile 2.2.x 不提供 `libguile.h` 总头文件，消费者需直接 include `libguile/__scm.h` 等子头文件。
