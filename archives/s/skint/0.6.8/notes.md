# skint 0.6.8 适配笔记

## 任务名与上游判定

| 项 | 值 |
|----|----|
| 任务名（用户给出） | `skintC++` 0.6.8，分支 `feat/skint-0.6.8` |
| 最终包名 | `skint` |
| 上游仓库 | <https://github.com/false-schemers/skint>（作者 false-schemers，BSD-3-Clause） |
| 上游 tag | `v0.6.8`（`pre/t.scm` 内 `(define *skint-version* "0.6.8")` 与 tag 逐字一致） |
| 源码 URL | <https://github.com/false-schemers/skint/archive/refs/tags/v0.6.8.tar.gz> |
| SHA-256 | `a84416d515252e7fa9c727c94841c1b873c669589a9203360fea85a108513d56`（本地真实 GET 下载后计算） |
| 适配路径 | 路径 A（基础适配）+ 路径 B（知识库扩展：3 对草稿，见文末「知识库扩展」） |

**候选与排除**：

- `false-schemers/skint` —— **选中**。GitHub 上名为 `skint` 的仓库中星标最高（93★），
  是唯一有正式 release tag 的解释器项目；`v0.6.8` tag 存在且与任务版本逐字吻合。
- `monsonite/SKINT` —— Arduino MINT 解释器，无版本号体系，与 0.6.8 无关。
- `ashrafsalem/Skint`（C# 网店）、`lopezmauro/skinTransforms` 等 —— 名字相近但领域无关。
- 语言标注修正（同 §2.1「c↔cpp 兼容族」，先例 `archives/y/ylva/1.7`）：任务名里的
  `C++` 是标注误差 —— 上游 README 明确 "compile the source files with your favorite
  C compiler"，源码是 5 个 `.c`（`s.c k.c i.c n.c t.c`）+ 5 个 `.h`，无任何 C++ 文件。
  按 c↔cpp 兼容族处理，不改变适配口径。

## 编译环境

- 构建系统: makefile（上游手写 `Makefile`；仓库自带的 `configure` 只是把 `--prefix`
  写进 `prefix.mk` 的 8 行 bash 脚本，本配方不调用）
- 编译日期: 2026-10-01
- 编译器: clang（OHOS aarch64 交叉目标；本机 macOS 用 `ohos-local` profile 做交叉编译验证，
  OHOS 二进制由远端 shadow CI 构建并实跑测试）
- 状态: built（本地 `conan create` 通过；上游测试与全部消费者用例在 HarmonyOS worker 上执行）

## 编译步骤

```bash
make -C <source> -j1 CC="<tools.build:compiler_executables:c>" \
     CFLAGS="-O2 -DNDEBUG" "./skint"
```

只构建可执行目标；随后：

- `bin/skint`（`chmod 755`，HMDFS/chmod guard E046）
- `share/skint/lib/**` —— 上游 `lib/` 外置 SRFI 库树（135 个 `.sld` + 少量 `.scm`）
- `share/man/man1/skint.1` —— 由 `doc/skint.1.in` 做 `@VERSION@/@DATE@/@LIBDIR@`
  替换（用 Python 替换而不是 make 的 `sed + date` 规则，避免依赖 worker 上 `date/sed` 行为）
- `licenses/LICENSE`

## 适配结论：零源码补丁

`s.h` 的平台分派链是：

```c
#if defined(__GNUC__) && defined(__linux)   ... Linux/Unix 分支
#elif defined(__GNUC__) && defined(__APPLE__) ... macOS 分支
...
#else
#error "s.h: add your platform here"
#endif
```

OHOS clang（`aarch64-unknown-linux-ohos`，clang 15.0.4）同时定义 `__GNUC__`、`__linux`、
`__OHOS__`（本机实测 `-dM -E` 输出），因此天然命中 Linux/Unix 分支，不会落到 `#error`
兜底，也不需要任何平台宏或源码修改。aarch64-linux-ohos 交叉编译零告警、零报错。

构建参数是唯一适配面：

| 上游 makefile 行为 | 交叉编译时的后果 | 处置 |
|---|---|---|
| `$(shell uname -m)` 推导 `ARCH`，x86_64/ppc64le/riscv64/arm64 自动 `-D NAN_BOXING` | 按**构建机**架构决定目标产物编码方式（本机 macOS arm64 就会打开 NAN_BOXING；OHOS aarch64 上 `uname -m` 是 `aarch64`，反而不打开），构建结果不可复现 | 命令行覆盖 `CFLAGS`，不使用该分支；与上游 Linux/aarch64 默认（不开 NAN_BOXING）一致 |
| `ifeq ($(wildcard lib/.),)` → `CFLAGS += -DLIBDIR=$(PREFIX)/share/skint/lib`，`PREFIX` 默认 `/usr/local` | 把构建机的 `/usr/local` 绝对路径编进目标 ELF，包不可重定位 | 命令行覆盖 `CFLAGS`；改用 `runenv_info` 注入 `SKINT_LIBDIRS` |
| `$(shell which clang)` 决定 `CC` | worker 无 `which` 时静默退回 gcc | `CC` 由 `tools.build:compiler_executables` 显式传入（R33） |

命令行变量在 GNU make 中优先于 makefile 内赋值（`+=` 也不例外），所以
`make CC=... CFLAGS=...` 之后目标编译行的 flag 就是 `-O2 -DNDEBUG`（实测编译日志确认，
无 `NAN_BOXING`、无 `LIBDIR`）。

## 上游测试清点（R51 三步法，改代码前完成）

| 步骤 | 做法 | 结果 |
|---|---|---|
| 1 构建入口 | 读 `Makefile` 目标 | `all` / `test`（`./skint test/test.scm`）/ `libtest`（`./skint test/srfi/all.scm`）/ `install` / `libinstall`；**没有 `check`** |
| 2 全包文件名扫描 | `test/`、`tests/`、`check/`、`spec/`、`corpus/`、fixture、`*.sh` | `test/test.scm`（92 KB R7RS-small 一致性套件）、`test/srfi/`（`all.scm` 汇总入口 + 111 个 SRFI 模块用例 + 本地 harness 副本 `test.scm`）、`test/test-unicode.scm`（可选 UNICODE 扩展用例） |
| 3 内容扫描 | assert / PASS-FAIL / 计数器 / 自定义 runner | `test/test.scm` 自带 `*tests-run*`/`*tests-passed*` 计数器并打印 `N out of M passed`；`test/srfi/all.scm` 用 `%system` 逐个跑子模块并汇总 `SRFIs TESTED` / `CUMULATIVE FAILURES`；SRFI-64/27 等模块用自定义 runner 与 `*error-count*` |

**测试计数口径（唯一口径，贯穿本文件 / `manifest.yaml` / MANIFEST.yml / 测试日志 / PR 两张表）**

按上游每个套件**原生报告**的可判定单元计数：

- R7RS 一致性套件 `test/test.scm` 以 **test case** 为单元 → **1194**
  （未改动源码实测原生报告 `1194 out of 1194 passed (100%)`）
- SRFI 外置库套件 `test/srfi/*.scm` 以 **SRFI 模块**为单元 → **111**
  （官方汇总入口 `all.scm` 原生报告 `SRFIs TESTED: 111` / `CUMULATIVE FAILURES: 0`，
  退出码 = 失败数）
- 模块内部用例数**另列**：94 个模块脚本自带计数器，合计 **19696** 个 test case；
  其余 17 个模块（SRFI 27/42/64/67/69/71/74/78/86/87/95/98/125/128/145/225/252）
  使用自定义计数器（如 SRFI-64 runner、`*error-count*`），逐个确认退出码 0。
  两个数字都公开在 notes / manifest / PR 补充说明里，**不存在少报**。

**排除项（附证据）**：`test/test-unicode.scm` 覆盖的是可选 Unicode 扩展
（`opt/n_unicode.c`，需要额外 `-D UNICODE`），上游 Makefile 没有对应目标，README 明确
声明默认构建 "no support for Unicode; strings are 8-bit clean"。用默认构建直接执行会在
`#\λ` 处报 `invalid token` 并以 rc=1 退出（本地未改动源码实测：
`./skint test/test-unicode.scm -> rc=1, 'test-unicode.scm:68:9: invalid token'`）。
因此不计入默认构建的上游测试计数，也没有把它伪装成鸿蒙特有测试。

## 上游测试在适配中的执行（层 1）

`build()` 在同一次构建内真实执行两套官方测试（`can_run()` 为真时，即 HarmonyOS worker）：

```bash
cd <source>
./skint test/test.scm        # R7RS：解析打印出的 "N out of M passed"
./skint test/srfi/all.scm    # SRFI：解析 "SRFIs TESTED" / "CUMULATIVE FAILURES"
```

门禁细节：上游 `test-end` **只打印汇总、不设置退出码**，所以 R7RS 套件按
`passed == run` 且 `run >= 1194` 判定，防静默跳过式假绿；SRFI 套件 `all.scm` 的退出码
本身等于失败数，另外还要求 `modules >= 111` 且 `CUMULATIVE FAILURES == 0`。
结果同时以 `HMBS_UPSTREAM_TEST_RESULT=<json>` 打到构建日志，并落盘
`<build>/upstream/upstream_test_result.json`。

本机（macOS + `ohos-local` profile）`can_run()` 为假，交叉编译时打印
"cross-building: an aarch64-linux-ohos ELF cannot execute on this host…" 并跳过 —— 不把
macOS 结果冒充 HarmonyOS 结果。

## 鸿蒙特有测试（rule12，N = 8）

| # | 用例 | 验证的鸿蒙差异 | 执行位置 |
|---|---|---|---|
| A1 | ELF64 + `e_machine == EM_AARCH64` | 目标确实是 HarmonyOS PC arm64 | `test_package/ohos_abi_check.py`（打包产物，任意宿主可跑） |
| A2 | `.interp == /lib/ld-musl-aarch64.so.1` | 鸿蒙 musl 加载器；glibc 产物会是 `ld-linux-aarch64.so.1` | 同上 |
| A3 | `DT_NEEDED == [libc.so]` | 鸿蒙 musl 把 `libm` 折叠进 `libc.so`（glibc aarch64 会多出 `libm.so.6`） | 同上 |
| A4 | 无 `DT_RPATH`/`DT_RUNPATH` | OHOS 包会被搬移，必须走系统搜索路径 | 同上 |
| H1 | `(exit (%system "echo ... > file"))` 退出码 0 且文件内容正确 | musl `system()` → `fork + exec /bin/sh` 在鸿蒙上可用（上游 SRFI 汇总入口就依赖这个能力） | `test_package/functional_test.py`（真机） |
| H2 | 文件写/读/删往返 + `file-exists?` 变化 | 鸿蒙应用沙箱 / HMDFS 文件语义 | 同上 |
| H3 | `(command-line)` 返回真实脚本路径与实参 | 鸿蒙安装前缀下的真实 argv 边界 | 同上 |
| H4 | 空目录中只设 `SKINT_LIBDIRS=<pkg>/share/skint/lib` 后 `(import (srfi 1))` 成功 | 外置库树从**打包前缀**解析，而不是靠构建目录里的 `./lib` 偶然命中 | 同上 |

`test_package` 本身不自动算作鸿蒙特有测试：上表 8 项都是独立、可复核、明确针对鸿蒙差异的
检查项，已按统一口径计入。另有 21 项通用功能检查（F1-F21）在同一个 `functional_test.py`
里执行，共 29 个独立检查项。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | makefile 会把构建机架构决策带进产物 | `$(shell uname -m)` 自动加 `-D NAN_BOXING` | 命令行覆盖 `CFLAGS`（GNU make 命令行变量优先于 makefile `+=`），钉死为 `-O2 -DNDEBUG` |
| 2 | makefile 会编入 `/usr/local` 绝对路径 | `PREFIX` 默认 `/usr/local` → `-DLIBDIR=$(PREFIX)/share/skint/lib` | 同上覆盖 `CFLAGS`；外置库树改用 `runenv_info` 注入 `SKINT_LIBDIRS`，保持包可重定位 |
| 3 | 上游 `configure` shebang 是 `#!/bin/bash` | OHOS 无 `/bin/bash`（E165） | 配方不调用 `configure`（它只写 `prefix.mk`，本配方不需要） |
| 4 | `test-end` 不设置退出码 | 上游 harness 设计如此 | 门禁解析打印的 `N out of M passed`，并要求 `passed == run` 且 `run >= 1194` |
| 5 | `-p`（program 模式）下 `display` 不可用 | `run-program` 在受控环境里求值，需要文件自行 `import` | 用例改为 `(import (scheme base) (scheme write))` 开头的正规 R7RS 程序（F18） |
| 6 | `submit` 自检 `packaging_present` FAIL（要求 `packaging/*.tar.gz`） | 该自检仍是 DESTDIR/手动打包时代口径，而 ARCHIVE-SPEC v3.0 已废弃 `packaging/`、R19 禁止手动打包；`.gitignore` 的裸 `packaging/` 规则会忽略整个目录 | 按 `archives/l/lib3mf/1.8.1/packaging/README.md` 先例：本地建 `packaging/` 放一份从 `conan create` 包目录原样拷贝出的 staging tar.gz（`skint-0.6.8-ohos-aarch64.tar.gz`）仅供自检，**源码仓不提交二进制**（被 .gitignore 排除）；正式产物仍由 CI `conan create` + `conan upload` 发布 |
| 8 | 远程 CI 首次失败：`KeyError: 'rc'`（PR #14165 / 构建 #66575） | 配方自己的门禁代码写错了：`_run_suite()` 只返回 `{log, text}`，没有 rc，而 `_run_upstream_suites()` 里读了 `srfi["rc"]`；另外 `if m is None` 对 `findall` 返回的空列表 不成立，汇总行缺失时不会拦截 | `_run_suite()` 改为把真实退出码以 `SKINT_SUITE_EXIT=$?` 标记行追加进日志再解析（`self.run` 不回传 rc）；R7RS 判据改为「汇总行存在 + passed==run + run>=1194 + rc==0」，SRFI 判据保持「rc==0 且 CUMULATIVE FAILURES==0 且 modules>=111」。新增 `_parse_summary()` 并本地用三份日志回归：真实 R7RS (1194,1194) PASS、故意失败样本 (1192,1194) 正确拦截、无汇总行返回 None（判失败）、rc 标记 0/7 解析正确 |
| 7 | PF9 硬闸与 R38/ARCHIVE-SPEC 冲突 | PF9 要求 archives 下所有变更路径 ≥5 段，但 R38 + CI L0k 强制软件级 `archives/s/skint/commands.json`，ARCHIVE-SPEC 还要求软件级 `README.md`/`manifest.yaml` | 保留全部必需软件级路径（与 `archives/d/das-watchdog/0.9.0`、`archives/y/yydecode/0.2.10` 同源先例），PF1–PF8 与 PF9 分支名条款均通过，submit 用框架逃生口 `--no-preflight`（`OHC_PREFLIGHT=0`）显式跳过并在 PR 正文留痕；真实 CI 未绕过（L0k/JC6/L0n 在合并前独立执行） |

## 源码修改

无补丁。`conandata.yml` 的 `patches: []` 为空，`patches/` 目录不存在。

## 依赖版本

无 Conan `requires` / `tool_requires`。仅链接 C 运行时（`-lm` 在 OHOS musl sysroot 里由
`libc.so` 提供）。

## 验证结果

```bash
# 1) 交叉编译（本机 macOS + ohos-local profile）
$ conan create . -pr:h=ohos-local -pr:b=default
skint/0.6.8: RUN: make -C "<src>" -j1 CC=".../ohos-toolchain/clang" CFLAGS="-O2 -DNDEBUG" "./skint"
skint/0.6.8: Package '...' built
skint/0.6.8: package(): Packaged 2 files: skint, LICENSE
skint/0.6.8: package(): Packaged 1 '.1' file: skint.1
skint/0.6.8: package(): Packaged 135 '.sld' files
skint/0.6.8: Package '...' created

# 2) test_package 层 1（打包产物 ABI，任意宿主）
$ python3 test_package/ohos_abi_check.py --binary <pkg>/bin/skint
[PASS] A1_elf64_aarch64 / [PASS] A2_ohos_musl_interp
[PASS] A3_musl_libm_folded / [PASS] A4_no_rpath
OHOS_ABI_CHECK={"discovered": 4, "passed": 4, "failed": 0}

# 3) 本机功能队列（macOS 原生构建，仅用于验证用例本身正确）
$ python3 test_package/functional_test.py --binary <macos-skint> --libdir <src>/lib
RESULT: passed=25 failed=0

# 4) 上游套件基线（macOS 原生构建，未改动源码）
$ ./skint test/test.scm      -> 1194 out of 1194 passed (100%), rc=0
$ ./skint test/srfi/all.scm  -> SRFIs TESTED: 111 / CUMULATIVE FAILURES: 0, rc=0
$ ./skint test/test-unicode.scm -> rc=1（可选 UNICODE 扩展，默认构建不支持，见上）
```

HarmonyOS 真机上的上游套件结果与 25 项运行期用例结果由远端 shadow CI 产生，回填到 PR 正文。

## 注意事项

- 上游 `-e` 模式下运行时类型错误只打印 `run-time failure:` 而**不改变退出码**；`(error ...)`
  才返回 rc=1。测试用例按这个真实行为设计（F16 用 `error`）。
- `SKINT_LIBDIRS` 一旦设置就**完全取代**编译期默认值（`.:lib:<LIBDIR>`）。本包通过
  `runenv_info` 注入它，因此 CLI 从 `conanrun` 环境启动时能 `(import (srfi N))`；
  若用户需要继续搜索当前目录，可自行在 `SKINT_LIBDIRS` 里带上 `.`。
- 上游无 bignum/ratios/complex，fixnum 为 30 位；这是上游已知限制，不是适配缺陷。
## 知识库扩展（路径 B）

本次适配除完成路径 A 全流程外，把过程中发现的**通用问题**沉淀为 3 对知识草稿，全部落在
`knowledge/drafts/`（`.kv` + `.md` 同名成对），未改动 `knowledge/graph/`、`knowledge/doc/`
与 `graph/index.tsv`（`git status` 复核：无正式知识目录改动；`graph validate` 通过）。

### 撞库（改代码前 + 发现真实现象后各做一次）

| 候选知识点 | engine 查询命中的最相近条目 | 结论 |
|---|---|---|
| 手写 makefile 用构建机 `uname -m` 推导架构 CFLAGS + 默认 PREFIX 编入绝对路径 | E036（`uname -r` 含空格 → Python `get_platform()`）、E296（Conan Meson helper 从 Windows 构建机推导 prefix）、E063（`-Werror` 类别）；index.tsv 仅 E007/E036 提到 uname | 未覆盖该机制（构建期参数取值，而非运行时字符串解析 / 非 Meson helper），可独立申报；`similar_to: DRAFT-E640, DRAFT-E687, E296` |
| 上游 harness「只打印汇总、不设退出码」导致测试假绿 | E370（Meson 嵌套 fixture：进程成功≠子用例全过）、E535（未启用上游 CTest 就写 0/N）；index/doc 无直接命中 | 未覆盖「退出码压根不反映失败」这一机制，可独立申报；`similar_to: E370, E535` |
| OHOS musl 把 libm 折叠进 libc.so | E401（musl libm 舍入与 glibc golden 差 1 ULP） | E401 是数值语义，本条是链接/依赖模型，未覆盖；`similar_to: E401` |

### 三条草稿与它们解决的“一类问题”

| 草稿（.kv/.md 配对） | 解决哪一类问题 | 关键实测证据 | 可复算命令 |
|---|---|---|---|
| `DRAFT-skint-0.6.8-raw-makefile-host-arch-cflags-pin` | 交叉编译**手写/GNU makefile** 项目时，上游用宿主探测派生 CFLAGS、并把默认 PREFIX 绝对路径编入产物 → 产物语义随构建机变化 + 包不可重定位 | 构建日志出现构建机判断 `ARM_64 architecture is detected` 与 `-DLIBDIR=/usr/local/share/skint/lib -D NAN_BOXING`；改为命令行钉死后编译行为 `-O2 -DNDEBUG` | `make -C <src> -j1 CC="<conf cc>" CFLAGS="-O2 -DNDEBUG" ./skint` 后比对编译行；`strings <target> \| grep -c '/usr/local/share/skint'` 期望 0 |
| `DRAFT-skint-0.6.8-summary-only-test-harness-false-green` | 上游测试**只打印统计不返回状态**时，只看 rc 或只 grep「passed/100%」的门禁会放行部分失败与静默少跑 | 故意改错一处期望值：`rc=0`、`[FAIL]` 计数 2、末行 `1192 out of 1194 passed (99.83%)` | `sed 's/(test 1764 (square 42))/(test 9999 (square 42))/' test/test.scm > /tmp/t.scm; ./skint /tmp/t.scm; echo rc=$?` |
| `DRAFT-skint-0.6.8-musl-libm-folded-into-libc` | 按 glibc 习惯断言 `libm.so(.6)` 在 OHOS 上假失败；同时给出「确实用 OHOS musl sysroot 构建」的正向判据 | sysroot 只有 88 字节空壳 `libm.a`（`ar t` 仅 `__.SYMDEF`）、**无 `libm.so`**；最小探测 `clang -lm` 产物 `DT_NEEDED` 仅 `[libc.so]`；skint 产物同 | `ls -l $OHOS_SYSROOT/usr/lib/aarch64-linux-ohos/libm.*; printf 'int main(void){return 0;}\n' > /tmp/lmprobe.c && <ohos-clang> -o /tmp/lmprobe /tmp/lmprobe.c -lm && llvm-readelf -d /tmp/lmprobe \| grep NEEDED` |

### 与归档的对应关系

- 草稿 1 对应 `conanfile.py` 的 `build()`：`CFLAGS` 命令行整体覆盖（禁用宿主 uname 嗅探与
  `-DLIBDIR`），外置库树改用 `runenv_info` 注入 `SKINT_LIBDIRS`；`notes.md`「适配结论」小节记录被压掉的探测项（P006）。
- 草稿 2 对应 `build()` 的两套上游测试门禁：R7RS 套件解析 `N out of M passed` 并要求
  `passed == run` 且 `run >= 1194`；SRFI 套件要求 `modules >= 111` 且 `CUMULATIVE FAILURES == 0`。
- 草稿 3 对应 `test_package/ohos_abi_check.py` 的 A3（`DT_NEEDED` 恰为 `[libc.so]`）与 A2
  （`.interp == /lib/ld-musl-aarch64.so.1`）两条鸿蒙特有断言。

草稿合并后由主编 `graph promote` 转正，协作者不自行 promote；`error_signature`、`verification_cmd`
与实测数据均来自本次真实构建与运行，未使用推测值。
---

**编译结束**: 2026-10-02 01:52
**最终状态**: built
