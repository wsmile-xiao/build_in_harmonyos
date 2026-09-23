# libgda5 5.2.10 适配笔记（HarmonyOS PC / aarch64-ohos）

- 上游：https://gitlab.gnome.org/GNOME/libgda ，tag `LIBGDA_5_2_10`
  （tag 对象 `51ce16db…`，peeled commit `85a2532df64698306fd3be324bb2052fb1b80fd3`）
- 源码：`https://ftp.gnome.org/pub/GNOME/sources/libgda/5.2/libgda-5.2.10.tar.xz`
  sha256 `6f6cdf7b8053f553b907e0c88a6064eb48cf2751852eb24323dcf027792334c8`
  （`download.gnome.org` 在本机 TLS 握手失败 exit 35，改用 GNOME 官方镜像 ftp.gnome.org）
- 构建系统：autotools（tarball 内已含预生成 `configure` / `Makefile.in`）
- 编译器/工具链：OHOS clang 15（`/data/service/hnp/bin/clang`），profile `ohos-aarch64`
- 阶段边界：仅新增 `archives/l/libgda5/**`，未改动任何依赖包或框架文件；未 push/PR

## 1. 依赖结论（与依赖分析阶段的差异）

| 依赖 | 采用 | 说明 |
|---|---|---|
| glib | **glib/2.88.3（shared）** | 必须 shared：制品仓 glib2/2.88.0 仅静态，静态 glib 会被 libgda 的 `-export-symbols-regex` 隐藏后内嵌进 libgda-5.0.so，消费者进程出现两套 GObject 类型系统 → 上游测试大面积崩溃（实测 6 PASS → 换 shared 后 27 PASS） |
| libxml2 | 2.15.3 | 与 libxslt/1.1.45.2 的 pin 对齐（取 2.15.3.1 会触发 conan 版本冲突） |
| libxslt | 1.1.45.2 | libgda-xslt / libgda-report |
| iso-codes | 4.20.1 | 可选数据（ISO 4217） |
| **sqlite3** | **不使用（内嵌）** | `--disable-system-sqlite`：libgda 5.x 的 SQLite provider 在**运行期** `g_module_open("libsqlite3.so")`（`libgda/sqlite/gda-symbols-util.c:110`、`gda-sqlite-provider.c:635`），而制品仓的 sqlite3 包只提供静态 `libsqlite3.a`（无 shared 变体，`-o sqlite3/*:shared=True` 解析到同一个 package-id） → provider 无法实例化（`Can't find libsqlite3.so file.` → `Could not create provider for 'SQLite'`），所有需要数据库连接的测试失败。内嵌模式定义 `STATIC_SQLITE`，provider 直接注册 GType |
| mysql-client | 不使用 | 与 glib 存在 conan 版本硬冲突（mysql-client/9.7.1 → zlib/1.3.1，glib/2.88.3 → zlib/1.3.2）；且 provider 探测需 `-lssl/-lcrypto`（mysql-client 只给裸 `-lssl`）与 C++ 运行库。上游测试中 MySQL 相关用例需要真实服务端，本环境无法执行 |
| postgresql | 不使用 | 探测入口是 `pg_config`，libpq 包不提供（见依赖分析报告接线项） |

## 2. 逐项修复记录（首个错误 → 根因 → 修复 → 复验）

| # | 首个错误（原始输出） | 根因 | 修复（配方内，未打源码补丁） | 复验 |
|---|---|---|---|---|
| 1 | `ERROR: Version conflict: Conflict between libxml2/2.15.3 and libxml2/2.15.3.1` | libxslt/1.1.45.2 pin 2.15.3 | `requires("libxml2/2.15.3")` | conan install exit 0 |
| 2 | `Conflict between zlib/1.3.1 and zlib/1.3.2` | mysql-client pin zlib 1.3.1 vs glib 1.3.2 | 换 glib/2.88.3（shared）+ 去掉 mysql-client | exit 0 |
| 3 | `configure: error: GNU gettext tools not found; required for intltool`（`checking for msgmerge... no`） | OHOS SDK 把 gettext 拆成两目录：`/data/service/hnp/bin` 无 `msgmerge`，在 `gettext.org/<ver>/bin` | generate() 里 `PATH` 前置 `glob("/data/service/hnp/gettext.org/*/bin")` | configure 越过该检查 |
| 4 | `configure: error: XML::Parser perl module is required for intltool` | OHOS perl 无 XML::Parser（XS 也无法在 HMDFS 加载） | 注入最小 `XML::Parser` stub（PERL5LIB） | 通过 |
| 5 | `config.guess: unable to guess system type … UNAME_SYSTEM = HarmonyOS` | tarball 内 config.guess 为 2018 版，不认 HarmonyOS | configure 显式 `--build=aarch64-linux --host=aarch64-linux`（同 goffice 做法） | 通过 |
| 6 | `configure: error: itstool not found` | gtk-doc/yelp 的 `YELP_HELP_INIT` 检查无条件执行 | 生成 `itstool` stub（`--disable-gtk-doc` 下 yelp 规则被门控，不会真正调用） | 通过 |
| 7 | `./config.status: line 957: ./confXXX/subs1.awk: Permission denied`（E114） | HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX` 产生的目录不可写 | 在 patch 中移除 `umask 077`（与仓库既有 aaphoto/libqalculate 同款 E114 处理；`configure` 单文件补丁，无平台宏） | `config.status` 正常 |
| 8 | `make[2]: *** [Makefile:993: s-enum-types-c] Error 126` → `glib-mkenums: /usr/bin/perl: bad interpreter` | OHOS 自带 glib-mkenums(2.38.2) shebang 指向不存在的 `/usr/bin/perl`；libgda 的 Makefile.am 以裸命令调用 `glib-mkenums`（无变量可覆盖） | build() 内把 conan glib 包的 `bin` 前置到 PATH（python3 版 glib-mkenums） | 枚举文件生成成功 |
| 9 | `error: call to undeclared function 'ngettext'`（gda-data-model.c:2982） | glib 的 gi18n-lib.h 只 include `<libintl.h>`，而 OHOS sysroot 的 libintl.h 无 `ngettext` | glib 静态包带 proxy libintl.h → 直接用；**glib 共享包不带** → 注入 `libintl.h` shim（gettext 家族映射到 glib 的 `g_dgettext/g_dngettext`，`bindtextdomain` 等做无害映射） | 编译通过 |
| 10 | `libtool: error: cannot find the library '//lib/libpcre2-8.la'` | pcre2 包的 `.la` 内 `libdir='//lib'`（打包时 prefix=/ 硬化），`libpcre2-posix.la` 的 `dependency_libs` 也引用它 | generate() 把 pcre2 静态库/.la 复制到 build 私有目录、改写 libdir/dependency_libs，并把生成的 `pcre2.pc` 指过去 | 链接通过 |
| 11 | `make: *** No rule to make target 'Gda-5.0.typelib'` | upstream 缺陷：`configure.ac:494` 用未加引号的 `test x$found_introspection != xyes`，`--disable-introspection` 会让变量取带空格字符串 → `disable_gda_gi` 未置位 → `ENABLE_GDA_GI` 恒真但 `INTROSPECTION_MAKEFILE` 为空 | 不传 `--disable-introspection`，保持默认 `auto`（OHOS 无 `gobject-introspection-1.0.pc` → 得到无空格的 `no`） | 配置摘要 `Introspection: no` |
| 12 | `providers/*/specs/*.xml` 生成失败：`Can't locate object method "new" via package "XML::Parser"`（intltool-merge -x） | XML 模式 intltool-merge 必须 XML::Parser | 自写 `intltool-merge` shim（仅剥离 `_name=`/`_descr=` 翻译标记，等价于无翻译结果），并用 `INTLTOOL_MERGE=` 显式交给 configure | xml 生成成功 |
| 13 | `configure: error: cannot run C compiled programs`（conftest 127） | `AutotoolsDeps` 把依赖 `-l` 全塞进 LIBS/LDFLAGS，早期 conftest 也链上 glib.so，运行期找不到 conan 包路径 | 不使用 `AutotoolsDeps`（链接标志全部来自 pkg-config 的 `.pc`） | configure 通过 |
| 14 | `libtool: error: cannot find the library '//lib/libpcre2-8.la'`（残留，链接 `test-rt-parser`） | 之前一次链接生成的子目录 `.la` 缓存了坏路径 | clean 重建 | 全量 make exit 0 |
| 15 | 上游测试大面积 `Signal 11/6`、`signal 'changed' is invalid … type '()'` | 静态 glib 被内嵌进 libgda-5.0.so（符号被版本脚本隐藏），测试进程另有自己的 glib → 两套 GObject 类型系统 | 改用 **glib/2.88.3 shared**，并 clean 重建 | 通过项 6 → 27 |
| 16 | 需要数据库连接的用例全部 `Can't find libsqlite3.so file.` / `Could not create provider for 'SQLite'` | SQLite provider 运行期 dlopen `libsqlite3.so`，sqlite3 包只有静态库 | `--disable-system-sqlite`（内嵌 sqlite，`STATIC_SQLITE`） | 通过项 27 → 35 |

## 3. 上游测试执行（实际运行，非 test_package 替代）

- 上游 `make check` 测试树：`tests/`（顶层 9 + data-models 9 + meta-store 4 + multi-threading 5 + parser 6 + providers 2 + value-holders 3 = **38**）
- automake 的并行测试 harness 在本平台不可用（libtool wrapper 报
  `getcwd: cannot access parent directories` → `providers/.libs/check_xxx: No such file`），
  因此改为**直接执行同一批测试二进制**（构建命令 `make -C tests -k check` 先生成它们）：

```bash
# 环境（见 libgda5-5.2.10-logs/run_upstream_tests.sh）
. installG2/conanbuild.sh ; . installG2/conanrun.sh
export LD_LIBRARY_PATH=$PWD/src2/_install/lib:$LD_LIBRARY_PATH
export SQLITE_DBCREATE_PARAMS="DB_DIR=<srcdir>/tests/providers"
export SQLITE_CNC_PARAMS="DB_DIR=<srcdir>/tests/providers;DB_NAME=testcheckdb"
export GDA_TOP_SRC_DIR=<srcdir> GDA_TOP_BUILD_DIR=<srcdir>
cd tests/<dir> && ./<test>
```

结果（`libgda5-build/upstream-test-logs/SUMMARY.txt`，逐用例日志同目录）：

- **总计 38：通过 35、跳过 2、未构建 1、失败 0**
- 跳过：`meta-store/check_meta_store_postgresql`、`meta-store/check_meta_store_mysql`
  （需要真实 PostgreSQL/MySQL 服务端，日志中为 `… test not run, please set POSTGRESQL_META_CNC …`）
- 未构建：`providers/check_mysql`（本配方未启用 MySQL provider）
- 关键用例：`providers/check_sqlite`（建库→元数据→游标→查询→清理）**PASS**

> 说明：`make check` 顶层还会在 `po/` 里跑 intltool 的**维护者检查**
> （`intltool-update -m`，要求 POTFILES 完整、需要 XML::Parser），该检查在 OHOS 不可用；
> 它是发布前的 l10n 一致性检查，不是测试用例，故不计入测试统计。

## 4. 与既有归档的差异

- 仓库既有 `archives/l/libgda/6.0.0` 是 **libgda6（meson）**，与本次 `libgda5`（autotools）
  是不同大版本，互不覆盖；本归档单独使用 `libgda5` 名字以免与 6.x 混淆。

## 5. 未做/待办

- MySQL / PostgreSQL provider（需要：mysql-client 与 glib 的 zlib 冲突解决或 sqlite3 提供 shared 变体；
  postgres 需 `pg_config`）——两者对应的上游测试也需要真实服务端。
- Vala 绑定（`--enable-vala`）与 GObject Introspection（`--enable-introspection`）默认关闭：
  前者需要 OHOS 可用的 valac/vapigen，后者需要可运行的 g-ir-scanner 且 upstream 5.x 的
  `configure.ac:494` 存在引号缺陷（见 §2 #11）。
- `tools/cmdtool`（gda-sql）：`AC_CHECK_LIB(ncurses)` 需要 `libncurses.so`，而 ncurses 包只提供
  静态 `libncursesw.a`（R4 策略）→ 探测失败后上游静默不构建，已用 `--disable-tools` 显式声明。

## 6. conan create 流水线（本机实测 `conan create` exit 0）

`conan create` 从零复现（下载源码 → 打补丁 → configure → make → install → package →
test_package），最后一次（日志 `83/84-conan-create-*.log`）**exit 0**，test_package 全部通过：

```
  ok   : SQLite provider 已注册（gda_config_get_provider_info）
  ok   : 打开 SQLite 文件库连接（DB_DIR=.;DB_NAME=libgda5_l1_test）
  ok   : CREATE TABLE t / INSERT 2 行 / SELECT 返回 2 行 2 列 / 值校验
test_libgda: ALL PASS
  ok   : provider 插件 dlopen(RTLD_NOW) 加载成功 + 导出 provider GType 符号
  ok   : 中文/emoji UTF-8 文本 round-trip 字节一致
  ok   : HMDFS 文件型数据库落盘 + 重开后数据仍在
test_ohos: ALL PASS (HarmonyOS 专项)
```

过程中修掉的问题（承接 §2 编号）：

| # | 首个错误 | 根因 | 修复 |
|---|---|---|---|
| 17 | `error: call to undeclared function 'ngettext'`（create 流程复现） | `tc.extra_cflags` 在 `tc.environment()` **之后**追加：`environment()` 会把当时的 cflags 快照进 env，之后的修改不生效 | 把 `-I<libintl shim>` 的 append 移到 `tc.environment()` 之前 |
| 18 | `package_info(): requires ... 'sqlite3::' is not a direct requirement` | 去掉 sqlite3 依赖后 package_info 未同步 | 移除 `sqlite3::sqlite3` |
| 19 | `package_info(): direct dependency 'iso-codes' is not used by any requires` | conan 一致性检查 | 显式加入 `iso-codes::iso-codes` |
| 20 | test_package：`'glib-object.h' file not found`（CMakeDeps） | CMakeDeps 未把 glib 组件 include 传递给消费者 | test_package 改用 `PkgConfigDeps` + CMake `pkg_check_modules(libgda-5.0)`（PkgConfigDeps 依据 cpp_info 生成含传递依赖的 .pc） |
| 21 | test_package：`'sql-parser/gda-statement-struct.h' file not found` | 上游 .pc 有两级 -I（`include/libgda-5.0` 与 `include/libgda-5.0/libgda`），recipe 只暴露了第一级 | `cpp_info.includedirs` 补齐第二级 |
| 22 | test_package：`ld.lld: undefined symbol: gda_value_get_int` | 测试代码用了 libgda 5.x 不存在的 API（只有 `gda_value_get_short` 等） | 测试改用 `gda_value_stringify()` 做值比较 |
| 23 | 运行期 `Could not parse '/share/libgda-5.0/dtd/...'` → `No provider 'SQLite' installed` | libgda 把 DATADIR/provider 目录编译进库；conan autotools 安装走 DESTDIR（configure 记录 `prefix=/`）→ 运行期去找 `/share`、`/lib/libgda-5.0/providers` | test_package 运行环境设 `GDA_TOP_BUILD_DIR=<pkg>/lib/libgda-5.0`（libgda 源码 `gda-config.c:1727` 的官方覆盖点，其下 `providers/` 即 SQLite provider），`GDA_TOP_SRC_DIR=<pkg>/share/libgda-5.0` |
| 24 | `The connection string must contain DB_DIR and DB_NAME values` | libgda 5.x 的 SQLite provider 不接受 `:memory:` | 测试改用 `DB_DIR=.;DB_NAME=<name>` 文件库（同时覆盖 HMDFS 文件 I/O） |

> 备注：`prefix=/` 是 conan autotools + DESTDIR 安装的通用现象；本配方通过 test_package 的
> `GDA_TOP_BUILD_DIR` 解决运行期 provider 定位，不额外打源码补丁。若后续要求包内 `.pc`
> 直接可用（非 conan 消费者），可在 `package()` 里把 `.pc` 的 `prefix=/` 改写为 package_folder。

## 7. W2/W3 与 PR 原子性（手工等价检查）

- W2 结构完整性：`conanfile.py` / `conandata.yml` / `test_package/`（conanfile.py +
  CMakeLists.txt + 2 个测试源） / `MANIFEST.yml` / `patches/` 齐全 ✔
- W2 原子性：本次改动**只在** `archives/l/libgda5/**`（`git status` 另有两处 `archives/l/libXext/*`
  修改，是新工作树创建时就存在的**他人未提交改动**，未触碰）
- W3 本地编译验证：`conan create` exit 0（等价于 W3 的 conan create 门禁），日志见
  `libgda5-5.2.10-logs/84-conan-create-*.log`
- R36 依赖发布检查：所需依赖（glib/2.88.3、libxml2/2.15.3、libxslt/1.1.45.2、iso-codes/4.20.1、
  pkgconf/3.0.6、intltool/0.51.0）全部已发布（`conan download`/`conan install` exit 0，
  见依赖分析报告 `libgda5-5.2.10-deps/DEPENDENCY-REPORT-20260921.md`）
- 未运行 `ohc-run.py conan-verify / finish / submit`（本次为手工等价流程；按用户要求
  停在 push/PR 之前）
---

**编译结束**: 2026-09-21 11:40
**最终状态**: built
