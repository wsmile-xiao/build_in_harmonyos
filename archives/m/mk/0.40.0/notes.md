# mk (mk-configure) 0.40.0 — OHOS 适配笔记

## 1. 目标定位

| 项 | 值 |
|---|---|
| 任务目标 | `feat/mk-0.40.0` → 包名 `mk`，版本 `0.40.0` |
| 上游项目 | **mk-configure**（"build system on top of bmake"） |
| 上游仓库 | https://github.com/cheusov/mk-configure |
| tag → commit | `mk-configure-0.40.0` → `4442e64ed8486e77afa8a091182aea8583e40445`（2024-10-06） |
| 源码 URL | https://github.com/cheusov/mk-configure/archive/refs/tags/mk-configure-0.40.0.tar.gz |
| sha256 | `7daaa79467389cd3bb7875ad24d0e56ba460b8f6165e138eb222620caf67f903` |
| 构建系统 | make（NetBSD **bmake**；顶层命令 `mkcmake`） |
| 产物 | 无 .so/.a/可执行二进制；安装 `mk/*.mk` include 库、`bin/` 下 POSIX shell 脚本、man 页、features 数据 |

## 2. 依赖（前置 W0 结论：强制第三方依赖全部可消费）

| 依赖 | 版本 | 类型 | ohpcd 可消费性 |
|---|---|---|---|
| bmake | 20200710 | tool_requires + requires | `conan download bmake/20200710 -r=ohpcd --only-recipe` → exit 0 |
| bmkdep | 20140112 | tool_requires | `conan download bmkdep/20140112 -r=ohpcd --only-recipe` → exit 0 |
| awk | 系统自带 | 运行期 | OHOS `/data/service/hnp/bin/awk`（GNU Awk 5.4.0） |

> `mkdep` 本身不在制品仓，但上游 `builtins/prog_mkdep.in:34` 接受 `bmkdep|nbmkdep|mkdep` 任一变体，
> 且构建期只使用**已发布二进制**（`conan create --build='mk/*'`，依赖从不从源码构建）。

## 3. 上游测试入口清点（R51 申报表，适配前完成）

| 项 | 数值 | 证据 |
|---|---|---|
| 测试驱动 | `mk/mkc.minitest.mk`（`test` 目标：`${MAKE} test_output` 输出与 `expect.out` 做 `diff`） | `mk/mkc.minitest.mk:11-25` |
| 顶层测试目标 | `test` = `test-tests test-examples` | `main.mk:48` |
| `tests/` 注册用例数 | **46**（上游 45 + 本次新增 `os_OHOS`；清单硬编码于 `tests.mk`） | `tests.mk` |
| `examples/` 注册用例数 | **63**（清单硬编码于 `examples.mk`） | `examples.mk` |
| **注册用例合计 = 实际执行数** | **109**（tests 46 + examples 63；逐例执行，无漏测） | `logs/21-final-cases.log`（109 CASE = 109 EXIT） |
| `tests/` / `examples/` 目录数 | 46 / 65——`examples/helpers` 为辅助子工程（`main.mk:9`）、`examples/hello_TARGETS` 上游未注册（仅 `doc/NOTES` 提及），二者均**不作为测试执行**，故与上表注册数不相等 | `main.mk:9`、`doc/NOTES` |
| 期望文件命名 | `expect.${OPSYS}.out` 优先，否则 `expect.out`（全树仅 `examples/files/expect.NetBSD.out`） | `mk/mkc.minitest.mk:18-22` |
| 本次新增用例 | **`tests/os_OHOS`**（OHOS 专用，≥1） | `tests/os_OHOS/`、`tests.mk` |
| 跳过机制 | `NOSUBDIR=` 可排除用例 | `mk/mkc_imp.subprj.mk:15-23` |

## 4. 适配改动（3 个补丁）

### 0001-ohos-platform-support.patch
- `mk/mkc.init.mk`：`uname -s` 返回 `HarmonyOS` → 规范化为 `OHOS`（与 `__OHOS__` / conan `os=OHOS` 对齐）；
  同时把 `_MKC_USER/_MKC_GROUP` 的 `id(1)` 调用静默化（`2>/dev/null || true`）。
- `mk/mkc_imp.platform.OHOS.mk`（新增）：`CC.OHOS ?= clang`、`CXX.OHOS ?= clang++`、`CPP.OHOS ?= clang -E`。
- `mk/Makefile`：把 `mkc_imp.platform.OHOS.mk` 加入安装清单 `FILES`。

**根因**：OHOS 无裸 `cc/c++/cpp`，`CC ?= ${CC.${TARGET_OPSYS}:Ucc}` 会退化为不存在的 `cc`；
且 `HarmonyOS` 不是上游已知平台，所有 `OPSYS` 分支都落到默认值。

**id(1) 的特殊性**：`id -un` 在本机失败（`id: bad uid 20020084`，用户库不含构建 uid）。
更关键的是 **bmake 的 `!=` 会捕获子进程 stderr**，`sh: id: inaccessible or not found` 会被写进
make 输出，直接污染 minitest 的 `expect.out` 比较（表现为 `configure_test`、`endianness`、
`cccxx_type`、`FSRCDIR`、`reqd_clean_cache`、`require_prototype`、`test_subprj_dash`、`WARNERR`
等 8+ 个用例同时 FAILED）。

### 0002-ohos-install-robustness.patch
- `scripts/mkc_install.in`：`chown/chgrp` 解析不到可执行文件时回退为 `:`（脚本内 `set -e`，
  否则安装会在 `cp` 与 `mv` 之间中断，**文件静默不落地**）。
  注意 OHOS `/bin/sh` 对 toybox 内置命令提供**别名**：`command -v chown` 返回
  `alias chown=chown`，所以必须解析为绝对路径后再判 `-x`。
- `mk/mkc_imp.links.mk`：`LINKS` 安装先尝试硬链接，失败则回退为**同目录相对符号链接**。
  HMDFS 上 `ln`（硬链接）恒报 `Operation not permitted`（`features/Makefile:43-44,55-56` 的
  `mkc_imp.f_*.mk` / `mkc_*.h` 别名文件）。

### 0003-ohos-regression-tests.patch
- `tests/configure_test/mkc_test.mk`：新增 `MKC_COMMON_DEFINES.OHOS = -DSYSTEM_OHOS`
  （该文件的 `KNOWN_SYSTEM` 断言要求 `TARGET_OPSYS` 属于已知系统）。
- `tests.mk`：新增 `os_OHOS`。
- `tests/os_OHOS/{Makefile,test.mk,expect.out}`（新增）：OHOS 专用回归用例，仅 `OPSYS == "OHOS"` 时执行，
  校验 `sys/types.h,sys/stat.h`、`sizeof(int)` 以及 OHOS 编译器内置宏 `__OHOS__` / `__OHOS_FAMILY__`；
  其他系统上打印 `skipped`（与 `tests/os_Linux`/`os_NetBSD`/`os_OpenBSD` 同构）。

> 三处补丁均无平台宏注入、无功能语义改动；`__OHOS__` 仅作为**被测断言的数据**出现在测试文件中。

## 5. 构建与安装

```bash
bmake all     PREFIX=<prefix>
bmake install PREFIX=<prefix>     # 必须与 all 使用同一 PREFIX
```

- mk-configure 会把 `@prefix@/@bindir@/@mkfilesdir@/@mkc_libexecdir@/@BMAKE@/@AWK@/@CC@/@CXX@`
  **烘焙进生成的脚本**，因此 `all` 与 `install` 的 `PREFIX` 必须一致；
  conan 配方使用 `self.package_folder`，从而使安装后的 `mkcmake` 在包目录内自洽。
- `bmake configure` 在**全新源码树**上会失败（`mkc_check_prog: No such file or directory`，
  进而 `mkdep(1) cannot be found`）：`configure` 的子工程顺序使 `mk/` 先于 `scripts/` 解析，
  而此时 `scripts/mkc_check_prog` 尚未生成。上游可用入口是 **`bmake all`**（先构建 `scripts/`）。
  同理 `bmake cleandir` 后再直接 `bmake test` 也会失败——必须先 `bmake all`。

## 6. 上游测试实测结果

**运行方式**：最终补丁树（tarball + 3 补丁）→ `bmake all` → **逐个用例** `bmake test-tests/<name>` /
`bmake test-examples/<name>`（避免 `bmake -k test` 在嵌套 submake 中提前终止，保证不漏测）。

| 指标 | 数值 |
|---|---|
| 用例总数（tests 46 + examples 63） | **109** |
| **PASS** | **89** |
| **FAIL** | **20**（逐项归因：环境缺口 9（makeinfo 4 + lua 4 + libfl 1）/ 平台·库缺口 4（libc fts 2 + 用户库 uid 与 HMDFS 权限 2）/ 测试机环境 4（conan perl 串扰 3 + `.pc` 链不全 1）/ 未定位 3；合计 9+4+4+3=20，其中 `libdeps` 已修复为 PASS） |
| SKIP | 0（未使用 `NOSUBDIR` 屏蔽任何用例） |
| 通过率 | 81.7% |

- 全量原始日志（最终树，官方 tarball + 3 补丁）：`/storage/Users/currentUser/Desktop/GPQworkspace/mk-0.40.0-build/logs/29-final-cases.log`（109 CASE = 109 EXIT）
- 逐用例摘要：`reports/upstream-tests-summary.txt`
- 逐用例归因报告：`reports/upstream-tests.md`

**由本次适配修复的用例**：`tests/configure_test`、`endianness`、`cccxx_type`、`FSRCDIR`、`reqd_clean_cache`、
`require_prototype`、`test_subprj_dash`、`WARNERR`、`mkshlib`、`mkstaticlib`、`mkpiclib`、`mkprofilelib`、`mkdll`、
`examples/libdeps`，以及**新增**的 `tests/os_OHOS`。

### 已知平台限制（设备环境缺口，与本包适配无关）

| 用例 | 缺失项 | 证据 |
|---|---|---|
| `tests/mkc_features`、`examples/fts` | OHOS libc 无 `fts.h` / `fts_*` | `echo '#include <fts.h>' \| clang -E -` 失败 |
| `tests/mkinstall`、`examples/files`、`examples/files2` | 无 `makeinfo`(texinfo)；制品仓亦无 `texinfo` 配方 | `conan download texinfo/* -r=ohpcd` → Found 0 |
| `tests/lua_dirs`、`examples/hello_lua*` | 无 `lua` 解释器与 `lua.pc`（ohpcd `lua/5.1` 仅含 `liblua.a`） | `find` lua 包仅 `include/lib/man` |
| `tests/mkc_install` | HMDFS 权限归一化：`chmod 0700→0770`、`0750→0770`，测试断言 `-rwx------`/`drwxr-x---` 无法成立 | `chmod 0700 f; ls -l f` → `-rwxrw----` |
| `examples/lexer`（及依赖 `-lfl` 的用例） | 无 `libfl`（flex 运行库） | `ERROR: cannot find function yywrap:fl` |

## 6.1 W3 本地 CI 模拟结果（ci/conan/setup.sh + build_and_test.sh）

| 门禁 | 结果 |
|---|---|
| W2 结构完整性 | pass（test_package/ 含 `conanfile.py` + `test.sh` + `MANIFEST.yml`）——⚠️ 见 §6.2：首次本地 W3 的该结论曾因工作树中 **gitignored 的 Conan 生成脚本残留**而误判为通过 |
| R36 依赖已发布 | pass（`conan create --build='mk/*'`，依赖全部为已发布二进制，未从源码构建） |
| JC 杂项文件 | **pass**（官方 `ci/scripts/junk_check.sh`，`prdiff` 模式，12 个文件，`JC6 涉及软件数: 1（合规）`） |
| L0 | pass: all checks passed |
| L1 | pass: upstream tests + test_package executed（L1a/L1b/L1c OK；**L1e 破坏性反向验证通过**，证明 test_package 真实依赖本包） |
| L2 | pass（12 个命令中 4 个支持 `--version`：mkc_check_funclib / mkc_check_header / mkc_check_sizeof / mkc_check_version；mkc_* 系列上游本就不实现 `--version`，非阻塞告警） |
| L4 | warn（误报：正则 `gets\b` 命中上游测试目录名 `predopos`t`_tar`get``s``，补丁未引入任何 C 危险函数） |
| L5 | pass: bin/ has content |
| 构建汇总 | Total 1 / Success 1 / Failed 0（100%） |

> **本地 `finish` 的 W3 步骤会失败**，原因是 `junk_check.sh` 在**无提交**时退化为 `full` 模式（`git diff origin/main...HEAD` 为空），
> 从而扫出 **main 上其他包已跟踪的历史垃圾文件**（`archives/c/cloog/0.21.1/.build-closed`、
> `archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`、
> `archives/t/thc/3.8/.staging-verified`），与本 PR 无关（W2 禁止在单个 PR 中改动其他软件目录）。
> 一旦本分支产生提交，JC 即自动切到 `incremental` 模式（仅检查本 PR 文件），与上表的 `prdiff` 模式结论一致。

## 6.2 ⚠️ L0c/PF3 假阳性陷阱：test_package 的 gitignored 残留

**现象**：本地 `finish`（W3）与 `preflight` 的 L0c/PF3 对 `test_package/` 结构检查报 **pass**，但在干净检出（CI / 新克隆）下必然 **FAIL**。

**根因**：`conan create` 会在 **`test_package/` 原地**生成 `conanbuild.sh` / `conanrun.sh` 等环境脚本（因为本地 recipe 无 `layout()`，conan 直接把生成器写到 test_package 目录）。这些文件被 `.gitignore` 覆盖（`**/test_package/conanbuild*.sh`、`**/test_package/conanrun*.sh`），**不会进入提交**；但 CI 的 L0c 实现是
```bash
for ext in c cpp cc cxx sh py; do
    found=$(find "$TEST_PKG_DIR" -maxdepth 2 -name "*.$ext" -not -name "conanfile.py" -print -quit)
```
——它会把这个残留的 `conanrun.sh` 当成"独立测试源"，于是本地 **假性通过**；干净检出下 test_package 只剩 `conanfile.py` + `MANIFEST.yml` → `[fail] L0c: No test source files in test_package/`。

**复现**（不依赖本地残留）：
```bash
git archive HEAD | tar -x -C /tmp/clean-checkout
ls <clean-checkout>/archives/m/mk/0.40.0/test_package/     # 仅 conanfile.py + MANIFEST.yml
```

**处置**：本包**新增独立测试源 `test_package/test.sh`**（消费者端到端：mkcmake 构建 C 工程 → 运行产物校验输出 → 调用 `mkc_check_version`），并由 `conanfile.py::test()` 以 `self.run(..., env="conanrun")` 调用，使 L0c / PF3 / L0d / R34 全部在干净检出下成立。

**通用教训**：任何依赖"目录里存在某类文件"的本地检查，都必须用**干净检出**（`git archive HEAD`）而非工作树来复验——工作树里的 gitignored 残留会让结构类门禁假性通过。

## 7. 复现命令

```bash
# 前置
conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
conan install --requires=bmake/20200710  --build=never -r=ohpcd -g VirtualRunEnv
conan install --requires=bmkdep/20140112 --build=never -r=ohpcd

# 构建 + 测试
src=.../mk-configure-mk-configure-0.40.0
cd "$src"
patch -p1 < 0001-ohos-platform-support.patch
patch -p1 < 0002-ohos-install-robustness.patch
patch -p1 < 0003-ohos-regression-tests.patch
bmake all PREFIX=$PWD/prefix
bmake test-tests/os_OHOS
bmake test-tests/<name> ; bmake test-examples/<name>
```

## 8. 未修改的内容

- 未删除、未禁用任何上游用例（无 `NOSUBDIR` 屏蔽）。
- 未改上游测试的判定逻辑（`expect.out` 仅新增 `tests/os_OHOS/expect.out`）。
- 未使用 `--build=missing` 绕过依赖（依赖全部为已发布二进制）。
---

**编译结束**: 2026-09-29 09:17
**最终状态**: built
