# readstat 1.1.9 适配笔记

## 编译环境
- 构建系统: autotools（上游仅有 configure.ac + Makefile.am；VS17/ 为 MSVC 工程，tarball 内无 CMake）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（OHOS SDK，`/data/service/hnp/bin/clang`）
- 平台: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤

上游 tag 归档**不含预生成的 configure**，因此第一步是 bootstrap：

```sh
# 1) bootstrap（tool_requires: automake/1.18 + libtool/2.5.4 + gettext/0.22.5.1）
#    ACLOCAL_PATH 必须含 gettext 的 share/aclocal（AM_ICONV 宏在 iconv.m4）
autoreconf -fi

# 2) configure：config.guess 不认 HarmonyOS → 显式钉 build/host 三元组
./configure --prefix=/ --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu

# 3) 编译 + 上游测试 + 安装
make -j<n>
make check          # TESTS = test_readstat test_dta_days test_sav_date test_double_decimals
make install DESTDIR=<package_folder>
```

配方层面：`generate()` 走 `AutotoolsDeps` + `AutotoolsToolchain`（静态默认 `--enable-static
--disable-shared`，OHOS 加 `--build/--host`，并把 gettext 的 `share/aclocal` 前置进
`ACLOCAL_PATH`、把 `TMPDIR` 指进 build 目录）；`build()` 顺序为
「缺 configure 才 `autoreconf -fi` → HMDFS 临时目录归一 → configure → make → make check」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 上游 config.guess 不认识 `uname` 输出 `HarmonyOS`；且**上游 tarball 根本不含 config.guess/config.sub**（由 automake `--add-missing` 在 autoreconf 时从 automake/1.18 包落入），没有可打补丁的文件——知识条目 E007/E129「应更新 config.guess 而非传 --build/--host」的前提在本包不成立 | 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（兼容三元组，同时命中 configure.ac 的 `*linux*` 分支取得 `-lm`；与 epeg/aalib/aldo 同法）。未打 config.guess 补丁、未 vendor 生成文件 |
| 2 | `libtoolize: error: $pkgauxdir is not a directory: '//share/libtool/build-aux'` | libtoolize 的 `@datadir@` 被烤进构建机绝对路径 | 由容器层 `libtool/2.5.4` 配方的 `_lt_pkgdatadir` 环境变量绕开（tool_requires 自动带出）；配方无需处理 |
| 3 | `config.status[1025]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 autoconf 的 `(umask 077 && mkdir …)` / `mktemp -d "./confXXXXXX"` 落成 2700 目录，属主映射后不可写（E011 同族） | `build()` 在运行 configure 前把生成的 `configure` 中 `umask 077`→`umask 022`、`./confXXXXXX`→`${TMPDIR:-.}/confXXXXXX`、`tmp=./conf$$-$RANDOM`→`${TMPDIR:-.}/conf$$…`，并把 `TMPDIR` 指向 build 目录内；打出 `[hmdfs] applied=N residual_umask077=M` 可 grep 校验 |
| 4 | `error: a function declaration without a prototype is deprecated in all versions of C [-Werror,-Wstrict-prototypes]`（`src/bin/readstat.c:157`、`src/readstat_bits.c:11` 等） | 上游 Makefile.am 给目标钉了 `-Werror -pedantic-errors -std=c99`，而 clang 15 已默认开启 `-Wstrict-prototypes`（上游 CI 的 clang 版本更老） | 不改上游源码：`CFLAGS` 追加 `-Wno-strict-prototypes`（用户 CFLAGS 排在目标 `_CFLAGS` 之后，可关掉该告警）；`-Werror` 其余告警仍然生效 |
| 5 | 关闭 HAVE_ZLIB 会让 `make check` 真实失败 | 测试集把 ZSAV（`RT_FORMAT_SAV_COMP_ZLIB`）算进 `RT_FORMAT_SPSS`，无 zlib 时写读往返不可用 | 显式 `requires("zlib/1.3.1.1")`（制品仓已有 OHOS 二进制），既补齐测试面又避免静默链接 SDK 系统 libz（R26/G3） |
| 6 | 可选依赖 `libxlsxwriter` 在制品仓不存在 | 上游 `AC_CHECK_LIB(xlsxwriter)` 为可选写路径 | 缺省禁用（不影响任何上游测试用例，`RT_FORMAT_*` 不含 xlsx）；`libcsv` 同理保持关闭 |
| 7 | 采信轮第 1 轮 G2 失败：`configure.ac:43: warning: macro 'AM_ICONV' not found` → `error: possibly undefined macro: AM_ICONV` | 制品仓 `gettext/0.22.5` 的**包内容是库形态**（只有 `include/ lib/ share/locale`，既无 `bin/` 也无 `share/aclocal/`），拿不到 iconv.m4；`gettext/0.22.5.1` 才带 `bin/autopoint` + `share/aclocal`（含 iconv.m4/lib-link.m4 等全套）+ `share/gettext` 数据文件 | tool_requires 改为 `gettext/0.22.5.1`（avahi-compat-libdns_sd 同款）；`generate()` 里 `_iconv_macro_dirs()` 收集 conan 包内 `share/aclocal`、`share/gettext/m4` 与 HNP glob（`/data/service/hnp/*/*/share/{gettext/m4,aclocal}`），**任一目录有 iconv.m4 才继续、全无则直接抛带候选清单的 ConanInvalidConfiguration**，并设 `gettext_datadir` 覆盖 autopoint 烤死的 datadir |

## 源码修改

**无补丁文件**（`patches/` 为空，`conandata.yml` 的 `patches: []`）。上表 #3/#4 均为构建期
环境处理（对生成的 `configure` 做字符串归一、`CFLAGS` 追加），不改动上游任何源文件与测试。

## 依赖版本

- 运行/链接: `zlib/1.3.1.1`（显式）、`iconv`（HarmonyOS libc 内置，configure 判定
  `checking for working iconv... yes`）、`m`（configure 按 `*linux*` 给出 `-lm`）
- 构建期 tool_requires: `automake/1.18`、`libtool/2.5.4`、`gettext/0.22.5.1`；`autoconf`
  用 SDK/HNP 自带 2.73（不声明 conan autoconf，避免 §一.23 的 perl ABI 崩溃）
- 未启用的可选依赖: `libxlsxwriter`（制品仓无）、`libcsv`、`ragel`（9 个 `.rl` 的生成产物
  `.c` 已签入源码，`RAGEL=true` 回退不影响构建）

## 验证结果

```bash
# 手工编译（Mode B Step 2，$BUILD_SRC_DIR）
AUTORECONF_RC=0 CONFIGURE_RC=0 MAKE_RC=0 INSTALL_RC=0 CHECK_RC=0
# make check 汇总（_build/test-suite.log）
#   # TOTAL: 4   # PASS: 4   # SKIP: 0   # FAIL: 0   # ERROR: 0
#   PASS: test_readstat / test_dta_days / test_sav_date / test_double_decimals
# 安装树清点：7 个文件（bin/readstat、bin/extract_metadata、include/readstat.h、
#             lib/libreadstat.*、share/man/man1/*.1）
# 逐项断言清点见 test_package/MANIFEST.yml（assertion_count=336378）
```

## 注意事项

- 上游 `configure.ac` 的 `READSTAT_MICRO_VERSION` 仍是 8（上游 TODO 未同步 1.1.9），因此
  安装产物 soname 为 `libreadstat.so.1.1.8`；本配方默认静态交付，不受影响，属上游已知问题。
- `extract_metadata` 无 `--version`/`--help` 选项（只认 `<input> <output>` 参数），conan-verify
  L2 smoke 对它会走 `--help` 回退分支，属预期。
- 上游 `dump_buffer()` 在 `DEBUG` 下写 `/tmp`；默认构建未定义 `DEBUG`，不触碰只读 `/tmp`。
