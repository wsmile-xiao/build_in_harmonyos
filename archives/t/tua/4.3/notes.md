# tua 4.3（The UUCP Analyzer）适配笔记

## 项目信息
- **软件名称**: TUA / The UUCP Analyzer（Taylor UUCP 日志分析器）
- **版本**: 4.3（上游版本，1996-02-16；证据：`configure.in:11` `VERSION=4.3`、`NEWS:1`）
- **上游作者**: Lele Gaifax `<lele@seldati.it>`，**GPL-2.0-or-later**（`src/tua.c` 横幅、`COPYING`）
- **源码**: 上游原站 `http://stone.trew.it/~lele/tua-4.3.tar.gz` 已失效（域名停用），
  且无 `salsa.debian.org` 维护仓库；采用 **Debian 官方源码归档 pool** 的
  `tua_4.3.orig.tar.gz`（SHA256 与 `tua_4.3-17.dsc` 的 Checksums-Sha256 一致）
- **SHA256**: `aaf2b40e34e0e4056f127720286287ecf3dfa8fc7ef234dd9c1d3e5ac3b2baba`
- **构建系统**: autotools（autoconf 2.4 生成的 `configure` + 手写 `Makefile.in`）
- **语言**: ANSI C（C89 时代代码）

## 编译环境
- **目标平台**: HarmonyOS PC aarch64（`uname -s` = HarmonyOS，HongMeng Kernel 1.12.0）
- **编译器**: clang 15.0.4（`/data/service/hnp/bin/clang`，目标 `aarch64-unknown-linux-ohos`）
- **Conan Profile**: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++）
- **构建日期**: 2026-09-30

## 依赖（W0）
`conanfile.py` 的 `requires()` 为空，**无第三方链接依赖**（仅 OHOS libc）。
`bison/3.8.2` 为**构建期工具**（`tool_requires`），用于生成 `src/pcdl_gram.c`
（发行包未附生成结果，上游 `configure` 需要 yacc）。
W0 依赖可消费性预检（`conan download -r=ohpcd --only-recipe`）：对照实验
`zlib/1.3.1`→0、`zzz-nonexistent-xyz/9.9.9`→1；`bison/3.8.2`→0。

## 编译过程（真实命令）

```bash
# 探索阶段（$BUILD_SRC_DIR 为解压后的源码树）
export PATH=/data/service/hnp/bin:$PATH
bash ./configure --prefix=$PREFIX --disable-nls    # YACC=bison -y
make -j4
make install                                       # 安装 bin/tua + lib/TUA.pcd
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E1 | `configure: error: ./intl/libgettext.h: File not found` | Debian 重打包删除了 `intl/`，但随包 `configure` 仍在 AC_OUTPUT 阶段链接 intl 头 | patch 0002：把 `nls_cv_header_intl/libgt` 别名置空，跳过该链接步骤 |
| E2 | `fatal error: 'libgettext.h' file not found`（`src/tua.h:86`） | 私有 gettext 头 `intl/libgettext.h` 已随 intl/ 删除 | patch 0005：改用公有 gettext API；无 NLS 时 `_()` 恒等 |
| E3 | `proclog.c:67:7: error: expected ')'`（`LOG` 宏展开） | clang 15 不再把 `__FUNCTION__` 当字符串字面量，无法用于字面量拼接 | patch 0005：`LOG()` 改用 `__func__` 作为 `%s` 实参 |
| E4 | `tua.c:615:14: error: use of undeclared identifier 'LC_ALL'` | `<locale.h>` 原先由内嵌 gettext 头间接带入，删除后不再可见 | patch 0004：显式 `#include <locale.h>` |
| E5 | `ld.lld: error: undefined symbol: gettext / bindtextdomain / textdomain` | OHOS SDK 链接期 libc.so 为 stub（无 gettext 符号），运行期 musl 才导出 | patch 0004/0005：以 `ENABLE_NLS` 守卫 gettext 调用，并以 `--disable-nls` 构建 |
| E6 | `Makefile:96: tua.dvi Error 127`（doc 子目录） | 文档目标需要 `texi2dvi`/`makeinfo`，工具链不具备；且 `doc/tua.1l` 已被重打包删除 | patch 0001：从 `SUBDIRS` 移除 `doc` |
| E7 | `make: ***No rule to make target 'getopt.o'`（隐含） | `getopt.c/getopt.h/alloca.c` 已被重打包删除，但仍在 `OBJECTS`/`SOURCES` | patch 0003：移除对应条目，改用 libc `getopt_long` |

## 源码修改（5 个补丁）

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-Makefile.in.patch | Makefile.in | `SUBDIRS` 移除 `doc`（文档工具缺失 + man 源已删） |
| 0002-configure.patch | configure | 中和已删除 `intl/` 的头文件别名（3 处 ×2 行） |
| 0003-src-Makefile.in.patch | src/Makefile.in | 移除 `getopt.o`/`getopt.c getopt.h alloca.c` |
| 0004-src-tua.c.patch | src/tua.c | 显式 `<locale.h>`；gettext 域设置以 `ENABLE_NLS` 守卫 |
| 0005-src-tua.h.patch | src/tua.h | 公有 gettext API + 无 NLS 时 `_()` 恒等；`LOG()` 用 `__func__` |

补丁由 `ohc-run.py refresh-patch --auto tua 4.3` 生成，并逐个通过
`patch -p1 --dry-run` 干净校验。全部为可移植性修复，**不含任何平台宏**。

## 上游测试（R51 三步法）
1. **清点**：全树无 `tests/`/`test/` 目录；无 `Makefile.am`（无 `TESTS` 声明）；
   无 ctest/meson/pytest 入口。唯一入口是顶层 `Makefile.in` 的
   `check: all` → `./tua`（无参数运行程序本身，无断言）。
2. **运行**：`make check` 退出码 2，输出
   `TUA (read_stats_log): cannot open /usr/local/spool/uucp/Stats` →
   `Error in processing stats`（因测试环境无真实 UUCP spool，非构建缺陷）。
3. **申报**：上游自动化用例数 = **0**，亦无上游样例数据。
   消费者侧验证由 `test_package/test_tua.sh` 提供（合成 spool + 实质运行）。
   详见 `reports/test-report.md` 与 `test_package/MANIFEST.yml`。

## 已知事项
- `make check` 依赖真实 Taylor UUCP spool（默认 `/usr/local/spool/uucp`），
  本适配以 `-p DIR` 指向合成 spool 做消费者测试。
- 运行期 `TUA.pcd`（费率配置）路径在 configure 时固化（`LIBDIR/TUA.pcd`）；
  缺失时程序仅打印告警并忽略费率分析，不影响报表。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → test_package: TOTAL=21 PASS=21 FAIL=0
file package/bin/tua
# → ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

---
**编译结束**: 2026-09-30
**最终状态**: built
---

**编译结束**: 2026-09-30 13:25
**最终状态**: built
