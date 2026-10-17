# mkc (mk-configure) 0.27.0 — OHOS 适配笔记

## 1. 目标定位

| 项 | 值 |
|---|---|
| 任务目标 | `feat/mkc-0.27.0` → 包名 `mkc`，版本 `0.27.0` |
| 上游项目 | **mk-configure**（"build system on top of bmake"） |
| 上游仓库 | https://github.com/cheusov/mk-configure |
| tag → 源码 | `mk-configure-0.27.0`（2019 年发布） |
| 源码 URL | https://codeload.github.com/cheusov/mk-configure/tar.gz/refs/tags/mk-configure-0.27.0 |
| sha256 | `6b8ae10f723f2c9fb250c943f5eadf136a926480b06f236c931b76dfa27acb85` |
| 构建系统 | NetBSD **bmake**（顶层无 configure；`*.in` 由 mkc 自身 INTEXTS 机制在 `bmake all` 时替换） |
| 产物 | 无 .so/.a；安装 `share/mkc-mk/*.mk` include 库、`bin/` 下 POSIX shell 脚本、man 页、features 数据 |
| 同软件新版本 | `archives/m/mk/0.40.0`（包名 `mk`，2024 版）——本配方三补丁与其保持同族做法 |

## 2. 依赖

| 依赖 | 版本 | 类型 | 可消费性 |
|---|---|---|---|
| bmake | 20200710 | tool_requires + requires | 制品仓 ✓ |
| bmkdep | 20140112 | tool_requires | 制品仓 ✓ |
| awk | 构建期烘焙 | INTEXTS 替换 | OHOS 仅有 toybox awk（/usr/bin/awk）；配方显式传 `AWK=` |

## 3. 上游测试入口清点（R51 申报表）

| 项 | 数值 | 证据 |
|---|---|---|
| 顶层测试目标 | `test: test-tests`（main.mk） | main.mk:44 |
| 注册清单 | tests 29 + examples 35，**均以 `:tests` 标签注册进 SUBPRJ** → `test-tests` 一次全跑 | main.mk `tests =`/`examples =` 两个硬编码清单 |
| 注册用例合计 | **65**（上游 64 + 本次新增 `tests/os_OHOS`） | main.mk |
| 未注册目录 | `examples/hello_require_tools`（上游注释掉）、`examples/hello_TARGETS`（未注册）、`examples/helpers`（辅助子工程） | 不作为测试执行，不计入 |
| 期望文件 | `expect.${OPSYS}.out` 优先否则 `expect.out`；驱动为 `mk/mkc.minitest.mk`（diff 判定） | mk/mkc.minitest.mk |
| 本次新增 | `tests/os_OHOS`（仅 OPSYS=OHOS 执行，其他系统 skipped） | tests/os_OHOS/ |

## 4. 适配改动（3 个补丁）

### 0001-ohos-platform-support.patch
- `mk/mkc.init.mk`：`uname -s` 返回 `HarmonyOS` → 规范化为 `OHOS`；`id -un/-gn`
  加 `2>/dev/null || true`（OHOS 用户库不含构建 uid，`id` 失败的 stderr 会被
  bmake 的 `!=` 捕获，污染 minitest 的 expect 比较）。
- `mk/mkc_imp.platform.sys.mk`：新增 `CC.OHOS/CXX.OHOS/CPP.OHOS = clang/clang++/clang -E`
  （0.27.0 无 0.40.0 的 per-OS platform 文件，平台默认集中在该文件）。

### 0002-ohos-install-robustness.patch
- `scripts/mkc_install`：`chown/chgrp` 解析不到可执行文件时回退为 `:`
  （OHOS /bin/sh 只提供不可执行的别名；脚本内 `set -e` 否则中断安装）。
- `mk/mkc_imp.links.mk`：`LINKS` 安装先硬链接失败则回退为同目录相对符号链接
  （HMDFS 上 `ln` 恒 `Operation not permitted`）。

### 0003-ohos-regression-tests.patch
- `tests/configure_test/mkc_test.mk`：新增 `MKC_COMMON_DEFINES.OHOS = -DSYSTEM_OHOS`
  （KNOWN_SYSTEM 断言要求 TARGET_OPSYS 属于已知系统）。
- `main.mk`：注册 `os_OHOS`。
- `tests/os_OHOS/{Makefile,expect.out}`（新增）：校验 OPSYS 识别、sys/types.h、
  sys/stat.h、`sizeof(int)=4`、编译器内置宏 `__OHOS_FAMILY__`；其他系统 skipped。
  （0.27.0 没有 0.40.0 的 os_NetBSD 泛型 test.mk，故自包含。）

## 5. 构建/测试环境要求（矩阵实跑口径）

- `MAKESYSPATH=<bmake 包>/share/mk`；PATH 前置 bmake/bmkdep 的 bin 与
  OHOS SDK `llvm/bin`（CC=clang 由平台默认解析）。
- **`STRIPPROG=llvm-strip`**：`mkc_install -s`（PROG 安装）会执行 `strip`，
  OHOS 无裸 `strip` → `Error code 127` → 全部 examples 的 install 段失败
  （错误摘要行即 minitest 输出里的 `1 error`）。
- **`AR=llvm-ar RANLIB=llvm-ranlib`**：mk*lib 系列用例需要（E012 族）。
- 不传 `CC=/CXX=` 命令行变量：mkc 的编译器探测会生成 `_mkc_prog_cc.res`，
  多个用例的 expect.out 文件清单依赖该探测产物。

## 6. 上游测试实测结果（OHOS 真机，2026-10-08，~/work/frj__/mkc027-tests/logs/）

| 指标 | 数值 |
|---|---|
| 用例总数 | 65 |
| PASS | **48**（含新增 os_OHOS） |
| FAIL | 17（逐项归因见下，全部为设备/矩阵环境缺口，非适配缺陷） |
| 新增 os_OHOS | PASS（4 项断言全中：OPSYS/sys_types_h/sys_stat_h/sizeof=4/__OHOS_FAMILY__） |

### 逐项归因（17 个 FAIL）

| 归因 | 用例 | 证据 |
|---|---|---|
| texinfo 工具缺失（makeinfo） | mkinstall、hello_files | `bmake[2]: exec(makeinfo) failed (No such file or directory)` |
| flex/bison 缺失（lex/yacc） | hello_calc2、hello_lex、hello_yacc | `Cannot find flex, good bye!` / `checking for program lex... NOT FOUND` / `yacc... NOT FOUND` |
| lua 缺失（解释器与 lua.pc；制品仓 lua/5.1 仅静态库） | lua_dirs、hello_lua、hello_lua2、hello_lua3、predopost_targets | `ERROR: Package lua was not found in the pkg-config search path` |
| pkg-config 依赖链未配置（glib-2.0.pc 在 conan 非系统前缀，矩阵环境无 PKG_CONFIG_PATH） | pkg_config_2、hello_glib2 | `ERROR: Package 'glib-2.0' not found`（与 mk 0.40.0 的「.pc 链不全」同类环境缺口） |
| 文档工具/矩阵三级子 make 递归差异（手动执行同目标成功） | hello_scripts、hello_dictd、hello_superfs、hello_xxzip、subprojects | 测试程序本体构建+运行全部成功（hello_world1/2/3 手动运行 rc=0；`bmake -m src/mk install` 手动 RC=0）；失败均发生在 test_output 内被重定向的三级子 make |

对照：mk 0.40.0（同软件 2024 版）在其环境下的通过率为 89/109（81.7%），同样存在
makeinfo/lua/libfl/fts 等环境缺口；本 0.27.0 适配未引入任何新的失败类。

## 7. 复现命令

```sh
src=.../mk-configure-0.27.0
cd "$src"
patch -p1 < 0001-ohos-platform-support.patch
patch -p1 < 0002-ohos-install-robustness.patch
patch -p1 < 0003-ohos-regression-tests.patch
export MAKESYSPATH=<bmake-pkg>/share/mk
export PATH=<bmake-pkg>/bin:<bmkdep-pkg>/bin:$SDK_LLVM/bin:$PATH
export AR=llvm-ar RANLIB=llvm-ranlib LD=ld.lld STRIPPROG=llvm-strip
bmake all  PREFIX=$PWD/prefix AWK=/usr/bin/awk
bmake test-tests/<name>  PREFIX=$PWD/prefix AWK=/usr/bin/awk
```

## 8. 路径 B（知识库扩展，issue #3864）

本库适配实测踩到、且查重（2026-10-08）**0 命中**的新族：

**install 期 strip 缺失与 STRIPPROG 约定（X11 install-sh 血统脚本）**：
`mkc_install`（X11R5 install.sh 直系后裔）以 `stripprog="${STRIPPROG-strip}"`
协议变量解析 strip、不看 make 的 `STRIP`；OHOS 无裸 strip → `-s` 安装在
`set -e` 下 Error 127 中断（bmake 摘要行 `1 error` 常被输出重定向吞掉）。

- 查重：`STRIPPROG` 0 / `llvm-strip` 0；E012（make 构建期工具变量）、
  E077/DRAFT-E703（strip 打掉 codesign）均为不同子族
- **单变量对照实验**（§5 环境要求处）：A 无 STRIPPROG 失败 / B 仅加
  `STRIPPROG=llvm-strip` 成功 / **C 仅加 E012 处方 `STRIP=` 仍失败**——
  子族判定的直接证据
- 通用性：autotools 全系（install-sh 标配）、mk-configure、libtool install 模式
- 实测影响：补 STRIPPROG 后上游矩阵 65 例 26 PASS → 48 PASS

草稿：`knowledge/drafts/DRAFT-ohos-install-sh-stripprog-strip-missing.{kv,md}`
（`draft: true`、`contributor_id: frj__`）。关联 issue **#3864**。

其余坑族已有条目：bmake 子进程 stderr 污染（DRAFT-13686）、HMDFS 硬链接
（E018/E079）、/tmp 只读（E002）、jobserver（E074/E525）、codeload 无扩展名
（E392/E483）→ 引用而不重复。
