# linuxlogo 6.01 适配笔记

## 编译环境
- 构建系统: makefile（上游为手写 `./configure` + 裸 Makefile，非 autoconf；configure 首行自述 This is not a real autoconf configure script）
- 编译日期: 2026-09-25
- 编译机: B 机（HarmonyOS aarch64，HongMeng Kernel 1.12.0）
- 编译器: profile `ohos-aarch64` 的 `tools.build:compiler_executables` c=`/data/service/hnp/bin/clang`（配方按 dict 取键，缺 `ar` 时回落 `llvm-ar`）
- CONAN_HOME: `~/tmp/ch/home-linuxlogo`（`core.sources:download_cache=~/tmp/ch/dlcache`、`tools.build:jobs=2`）

## 门禁判决（本轮实测，逐条指回盘上输出）
| 门禁 | 判决原文 | 出处 |
|---|---|---|
| conan-verify | `**Verdict**: PASS`，G1/G2/G3/G4 全 PASS | `reports/conan-verify-report.md` 第 3 行（G1 第 12 行、G2 第 27 行、G3 第 31 行、G4 第 35 行） |
| conan-verify 控制台 | `✅ 配方验证通过: linuxlogo 6.01` ⇒ `VERIFY_RC=0` | `~/tmp/uc2/z34-linuxlogo/verify3.log` 第 26 / 30 行 |
| W3 本地 CI 模拟 | `✅   ✅ W3 本地 CI 模拟通过` | `~/tmp/uc2/z34-linuxlogo/finish2.log` 第 69 行 |
| W3 归档判决 | `.ci-result.json` `exit_code: 0`，`integrity_hash: 262b5d6a254497b3`，`log_sha256: e86948aa34a4ada56e12393b4b4d1c7954ad391b4e3f582490cc90dbf8484c61` | `archives/l/linuxlogo/6.01/.ci-result.json`（时间戳 2026-09-25T05:28:50） |
| W3 内 CI 脚本 | `L0_RESULT=pass: all checks passed`、`L1_RESULT=pass: test_package executed`、`Pass rate: 100.0% (1/1)` | `reports/w3-local-ci.log` 第 325 / 326 / 337 行（该文件 md5 `86b30d7dd8419471eac46b61098357df`，339 行） |
| finish 收尾 | `失败步骤: step5b, step8`、`FINISH_RC=2` | `~/tmp/uc2/z34-linuxlogo/finish2.log` 第 114 / 142 行 |

### 非阻塞项如实披露（不改判、不隐藏）
- `step8` 失败原文 `⚠️  gen_summary 失败: 'str' object has no attribute 'append'`（finish2.log 第 103 行）⇒ 框架 SUMMARY 生成缺陷，与本包配方无关，未修框架。
- `step5b` 为全仓存量一致性红（finish2.log 第 79 行 `finalize 完成，有 1 个缺失 + 2 个一致性问题`）；其"缺失项"是 `reports/test-report.md`、`packaging/`、`.staging-verified` 三件 legacy 归档面，`reports/` 与 `.ci-result.json` 均在本仓 `.gitignore` 内（第 80/96 行），当前批次不入 PR。
- verify 的 L2/L4/L5 判决行是 `⏭️ 跳过（无 cache 路径）` ⇒ **不得当作"二进制可执行"证据**；可执行性的实证是 test_package 真跑（见下表 consumer 行）。
- Step 1/2/3 有 `无法定位源码目录: orig=None, work=None`、`G0: 找不到原始 tarball` 告警（finish2.log 第 13/22/34 行）：本轮源码由 conan `source()` 直取 dlcache，未走 init-build 的 orig/work 目录，属流程形态差异；构建与打包实际成功（w3-local-ci.log 第 270-271 行 Packaged 行）。

## 源码获取
上游只在 http://www.deater.net/weave/vmwprod/linux_logo/ 以明文 HTTP 发布
linux_logo-6.01.tar.gz，R39/PF7 不接受明文 http，也不接受 deb.debian.org
（PF7 的 Debian 下游主机名单，`scripts/ohc/preflight.py` `_PF7_DEBIAN_HOSTS`）。改用作者在官网页面直接链接的自有仓库
release tag：https://github.com/deater/linux_logo/archive/refs/tags/v6.01.tar.gz
（sha256 ca831148b39d6c86eb5413068aca9e450f2f704c95cee3ccb7c0dd574d8e6e16）。
可核证据：B 机 `~/tmp/uc2/z34-linuxlogo/dl` 下 `codeload-v6.01.tar.gz`（116823 B，sha256 与 conandata 逐字相同）与
`deb-6.01.orig.tar.xz`（97876 B，sha256 bdde3abeea2dce73c892340ad48e6c05a8a1b5cd7ca42766efa8bf6957694041）
分别解到 `dl/xgh` 与 `dl/xdeb`，两边均 146 个文件，`diff -r` 无输出 ⇒ 同一份上游原件。
构建主机侧 `github.com:443` 不可达（curl rc 28）而 `codeload.github.com` 可达，故按检查清单第 7 条把上述
已验证官方 tarball 以 sha256 预置进 `~/tmp/ch/dlcache/s/`；`conan create` 日志实证命中缓存：
`Source ... retrieved from local download cache`（`reports/conan-create.log`）。
conandata.yml 内**只有官方 URL**，镜像域不得写入配方。

## 编译步骤（配方 build() 实际执行）
```bash
sh ./configure --prefix=<package_folder>          # cwd = source_folder
make CC=<profile c> AR=llvm-ar OS=Linux USE_I18N=0 TRANSLATIONS= -j1
make -C tests CC=<profile c> AR=llvm-ar LIBSYSINFO=libsysinfo-0.3.0 -j1
```
W3 全量构建实证产物：`package(): Packaged 2 files: linux_logo, COPYING` +
`Packaged 1 '.gz' file: linux_logo.1.gz`（w3-local-ci.log 第 270-271 行）。
真机执行 `linux_logo` 返回 0、stdout 2976 字节，输出含
`HarmonyOS Version HongMeng Kernel 1.12.0` 与 `31.2GB RAM`（w3-local-ci.log 第 310 行
`ALL 6 CHECKS PASSED, stdout 2976 bytes`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 未覆写时 make 报 `make: O2: No such file or directory` 与 `[Makefile:75: parse_logos] Error 127 (ignored)`，最终 `*** [Makefile:81: load_logos.h] Error 127` | 手写 configure 的参数协议只有 `--help`/`--prefix`（第 17-24 行 `case "${1%=*}"`），命令行 `var=value` 与环境变量都不构成可靠入口；第 44-57 行 `which gcc`→`which cc` 双双落空时只 `echo "C compiler not found!"` 且**不给 CC 赋值**，第 63-67 行无条件重写 `CFLAGS="-O2"`，第 92-97 行把 `CC=`（空）与 `CFLAGS=-O2` 写进 Makefile.default，**configure 仍 exit 0** | 只在 **make 命令行**覆写 CC/AR/OS/USE_I18N/TRANSLATIONS（GNU make 行内变量优先级高于 Makefile 内 include 的赋值，并经 MAKEFLAGS 下发给 libsysinfo 子 make）；机制与对照实验见"路径 B"节 |
| 2 | libsysinfo 报 `cd .../libsysinfo-0.3.0/HarmonyOS: No such file or directory` | configure 第 30 行 `OS=\`uname\`` ⇒ HarmonyOS，而 libsysinfo 用 `cd $(OS) && make` 选后端，上游无该目录 | make 命令行 `OS=Linux`（该后端只读 /proc，HongMeng 提供） |
| 3 | 15 个 `-Wint-conversion` 致命错误（`linux_logo.c:59` 等，call to undeclared function `gettext`） | configure 第 69 行 `$CROSS$CC $CFLAGS -c intl_test.c` 在 CC 为空时必然失败 ⇒ 判成需要 i18n，而 OHOS native sysroot 无 `libintl.h` | make 命令行 `USE_I18N=0` 走 `_()` 恒等宏，并 `TRANSLATIONS=` 跳过 po/ |
| 4 | 上游 `install` 目标不可用 | configure 第 31 行 `INSTALL=\`which install\`` 在本机为空（设备无 install(1)），且 install 还会 `cd po && make install` | `package()` 手工 copy + `os.chmod(0o755)`（检查清单 Makefile 第 3 条）；机制同池草稿 M13，本 PR 按"一 PR 一知识"只申报问题 1 |
| 5 | `self.run("sh ./configure ...")` 找不到 `./configure` | 配方用 `basic_layout`，conan 在 `build()` 期把进程 cwd 切到 `build-release`，而 configure 在源码目录 | 三处 `self.run` 全部显式 `cwd=self.source_folder`；`tests/test1` 用 `./linux_logo`、`tests/test2` 用 `../linux_logo` ⇒ 两个用例统一在 `cwd=<source>/tests` 下执行 |
| 6 | conan 2.29 抛 `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list` | 该 conf 只注册为 dict，`:c` 形态不是合法 conf 名（检查清单 Makefile 第 6 条的字面写法在本仓多个已合入配方里都用 dict 形态） | 改 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后 `.get("c")`/`.get("ar")` |
| 7 | CI 门禁 L0d 判 `stub_test_method` | `test_package/conanfile.py` 只用 `subprocess.run` 取断言，字面缺 `self.run` | 增加一遍 `self.run('<exe> > /dev/null 2>&1')`（conan 自带 runner，非零即抛，同时覆盖 runenv 包装），`subprocess` 那遍负责抓 stdout 做内容断言 |

## 上游测试（rule4 五维账本）
tests/README: "Here are some tests checking for buffer overruns in linux_logo."
两个 Makefile 均无 `check:`/`test:` 目标（`grep -n "^check:\|^test:" Makefile tests/Makefile` 无输出）⇒ 无 automake/CTest harness，注册面即静态面。

| 维度 | 数值 | 依据 |
|---|---|---|
| N_static | 4 | `tests/` 下 test1、test2（shell 驱动）+ memory_print、memory_method（tests/Makefile `all:` 构建的两个程序） |
| N_registered | 4 | 同上，无 harness 注册层 |
| N_executed | 4 | 配方 `build()` 内真实执行，W3 判决行 `reports/w3-local-ci.log` 第 261-264 行：test1 `OK (rc=0)`、test2 `OK (rc=1, marker matched)`、memory_print `OK (rc=0, marker matched)`、memory_method `OK (rc=0, marker matched)` |
| 未执行 | 0 | 本轮四项全部执行，无 skip 项 |
| 通过率 | 4/4（执行项口径），分母不缩即 4/4 静态全量 | 每项按"期望退出码 + 输出标记"双断言；test2 期望 rc=1 且必须打印 `Not enough room in string`，这是上游截断守卫触发即通过 |
| N_consumer | 1 个程序、6 项断言 | `test_package/conanfile.py`；W3 第 310 行 `ALL 6 CHECKS PASSED, stdout 2976 bytes`；被测二进制峰值 RSS 实测 4576 KB（`getrusage(RUSAGE_CHILDREN).ru_maxrss`）⇒ `MANIFEST.yml` 记 `max_rss_mb: 5` |

## 产物
| 文件 | 大小 | 说明 |
|------|------|------|
| bin/linux_logo | 59776 B | 命令行程序，无库无头（`package_info` bindirs=["bin"]、includedirs/libdirs 置空） |
| man/man1/linux_logo.1.gz | — | 上游 man page 原件 |
| licenses/COPYING | — | 上游只有 COPYING（无 LICENSE 文件），GPL-2.0-or-later |

## 路径 B 判定
适配路径: B（新建知识草稿）
使用知识库: 是（`recipe-search linuxlogo` 零命中（语料 6173 条）；`preflight_check.sh` 预检通过、无依赖需检查；`knowledge/graph` 与 `knowledge/drafts` 全量检索）
知识库扩展: DRAFT-linuxlogo-6.01-custom-configure-drops-nonprefix-argv
关联 Issue: 待创建（PRE_CREATE）

判 `create` 的举证（不是措辞问题，是机制不同）：本包与池草稿 M12
（`DRAFT-PKG-VER-custom-configure-only-cli-args-no-env`，来源 lzip 1.24.1）在**承重维度上正好相反**——
M12 的机制是"命令行 `var=value` 生效、环境变量被忽略"，解法是把编译器当 **configure 参数**传；
本包在 B 机同一份源码三臂实测（`~/tmp/uc2/z34-linuxlogo/probe2`，2026-09-25 05:2x，`grep -E '^(CC|CFLAGS)=' Makefile.default`）：

| 臂 | configure 调用形态 | 生成 Makefile.default |
|---|---|---|
| a1 | `sh ./configure --prefix=P` | `CC=`（空）、`CFLAGS=-O2` |
| a2 | `sh ./configure --prefix=P CC=clang CFLAGS=-DMARKER9911` | `CC=`（空）、`CFLAGS=-O2` ⇒ **命令行 var=value 被丢弃** |
| a3 | `CC=<abs>/clang CFLAGS=-DMARKER9911 sh ./configure --prefix=P` | `CC=<abs>/clang`、`CFLAGS=-O2` ⇒ **CC 环境变量意外存活**（第 50-54 行 not-found 分支不给 CC 赋值，env 得以保留），CFLAGS 仍被无条件重置 |

⇒ 照 M12 的解法（把 `CC=` 塞进 configure 命令行）在本包**必然无效**（a2 即否证），故不能判 hit；
新条目申报的机制是"手写 configure 只认 `--prefix`、非 `--prefix` 的 argv 静默丢弃、编译器探测失败仍 exit 0
并把空 CC 烧进生成物 ⇒ 唯一可靠通道是 make 行内变量"。与既有条目区分：E2167 是手写 configure 对白名单外
`--*dir` 参数**致命退出 Unknown option**（与本包"静默丢弃"相反，且解法为
`AutotoolsToolchain.update_configure_args`）；E386/E540 家族是 autoconf 生成物的 `$CONFIG_SHELL` re-exec
在 HMDFS 下 getcwd 失败（本包与 shell 无关，`/bin/sh` 与 hnp bash 均可复现）。
M13（`INSTALL=\`which install\`` 在本机为空 ⇒ 上游 install 目标不可用）同包命中，但按"一 PR 一知识"不并入本 PR，
此处备查。

## 注意事项
- 每次 `conan-verify` / W3 运行期都会把 `conandata.yml` 的 `sources.url` 临时改成镜像列表
  （本轮 W3 后现场为 `url:` + `gh-proxy.com` 与官方 URL 两行）⇒ 提交前必须从 HEAD 还原并核 `git diff` 为空、
  禁词按**值行**锚定为 0；本仓 `.gitignore` 已排除 `reports/` 与 `.ci-result.json`，故 W3/verify 日志不入库。
- `commands.json` 为软件级（含 `versions["6.01"]`），CI L0k 判决行 `[ok] commands.json valid (type=tool)`；
  其 `binary` 布尔字段无门禁读取，本 PR 不为该外观字段改动。
- 框架侧未改：B 机 `init-build` 因 `scripts/ohc/check_env.py:33` 的 `NameError` 不可用（上一棒报告），
  本轮全部经 `conan-verify` / `finish` 路径完成，未触碰框架文件（W2 判决 `仅含配方变更 (8 文件)，无框架文件`，
  finish2.log 第 108 行附近）。

---

**编译结束**: 2026-09-25 05:28
**最终状态**: built
