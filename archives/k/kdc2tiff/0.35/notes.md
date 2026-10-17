# kdc2tiff 0.35 适配笔记

## 软件简介

kdc2tiff 是 Chris Studholme 写的命令行图像转换器，最初用于把柯达 DC120 相机的
`.kdc` 原始图转成 TIFF 或 JPEG；0.35 版已能读 `.kdc`/`.tif`/`.jpg` 三种输入。
输出格式由 `argv[0]` 的程序名决定，因此上游同时安装 `kdc2tiff`（写 TIFF）与
`kdc2jpeg`（写 JPEG）两个入口名。

- 上游主页：<https://sourceforge.net/projects/kdc2tiff/>
- 官方源：<https://downloads.sourceforge.net/project/kdc2tiff/kdc2tiff/0.35/kdc2tiff-0.35.tar.gz>
- 许可证：GPL-2.0-or-later（COPYING）
- 构建系统：autotools（tarball 内已预生成，Autoconf 2.58 + automake 1.4-p4）

## 编译环境

- 构建主机：B 机（HarmonyOS PC，aarch64，`frp-bar.com:19214`）
- worktree：`~/qzy/主理-74-kdc2tiff-0.35`，分支 `feat/kdc2tiff-0.35`
- CONAN_HOME：`~/tmp/ch/home-kdc2tiff`（profiles 目录为空 ⇒ 所有命令显式带双 profile）
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / armv8 / clang 15.0.4 / libc++ / cppstd=17 / Release）
- conan：2.29.1

## W0 依赖实证（R35：只用 `conan install --build=never` 判 binary，不用通配 `conan list`）

`configure.in` 的依赖声明（逐字读解包件）：

```
AC_CHECK_LIB(m,main,,AC_MSG_ERROR([a math library is required]))
AC_CHECK_LIB(tiff,main,,AC_MSG_ERROR([libtiff is required]))
AC_CHECK_LIB(jpeg,main,,AC_MSG_ERROR([jpeglib is required]))
```

⇒ 需要 libtiff 一族 + libjpeg 一族 + libm。上游对两者**都没有版本下限**
（无 `AM_PATH_LIBTIFF`、无 `aclocal/` 版本宏），故按"已发布 + 与 libtiff 自带
的 jpeg  provider 一致"选型，不猜版本号。

| 候选 | `conan install --requires=<pkg> --build=never`（双 profile） | 结论 |
|---|---|---|
| `zlib/1.3.1`（对照样本） | RC=0，`Install finished successfully` | 通道正常，对照组成立 |
| `libtiff/4.7.2` | **RC=0** | 已发布，选它 |
| `libtiff/4.7.0` | RC=0 | 已发布（备选，不选：取最新可用） |
| `libtiff/4.6.0` | RC=1 `Unable to find 'libtiff/4.6.0' in remotes` | 未发布 |
| `libjpeg-turbo/3.2.0` | **RC=0** | 已发布；且正是 libtiff/4.7.2 自己 requires 的那一枚 ⇒ 依赖图里只有一份 libjpeg.so |
| `libjpeg-turbo/3.1.4.1` | RC=1 `Unable to find ... in remotes` | 未发布 |
| `libjpeg-turbo/3.0.4` | RC=0 | 已发布（不选：与 libtiff 的 jpeg provider 不同版会双份 libjpeg.so） |
| `libjpeg/10` | RC=0 | 已发布（不选：同上，会与 libtiff 传递来的 libjpeg-turbo 同名撞车） |

`libtiff/4.7.2` 自身 requires：`zlib/1.3.1.1`、`libdeflate/1.25`、
`libjpeg-turbo/3.2.0`、`zstd/1.5.7`、`libwebp/1.6.0`、`lerc/4.1.1`、
`jbigkit/2.1`、`xz/5.6.2` —— 这些随 `libtiff/4.7.2 --build=never` 一次性解析
且 RC=0，即全链 binary 均可下载，无需本机现编（R36）。
`libm` 由 libtiff 的 `cpp_info.system_libs = ["m"]` 在 Linux/OHOS 下提供。

`bash ci/scripts/preflight_check.sh kdc2tiff/0.35` 首跑 RC=0（此时尚无 conanfile，
脚本按"无依赖需检查"放行）；配方成型后复跑见下方验证结果。

## 上游测试清点（R51 第一步）

- tarball 文件全集里没有 `tests/`、没有任何 `test-*` 源文件。
- 实测（本窗对干净解包件 `.build-cache/predl_cache/b50a9796_kdc2tiff-0.35.tar.gz` 复算）：
  `grep -n "^check\|^test\|TESTS" Makefile.am Makefile.in` **只命中 2 行** ——
  `Makefile.in:354:check-am: all-am`、`Makefile.in:355:check: check-am`；`Makefile.am` 侧
  **0 命中**。这两行是 automake-1.4-p4 生成的**空壳目标**：只有依赖声明、后面没有任何
  recipe 命令（紧邻的 `Makefile.in:356:installcheck-am:` / `:357:installcheck: installcheck-am`
  同样为空），并且全包无 `TESTS` 变量 ⇒ **空壳 `check` 目标存在，但不注册任何用例**。
  （整改前此处写作"无 `check`/`test` 目标"，与上面的 grep 读数不符 —— W4 审计 W4-04
  点名"引文不实"，现按实测更正；结论「上游成体系测试为 0」不变。）
- `configure` 无测试相关开关（实测 `grep -c "AC_CHECK_PROG.*ctest\|enable-test" configure` = 0）。
- `README`/`INSTALL`/`ChangeLog` 只讲 `./configure && make && make install`。

⇒ **上游成体系测试为 0**。功能面由 `test_package/test.sh` 以消费者视角补齐
（真跑安装后的二进制，断言 **29/29**，判决原文 `reports/w3-local-ci.log:462`，
声明见 `test_package/MANIFEST.yml` 的 `assertion_count`）。

## 适配过程与关键判断

### 1）源码获取

只取 SourceForge 官方发布址（实测 3/3 次 HTTP 200、94618 B、
sha256 `bde9e3ed41bf09ded586e0ac87c2fe6e48780e4e98f9927a31d1c19e192f51ec`）。
Debian 池件 `kdc2tiff_0.35.orig.tar.gz` 的 sha256 与之**同值**（同一文件），
但 PF7 拉黑 Debian 重打包形态 ⇒ 池址不进配方，只作交叉验证。
真文件名是 `kdc2tiff-0.35.tar.gz`；按 Debian 命名去猜 SourceForge 址会 404。

### 2）配方骨架

`ohc-run.py recipe-search kdc2tiff` 报"无相似配方（语料 6173 条）"⇒ 按仓内
`templates/conanfile-autotools.py.tmpl` 范式自写，形状参照同平台已归档的
Autotools 单二进制 CLI 配方 `archives/a/aaphoto/0.45/`
（`basic_layout` + `AutotoolsDeps` + `AutotoolsToolchain` + `-j1` +
`package_type=application` + 依赖 libdir 进 `LD_LIBRARY_PATH`）。
按流程要求**未跑** `ohc-run.py build`（其 Step1 会去搜索引擎取源并写坏 conandata），
直接用 `conan create` 迭代。

### 3）三处 OHOS 侧障碍（都有当场复现证据，不是推断）

| # | 障碍 | 取证方式与读数 | 处方 |
|---|---|---|---|
| 1 | `config.status` 建临时目录用 `umask 077 && mktemp -d` ⇒ 目录落成 `drwx--S---`，**属主也写不进去** | 在 conan 缓存同类目录下实跑该构造：`MKTEMP_RC=0` 但 `touch $tmp/subs1.awk` 报 `Permission denied`（`TOUCH_RC=1`）；同一位置去掉 umask 后 `TOUCH_RC=0` | `patches/0001-configure-umask-077.patch`（E114 家族，先例 `archives/a/aaphoto/0.45/patches/0003-configure.patch`） |
| 2 | 上游把 `kdc2jpeg` 写成 `kdc2tiff` 的派生目标、用 `ln -f kdc2tiff kdc2jpeg`（硬链接）造第二个入口名（实测 `Makefile.am:20-21`、`Makefile.in:431-432`，全包 `ln -f` 恰此 2 处） | 同盘实跑 `ln -f ha hb` ⇒ `ln: cannot create hard link from 'ha' to 'hb': Operation not permitted`，`LN_RC=1` | `patches/0002-Makefile-ln-f-to-cp-f.patch`（改 `cp -f`；**E050**，`knowledge/doc/E050.md` —— 本包 B 判定 hit 的命中条目，逐字引用与 hit 四条件见下节 3.1） |
| 3 | 2004 年代码 `main (int argc, char*argv[])` 无返回类型 | 用配方同款编译器 `clang++ 15.0.4 (aarch64-unknown-linux-ohos)` 单文件 `-fsyntax-only` 实跑 ⇒ `error: a type specifier is required for all declarations`（`-std=gnu++17` 与 `-std=gnu++98` 同样报错） | `patches/0003-kdc2tiff.cpp-int-main.patch` 补 `int`（clang 兼容性问题，**不对应任何 HMDFS 知识条目**；与 E007 无关，见下节 4）） |

### 3.1）核心机制的知识条目归属：**E050**（本包 B 判定 = hit）

整改前整棵交付树 **0 处引用 E050**（W4 审计 W4-03：`.handoff.json` 写 `knowledge_hit: none`、
verify 报告 G0 只提 E490），本节补齐 —— 本包命中的是基线既有条目
**`knowledge/doc/E050.md`**（标题 `# E050: copy-replace-symlink`，类别
`hmdfs, linking, runtime, filesystem`，严重度 3）。

- **E050 推荐方案逐字引用**（`knowledge/doc/E050.md:21-25`）：

  ```
  **方法**: copy-replace-symlink

  **说明**: 用文件副本(cp)替代符号链接(ln):
                           rm libpython3.9.so && cp libpython3.9.so.1.0 libpython3.9.so
                           对于 make install, 将 $(LN_FORCE) 改为 $(HARDLINK)(鸿蒙上为 cp -p)
  ```

  其中被沿用的处方句是：**「对于 make install, 将 $(LN_FORCE) 改为 $(HARDLINK)(鸿蒙上为 cp -p)」**
  —— 即"鸿蒙上不给你 link，就换成 copy"。根因段（`E050.md:16-18`）：HMDFS 不正常跟踪符号链接。
- **本包落点**：上游没有 `$(LN_FORCE)` 变量，而是在 Makefile 里把 `kdc2jpeg` 写成
  `kdc2tiff` 的派生目标、recipe 为字面量 `ln -f kdc2tiff kdc2jpeg`
  （`Makefile.am:21`、`Makefile.in:432` 各 1 处）⇒ 0002 把这两处同改成 `cp -f`，
  是 E050 "用 cp 替代 link" 处方的逐字落地（本包由 `make` 在为 install 准备第二个
  入口名时执行该语句，与 E050 措辞的 "make install" 同一触发面）。
- **机制的另一半是 mtime 顺序**：0002 内 **Makefile.am 的 hunk 在前（`@@ -18,4 +18,4 @@`）、
  Makefile.in 的 hunk 在后（`@@ -429,7 +429,7 @@`）**，打完补丁保持"生成件比输入新"，
  否则 automake-1.4-p4 的 maintainer 规则会去调 worker 上不存在的 automake/autoconf/autoheader
  （配方里的 `_order_autotools_mtimes()` 也是为这件事）。
- **hit 四条件逐条**：

  | 条件 | 判定 | 依据 |
  |---|---|---|
  | 同机制 | ✅ HMDFS 不允许用 link（本包是硬链接，E050 记录的是符号链接不被跟踪）作为"造第二个名字"的安装/构建手段 | 本窗复算 `ln -f ha hb` ⇒ `Operation not permitted`（上表第 2 行）；`E050.md:16-18` |
  | 同触发 | ✅ 同为 Makefile 里"用 link 生成第二个名字"的语句（E050 措辞 "对于 make install"） | `Makefile.am:20-21`、`Makefile.in:431-432` |
  | 同处方 | ✅ link → 文件副本（E050：`$(LN_FORCE)`→`$(HARDLINK)`，鸿蒙上为 `cp -p`；本包：字面量 `ln -f`→`cp -f`） | 0002 两枚 hunk（见上） |
  | 判据可复用 | ✅ 判据 = 包内第二个入口名必须**真实存在、非空、与被"复制"源同 sha256 而 inode 不同** | 本窗在 B 机 `~/tmp/ch/home-kdc2tiff/p/b/kdc2t7d855c4175185/p/bin` 实测（未重跑构建）：恰 `kdc2tiff` + `kdc2jpeg` 两枚、各 109184 B、sha256 同为 `0ffecdb134d353ebfc0116926141a3560c5846c364bcc1075027a2d70cee1ba6`、inode 分别 `2305843009234687777` / `2305843009234688389` ⇒ 非硬链接别名，`cp` 语义成立 |

- **同族最近邻只作差异化对照（不混引）**：`E331`（OHOS HMDFS 构建 CMake 版本化共享库时
  避免符号链接链）、`E382`（HMDFS 保不住悬空链接时把跨包不可变资源实体化）、
  `E446`（文件系统测试保持激活同时豁免 OHOS 不支持的建链路径）——三者分别落在
  "版本化 `.so` 链接""打包资源实体化""测试豁免"面上，与本包"可执行文件第二入口名的
  Makefile 建链"处方落点不同 ⇒ 本包 hit **只挂 E050**。

### 4）E007（老 config.guess 不认 HarmonyOS）**不适用**

任务预报的头号风险是 E007。逐项核实后判定本包不命中，依据四条（第 4 条为 W4 整改补证）：

1. tarball 文件全集**不含** `config.guess` 与 `config.sub`（`find` 结果为空）；
2. `configure`（Autoconf 2.58）里 `config.guess` 只出现在第 1293 行的
   `ac_config_guess="$SHELL $ac_aux_dir/config.guess"` 赋值，全文再无第二处 ⇒
   从未被调用（本包没用到 `AC_CANONICAL_HOST`）；
3. `configure` 既不识别也不调用 `config.sub`，同 `-Iinclude` 一样只走过场。
4. （W4 整改补证）`reports/w3-local-ci.log:204` 的 `RUN: ".../configure"` 实参只有
   `--prefix=/` 与 `--bindir/--sbindir/--libdir/--includedir/--oldincludedir`，
   **没有** `--build/--host`；`grep -c "ac_cv" reports/w3-local-ci.log` = **0**
   ⇒ 也没有用 `ac_cv_*` 预置缓存绕过 `AC_RUN_IFELSE`（日志第 229 行
   `checking for main in -ltiff... yes` 是真探测，不是缓存喂出来的）。

⇒ `perl scripts/patch-autotools-ohos.pl ...` 无对象可打；也**没有**用
`--build/--host` 去绕（E007 第 21 行明令禁止）。

**归因更正（W4 整改）**：主窗此前把 0001/0003 两枚补丁的出处写成 **E007**。经复核该口径
**不成立** —— 本包 tarball 里没有 `config.guess`/`config.sub`（上列依据 1），E007 在本包
**0 处方落地**。实际归因：**0001 = E114**（`knowledge/doc/E114.md:1` `bypass-mktemp`；
实测解包件 `grep -c "umask 077" configure` = **2**，恰对应 0001 单 hunk
`@@ -4355,12 +4355,12 @@` 里去掉的 2 处）、**0003 = clang 需补 `int main`**
（`kdc2tiff.cpp:308`，编译器兼容问题，无 HMDFS 条目号）、**0002 = E050**（见 3.1）。
交付件（软件级/版本级 manifest、补丁表）凡按 E007 表述之处已同步改成本段的实际条目。

### 5）VPATH 构建可用性

`conan` 的 `basic_layout` 会做树外构建。核过上游生成件确实支持：
`Makefile.in` 有 `VPATH = @srcdir@`、`DESTDIR =`（install 规则全部带
`$(DESTDIR)`），`DEFS = @DEFS@ -I. -I$(srcdir) -I.`，`install-sh`/`missing`/
`mkinstalldirs` 都在包内。`conan 2.29` 的 `Autotools.install()` 文档明确
默认注入 `DESTDIR=<package_folder>`，`AutotoolsToolchain` 的 `--prefix` 默认 `/` ⇒
产物落 `<package_folder>/bin/`。

### 6）`-Iinclude` 与自带 libtiff 私有头不冲突

包内 `include/` 放着 3.x 时代的 `tiffconf.h`/`tif_dir.h`/`tiffiop.h`/`port.h`，
而 `Makefile.am` 有 `INCLUDES = -Iinclude`。核过 libtiff 4.7.2 的
`tiffio.h` 只引 `"tiff.h"`/`"tiffvers.h"`，`tiff.h` 引 `"tiffconf.h"` 属**同目录
引号包含** ⇒ 先命中 libtiff 自己那份，不会被 `-Iinclude` 抢走；
需要私有头的 `xtif_dir.c` 只在 `EXTRA_kdc2tiff_SOURCES` 里、不参与编译。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| libtiff | 4.7.2 | ohpcd 制品仓 | `-ltiff`，`tiffio.h` |
| libjpeg-turbo | 3.2.0 | ohpcd 制品仓 | `-ljpeg`，`jpeglib.h`；与 libtiff 自带的 jpeg provider 同版 |
| zlib / libdeflate / zstd / libwebp / lerc / jbigkit / xz | 见 libtiff/4.7.2 的 requires | ohpcd 制品仓 | 经 libtiff 传递引入，`--build=never` 一次解析通过 |
| libm | — | 系统 | 由 libtiff 的 `cpp_info.system_libs` 在 Linux/OHOS 提供 |

## 源码修改（补丁）

| 补丁 | 改动 | 类型 | 知识归因（本窗复算，纠正此前 E007 误标） |
|---|---|---|---|
| `patches/0001-configure-umask-077.patch` | `configure` 内 config.status 的两处 `umask 077 &&` 去掉 | platform | **E114**（`knowledge/doc/E114.md:1` `bypass-mktemp`）：解包件 `grep -c "umask 077" configure` 实测 = **2**，恰为此补丁单 hunk `@@ -4355,12 +4355,12 @@` 覆盖的 2 处 |
| `patches/0002-Makefile-ln-f-to-cp-f.patch` | `Makefile.am:21` + `Makefile.in:432` 的 `ln -f kdc2tiff kdc2jpeg` → `cp -f` | platform | **E050**（`knowledge/doc/E050.md`，本包 B 判定 hit 的命中条目；逐字引用与 hit 四条件见 3.1 节） |
| `patches/0003-kdc2tiff.cpp-int-main.patch` | `kdc2tiff.cpp:308` 的 `main (...)` → `int main (...)` | portability | **无条目号**：clang 15 不接受无返回类型 `main`（编译器兼容性）；**不是 E007** —— E007 只管 `config.guess`/`config.sub`，本包 tarball 里没有这两件文件 |

补丁一律 `diff -u` 形态、`a/`+`b/` 前缀、无时间戳头；用干净副本做
`patch -p1 --dry-run` + 真打 + `cmp` 的 round-trip，逐字节等于期望内容。
三处改动都只服务 HarmonyOS PC 的构建/运行环境，不带平台宏
（PF5/R8），也不注入 `/usr/local` 之类共享前缀（PF6/R49）。

## 验证结果

- 编译状态：成功
- 测试状态：test_package 端到端断言全部通过 —— 判决原文逐字为
  `SUMMARY kdc2tiff consumer: total=29 passed=29 failed=0`（出处
  `reports/w3-local-ci.log:462`，是 w3 日志全文**唯一**一条 SUMMARY；同次日志里 `[PASS]` 实测
  29 行、`[FAIL]` 0 行）。另一份独立判决 `reports/conan-create.log:173`（conan-verify 的 G2
  自己再跑的一轮 `conan create` + test_package）同为 `total=29 passed=29 failed=0`，两日志互证。
  **断言数同源复算（声明数 == 日志 SUMMARY == 静态计数，三者一致）**：`test_package/test.sh` 静态
  `^chk ` 调用点 **21** 处（L34、36、166、169、171、173、175、182、184、186、190、197、
  202、206、210、214、216、221、226、228、232）+ 内联 `if …; then ok/bad` 判定点 **8** 处
  （L180、187、195、198、203、211、222、233）= **29**；脚本内**无循环展开**，
  21 + 8 即全部（L24 的 `chk() { …; then ok "$2"; …}` 是函数定义、不计为站点）。
  ⇒ `test_package/MANIFEST.yml` 的 `assertion_count` 同写 **29**（整改前此处与 MANIFEST
  都写 24，既不等于日志实测 29、也不等于静态 21，W4 审计 W4-01 点名后已四处改齐）。
  上游成体系测试清点为 0（见上文「上游测试清点」）。
- 运行状态：`kdc2tiff`/`kdc2jpeg` 均为 AArch64 ELF，DT_NEEDED 含 libtiff 与 libjpeg；对合成 4x4 RGB TIFF 完成 TIFF→TIFF 与 TIFF→JPEG 两次真实转换，产物从格式侧解析通过，并能读回自产 TIFF（往返）

命令与判决原文见下方「编译结束」块与 `reports/`。

## 注意事项

- `conan-verify` 的 G2 会自己再跑一次 `conan create`（缓存里没有
  `kdc2tiff/0.35@ohpcd/stable_<hash>` 时日志不会出现 `- Cache`，属正常，不是假绿）。
- **★本包是两档（two-rrev），不是一档**（W4 审计 W4-05；此前"未见镜像注入、可能单档"的
  预报与日志事实相反，现按实测分档披露）：

  | 档 | rrev | 形成方式与出处 | PKGID | 本地整编证据 |
  |---|---|---|---|---|
  | W3 绿跑档（注入档） | `4890466954cbc948e72e295ee3e5d8b5` | harness 的 Pre-download 把 `conandata.yml` 的 url 临时改成 `file://…/.build-cache/predl_cache/b50a9796_kdc2tiff-0.35.tar.gz` 后导出：`reports/w3-local-ci.log:96-100`（注入）、`:111`（Exported）、`:186`（file:// 取源）、`:373`（Full package reference）、`:493`（已还原为官方 URL） | `cc91ff87ca05a40e640fad0984a2654e990285c6`（同 `:373`） | **有**：`conan create` 全程 + test_package 29/29 |
  | 交付态档（官方 URL 档） | `c2cb7785e3654e9a2ae534d2cf1eb8cb` | 提交里 `conandata.yml` 只剩官方 https 址；W4 审计与**本窗各跑一次 `conan export` 复算，同值** | — | **无**：交付档从未在本地整轮 `conan create` 过，本地只有 `conan export` 级证据 |

  - 两档**只差 `conandata.yml` 的 url 串**（conan 的 rrev 随 url 变），tarball 是同一枚：
    sha256 `bde9e3ed41bf09ded586e0ac87c2fe6e48780e4e98f9927a31d1c19e192f51ec`、94618 B。
    官方址活性由 W4 审计独立 `curl` 复现（HTTP 200 / 94618 B / 同 sha256）。
  - 本窗另测得：**改 notes/manifest/MANIFEST 这类文本不翻 rrev**（副本加一行后
    `conan export` 仍是 `c2cb7785…`）⇒ rrev 只随 `conanfile.py`/`conandata.yml` 变，
    本轮整改不碰这两件。
  - **口径纪律**：不得写"CI 会首次真跑官方址"这类断言（本仓的 Pre-download 注入已把该说法
    证伪过一次）；交付档的真编要等 CI 侧独立证据，或按审计建议另跑一次"直读官方 URL 的
    `conan create`"并比对 PKGID 是否仍为 `cc91ff87…`。
- `conan-verify` 的 **G4 与 L2/L4/L5 实际是 skip，不是通过**：`G4` 正文
  `⚠️ 无法找到程序包 ID`、`L2/L4/L5` 正文全为 `⏭️ 跳过（无 cache 路径）`
  （`reports/conan-verify-report.md:39-49`）⇒ conan-verify 真做过的只有 **G0/G1/G2/G3**。
  **判据（复核时务必照此读）**：该报告的 `## Gx:`/`## Lx:` **节标题恒为 `✅ PASS`**（harness
  固定文案），**真判决在标题的下一行**——只看标题会把 4 条 skip 读成"通过"（W4 审计 W4-02
  就是抓这件事）。运行面证据因此由别处承接：test_package 的 29 条断言（两份日志互证，见
  「验证结果」）+ 本窗对 `pkg/bin` 的实测（两枚 109184 B、同 sha256 `0ffecdb1…`、inode 不同）。
  另 G0 节内带未披露告警 `⚠️ 已知风险 E490 未在配方中处理` ＋ `⚡ G2 conan create 可能因此
  失败，建议先修复`（`conan-verify-report.md:11`/`:15`）：E490 指的是 autotools 辅助脚本的
  可执行位；本次 G2 的 `conan create` 实际成功（`report:32`，且 `configure` 在
  `w3-local-ci.log:204` 被真实 `RUN`），该风险在本环境未成立 ⇒ 配方未为此改 `chmod`。
- test_package 的临时目录落 `$HOME/tmp`（OHOS `/tmp` 只读，E002）；
  脚本由 `CONFIG_SHELL`（`/data/service/hnp/bin/bash`）调起，不用 mksh 跑 ELF。
- `Makefile.in` 由 automake-1.4-p4 预生成，worker 上没有 automake/autoconf/autoheader
  ⇒ 打完补丁后 mtime 顺序需保持"生成件比输入新"，0002 里 Makefile.am 在前、
  Makefile.in 在后就是为这件事。
---

**编译结束**: 2026-09-27 06:23
**最终状态**: built
