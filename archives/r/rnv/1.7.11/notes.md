# rnv 1.7.11 适配笔记

## 基本信息

- 软件：rnv（Relax NG Compact Syntax validator in C，David Tolpin）
- 版本：1.7.11
- 上游：https://github.com/hartwork/rnv（官方维护仓库，release 1.7.11）
- 源码：`https://github.com/hartwork/rnv/archive/refs/tags/1.7.11.tar.gz`
- sha256：`3bfa192d8cea7a84e6a247e2d42b5baf911d9bab9920ec64dcafd15f2d015f91`
- 许可证：BSD-3-Clause（COPYING，随包安装到 licenses/）
- 构建系统：GNU autotools（configure.in + Makefile.am）
- 产物：命令行工具 `rnv` / `arx` / `rvp` / `xsdck`（application 包）
- 依赖：expat/2.8.2.1（强制，configure 硬检查）
- 申请人：gcw_uQ09W7jl（队伍：干）

选用 GitHub tag 归档而非 SourceForge tar.xz 的原因：
官方下载站（SourceForge）在本机网络下返回 403，无法验 sha256；
hartwork/rnv 是上游官方维护仓库，同版本 git 归档内容与发行包同源，
且 `github.com` URL 可被 CI 的 gh-proxy 镜像自动回退，下载更可靠。

## 编译步骤（直编方案，不依赖 autotools 生成链）

1. `get()` 解包 GitHub tag 归档（strip_root）。
2. `generate()`：`VirtualBuildEnv` + `AutotoolsToolchain` 提供 conanbuild
   环境（`$CC/$CFLAGS/$LDFLAGS` 含交叉 `--target`/sysroot）与 expat
   `-I/-L/-lexpat -ldl -lm`（Gentoo ebuild 同款 LIBS）；**无
   `tool_requirements`**。
3. `build()` 内按 `Makefile.am` 源表直编：18 个源 → `librnv1.a`，
   `dxl.c/dsl.c` → `librnv2.a`（`ar rcs`，缺 `ar` 时回退 `llvm-ar`）；
   编译宏 `-DUNISTD_H=<unistd.h> -DEXPAT_H=<expat.h>`（configure.ac 同款）
   与 `-DRNV/ARX/RVP_VERSION="1.7.11"`（Makefile.am 同款）；尖括号 -D 值
   用单引号包裹防 sh 重定向解析。
4. 链接 `rnv(xcl.c) / arx / rvp / xsdck` 四个 CLI 到 `obj/`。
5. 上游测试：`test.c` 对 `librnv1.a` 编出 `rnvtest` 并真实运行
   （`TESTS = rnvtest` 唯一用例，见下）。
6. `package()` 手工拷贝四二进制 → `bin/`、预置 `man/*.1` →
   `share/man/man1`、COPYING → `licenses/`。
7. SCM 支持保持关闭（默认），不引入 ncurses/readline/X11 依赖。

## 上游测试

- 口径：`Makefile.am` 中 `TESTS = rnvtest` 且 `check_PROGRAMS = rnvtest`
  （注册用例 `test.c`：`s_test()` + `xsd_test()`，自包含、无数据文件，
  退出 0 即通过）。真机核验按文件枚举口径要求 N=8（1 注册 + `tst/c/`
  下 7 个 `*_test.c`），故声明总数为 8 并全量接入：`ht/rnd/rx/u2/u3`
  5 个可构建草稿给安全调用（ht 无参、rnd 接最小 RNC、rx 接 `a/a`、
  u2/u3 接管道 stdin），`strops_test.c`（引用已删除的 `strops.h`）与
  `u_test.c`（调用已删除的 `u_base_char` 系 API）在 1.7.11 已是 stale
  文件（任何平台均无法编译链接，证据见 `conanfile.py stale_evidence`），
  如实记 `skipped` 并附 `test_failure` gaps。
  `tst/run.sh` 为作者本地脚本（硬编码 `/home/dvd` 私有路径），非自动化 harness，
  不计入；`tst/d|dt|g` 为 `.rnc/.xml` fixture，不计入。
- 总数：`upstream_test_total: 8`，口径 `autotools_tests`（官方 TESTS
  注册 1 个，核验文件枚举要求 8，审计见 `MANIFEST.yml`）。
- 执行：`build()` 内把 8 个程序逐个编译链接并真实执行，
  退出码直接计 `passed/failed`、编译/链接失败记 `skipped`（无字符串数数、
  无算术修补），上报 `HMBS_UPSTREAM_TEST_RESULT`（framework=automake，
  discovered=8）。核心全绿但 `executed<total` 时按 ifopt/2.1.4 先例发
  `failed+gaps` 且不抛错（让证据到达后端）；仅 `rnvtest` 或可执行项真
  失败才抛错。前一轮 N=1 被 rule4 判少报（核验 N=8 > 声明 N=1）；再前一轮
  N=8 以 `status=passed` 上报 `skipped=2` 自相矛盾被判 incomplete，本轮修正
  状态逻辑。
- test_package：`test.sh` 4 项真实检查（`rnv -v` 版本输出、`rnv -c` 语法检查、
  有效 XML 通过、无效 XML 被拒绝——第 4 项同时是 harness 证伪对照），
  上报 `HMBS_TEST_PACKAGE_RESULT`（discovered=4）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档无 configure | 上游不提交生成文件 | `autoreconf -fi` 引导（adcli 先例） |
| 2 | config.guess 不识别 HarmonyOS | `uname -s`=HarmonyOS 无分支 | `--build` 强制 triplet + config.guess 内联补丁（buddy/cadaver 先例） |
| 3 | configure 临时目录不可写 | `umask 077` + HMDFS setgid | 改为 `umask 022`（E011/adcli 方法） |
| 4 | 缺 expat 即 configure 硬错误 | AC_CHECK_LIB(expat) | `requires expat/2.8.2.1` + inc/lib 显式指向 |
| 5 | `rnv -v` 单独执行退出码为 1 | 无 schema 参数时 usage+return 1（xcl.c） | test.sh 只断言输出含 `rnv version 1.7.11`，不判退出码 |
| 6 | 真机 `autoreconf: inaccessible or not found` | 配方调 `autoreconf -fi` 但真机 PATH 无 autoconf 套件 | 首轮加 `tool_requires(automake/autoconf/libtool)`，见 #7 |
| 7 | `tool_requires` 引入的 m4/1.4.19 在真机编不出 | m4 自身 configure 硬调 `/data/service/hnp/bin/bash` 报 inaccessible（Error 127），autotools 引导链在该 worker 上根本不可用 | 改直编方案：删 `build_requirements`，按 Makefile.am 源表用 `$CC/$CFLAGS/$LDFLAGS`（conanbuild）直编 + 直链，宏与 LIBS 与 configure.ac/Makefile.am/Gentoo ebuild 同款，不再调 autoreconf/configure |
| 8 | 直编后 `$CC`（profile 钉死的 `/data/service/hnp/bin/clang`）报 inaccessible | 预检沙箱内 hnp/bin 下文件不可执行（autoreconf/bash/clang 同指纹三连），`$CC` 绝对路径绕过 PATH 直击坏点 | `_resolve_cc()` 运行时逐个跑 `<cand> --version` 取证：conf 钉死值 → usr/local/bin/clang → PATH clang/cc → 裸名；首个成功者用于全部编链，仅换 CC 不碰标志（zurl 同构先例 adapt）；test_package 的 hnp bash 选择加 `X_OK` 门（误判只回退到 sh，安全方向） |
| 9 | 预检 7 个 tst/c 程序全部 SKIP（`ht.h/rnc.h/rx.h/u.h not found`），仅 rnvtest 执行 | harness 编译命令只加 `-I tst/c`，漏了头文件所在的源码根 `-I src`（注释写对、命令写错） | 编译命令补 `-I src` 后 5 个可构建草稿恢复运行，但 strops（缺 `strops.h`，已更名为 `s.h/s_tokcmpn`）与 u_test（调已删除的 `u_base_char` 系 API）仍失败，且 N=8 口径下 `status=passed` 与 `executed=6/skipped=2` 自相矛盾被 rule4 判 incomplete |
| 10 | rule4：`passed` 状态与上游结果矛盾（discovered=8/executed=6/skipped=2 却标 passed） | 复核 `Makefile.am` 全文：`TESTS=rnvtest` 且 `check_PROGRAMS=rnvtest`，`tst/c/*` 零引用、`tst/run.sh` 硬编码 `/home/dvd` 私有路径——7 个草稿从不是注册测试，N=8 为口径虚增；stale 二文件的全平台不可构建恰好是佐证 | 曾收敛到官方口径 N=1，但真机核验按文件枚举要求 N=8，少报被判 incomplete；本轮改回 N=8 并修正状态逻辑 |
| 11 | rule4 少报：上游核验 N=8 > 声明 N=1（2026-09-27 预检，evidence 门） | 核验按 `test.c + tst/c 7 个 *_test.c` 文件枚举计 8（`api.github.com .../tst/c?ref=1.7.11` 7 文件 + `test.c`；`Makefile.am` 仅注册 `TESTS=rnvtest`，见 raw `Makefile.am`），声明 N=1 必然少报；且前次 N=8 以 `passed+skipped` 自相矛盾被判 incomplete，状态逻辑亦须修正 | 全量接入 8 程序：`rnvtest` + 5 可运行草稿（ht 无参、rnd 接最小 RNC fixture、rx 接 `a/a`、u2/u3 接 `printf hello` 管道，避免裸 stdin 挂起）真实执行，2 stale（strops 缺 `strops.h`、u 缺 `u_base_char`）记 `skipped` + `test_failure` gaps；`passed` 仅当 `executed==discovered`，核心全绿但 `executed<total` 时发 `failed+gaps` 且不抛错（ifopt/2.1.4 先例 adapt），仅 `rnvtest`/可执行项真失败才抛错；`MANIFEST.yml` total 改 8、上游表列 8 项、`manifest.yaml`/notes/PR 草稿同步 |

## 验证结果

- 真机预检（HarmonyOS aarch64，conan create 全流程）待 HMBS 本轮结束后自动执行；
  上游测试通过率与新增用例通过率以预检日志实测为准，CI 最终结果为准。
