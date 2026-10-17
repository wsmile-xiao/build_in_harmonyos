# libpreludedb 5.2.0 适配笔记

## 编译环境
- 构建系统: autotools（上游 GitHub tag 归档，**不含** configure/Makefile.in，需自举）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin/clang`），CONFIG_SHELL/SHELL=HNP bash
- 平台: OpenHarmony / HarmonyOS PC，aarch64（`aarch64-unknown-linux-ohos`）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15）
- 状态: built

## 编译步骤

```bash
# 1) 初始化（官方 GitHub tag 归档）
python3 scripts/ohc-run.py init-build libpreludedb 5.2.0 --auto \
    --url=https://github.com/Prelude-SIEM/libpreludedb/archive/refs/tags/5.2.0.tar.gz
sha256: fdbfb75f3ae02e016f05881dabb6c2d588b1ae9896624cb46594e765f8b4b261

# 2) 语言预检（R47）：task=cpp, detected=cpp（源文件 98 个，c 主体占比 92%）

# 3) 真实构建 + 上游测试 + test_package（配方内完成）
cd archives/l/libpreludedb/5.2.0
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

配方内部（`build()`）次序：`apply_conandata_patches`（本包无补丁）→ 自举
`libtoolize -c --force --automake` + `aclocal -I m4 -I libmissing/m4` + `autoconf` +
`autoheader` + `automake --add-missing --copy --foreign`（等价上游 `autogen.sh`）→
注入 `config.guess` 的 HarmonyOS 分支（E007）→ 放宽 `configure` 的 `umask 077`（E011）→
`configure`（`--disable-maintainer-mode --disable-gtk-doc --disable-easy-bindings
--without-swig --without-python2 --without-python3`）→ `make -j1` →
`cd libmissing/tests && make check`（上游测试入口）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `AM_PATH_LIBPRELUDE` 失败：`*** Could not run libprelude test program ... The test program compiled, but did not run` → `configure: error: Cannot find libprelude` | 上游 `m4/libprelude.m4` 用 autoconf 老套路：`AC_PATH_PROG` 找 `libprelude-config` 脚本 + `AC_TRY_RUN` **运行**探测程序比对 `prelude_check_version(NULL)`/头文件宏/脚本版本。探测程序链接成功但运行期加载 `libprelude.so.28` 失败：配方注入的 `LD_LIBRARY_PATH` 用 `Environment.append()` 追加，Conan 的默认分隔符是**空格**，拼出 `<旧值> <dir1> <dir2>`，动态链接器与 shell 都不认 | `Environment.append_path()`（按 `os.pathsep` 连接）注入 `PATH` 与 `LD_LIBRARY_PATH`。同时生成最小 `libprelude-config` 兼容层（ohpcd 的 libprelude 制品按 R38 只交付库，`bin/libprelude-config` 已剔除） |
| 2 | test_package 编译失败：`fatal error: 'libprelude/idmef.h' file not found` | libpreludedb 的**公开头文件**直接 `#include <libprelude/prelude-inttypes.h> / <libprelude/idmef.h>`，但 Conan 对非直接依赖默认 `headers=False/libs=False`，CMakeDeps 会把传递依赖的 `INCLUDE_DIRS/LIBS` 清空（`cmakedeps/templates/target_data.py`：`if require and not require.headers: self.include_paths = ""`） | `self.requires("libprelude/5.2.0", transitive_headers=True, transitive_libs=True)`（仓库内 461 个配方同一约定） |
| 3 | E007（预置知识）：`config.guess` 不认 `uname -s` = HarmonyOS，`AC_CANONICAL_TARGET` 直接 "cannot guess build type" | automake 1.18 自带 config.guess（FSF 2024-07-27）无 HarmonyOS 分支 | 注入 `*:HarmonyOS:*:*` → `GUESS=$UNAME_MACHINE-unknown-linux-ohos`；**不用** `--build/--host` 伪造三元组（那会跳过全部 AC_RUN_IFELSE 探测） |
| 4 | E011（预置知识）：HMDFS 下 `config.status` 报 "could not setup config files machinery" | configure 里 `(umask 077 && mktemp -d ./confXXXXXX)` 建出的 0700 目录对当前进程也不可写（HMDFS UID 映射） | `configure` 内 `umask 077` → `umask 022` |

首个真实错误即 #1（首次 `conan create` 的 configure 阶段，退出码 1，日志
`logs/10-conan-create-1.log`）；#2 是第二次运行（build/package 已通过、进入
test_package 后）暴露的消费侧缺陷（日志 `logs/11-conan-create-2.log`）。

## 源码修改

**无**。本版本目录 `patches/` 为空：E007/E011 是对 **autoreconf 生成物**（config.guess、
configure）的构建期修正，libprelude-config 兼容层与 env 注入都在 Conan 侧（`generate()`），
上游源码与构建文件一字未改。

## 依赖版本

| 依赖 | 版本 | 角色 | 证据 |
|------|------|------|------|
| libprelude | 5.2.0 | 强制（`configure.ac:135 AM_PATH_LIBPRELUDE(5.2.0, ...)`），`transitive_headers/libs=True` | conan download -r=ohpcd → EXIT=0（rev 6c5f924f…） |
| automake | 1.18 | tool_requires（自举，归档无 Makefile.in） | conan download → EXIT=0 |
| libtool | 2.5.4 | tool_requires（自举，`libtoolize --automake`） | conan download → EXIT=0 |
| flex / bison | 宿主 HNP（`/data/service/hnp/bin`） | `AC_PROG_LEX` / `AC_PROG_YACC`（路径选择语法由 lex/yacc 生成） | `command -v flex bison` |
| autoconf | 宿主 2.72 | 自举；**故意不** tool_requires（ohpcd 的 autoconf/automake 制品 perl 依赖互相冲突） | `autoconf --version` |

MySQL / PostgreSQL / SQLite3 后端插件由 `AX_LIB_*` 探测决定，本次未探测到
（`configure` 输出 `Enable MySQL plugin : no` 等），因此制品只含 classic 格式插件。
Python2/3、SWIG、gtk-doc 全部显式关闭。

## 验证结果

```bash
# 上游测试（build() 内实跑，automake parallel-tests）
cd libmissing/tests && make check
# Testsuite summary for libpreludedb 5.2.0
# TOTAL: 44 | PASS: 44 | SKIP: 0 | XFAIL: 0 | FAIL: 0 | ERROR: 0

# 消费者测试（conan create 自动执行）
./test_libpreludedb
# libpreludedb 5.2.0 consumer test: OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libpreludedb.so.7.4.1`（soname `libpreludedb.so.7`） | IDMEF 数据库抽象层主库（上游 `-version-info 11:1:4` → libtool current-age=7） |
| `include/libpreludedb/*.h` | 公开头文件（含 `preludedb-version.h`） |
| `lib/libpreludedb/plugins/formats/classic/classic.so` | classic 格式 dlopen 插件（上游默认安装） |
| `share/aclocal/libpreludedb.m4` | `AM_PATH_LIBPRELUDEDB` 宏，供下游 autotools 使用 |

剔除项：`bin/preludedb-admin`（Perl 运维脚本）、`bin/libpreludedb-config`（已被 pkg-config
取代）、`share/man`、全部 `.la`（libtool 归档元数据在制品间不可重定位）。

## 注意事项

- `preludedb_init()` 会去访问编译期常量 `FORMAT_PLUGIN_DIR`（configure 时 prefix=/ →
  `/lib/libpreludedb/plugins/formats`）。该路径在**部署到设备根**后才存在，因此在
  Conan test_package 里不调用 `preludedb_init()`（避免误报），改为直接验证
  `preludedb_check_version` / 路径选择解析器 / libprelude 对象 API。
- test_package 里对非法路径 `not-an-idmef-path((` 断言返回 `< 0`：上游 lexer 会往 stderr
  打 `Unknown token 'x'`（上游行为，非本适配引入），随后 parser 正常报错。
- 本包无 `tests/` 目录，上游测试入口只有随树发布的 gnulib 自检（44 项）；与
  libprelude/5.2.0 的 160 项不同，本包 TESTS 声明即 44 项且全部通过（无内核语义失败项）。
---

**编译结束**: 2026-09-20 19:24
**最终状态**: built
