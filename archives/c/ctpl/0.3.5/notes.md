# ctpl 0.3.5 适配笔记

## 编译环境

- 构建系统: autotools (configure + make, 发布包自带生成文件)
- 编译日期: 2026-09-12
- 编译器: clang/clang++
- 状态: built（待真机 conan create 全量验证后更新）

## 上游来源

- 官网: https://ctpl.tuxfamily.org/
- 源码包: https://download.tuxfamily.org/ctpl/releases/ctpl-0.3.5.tar.gz
- SHA-256: `21108fc7567ed216deea4591adbfece8e88b1f4bb1ca77c37400920644d756be`（本机实测下载 700671 字节）
- GitHub 镜像: https://github.com/b4n/ctpl（tag v0.3.5，`ae60c793...`，仅 git 内容无 configure，仅作交叉核验，不采用）
- 许可证: GPL-3.0-or-later
- 版本说明: 0.3 分支 bugfix/enhancement 合集（含 `ctpl_value_take_string`、GCC 14 构建修复）

## 编译步骤

1. `get()` 下载官方 release tarball（strip_root 解包，顶层 `ctpl-0.3.5/`）。
2. `generate()` 生成 PkgConfigDeps + AutotoolsToolchain；configure 参数固定
   `--build/--host=aarch64-unknown-linux-gnu`（config.guess 不识 OHOS，绕过探测；
   编译器仍经工具链指向 OHOS sysroot/target）与 `--enable-static/--disable-shared`。
3. `build()` 内对源码树 `configure` 做 `umask 077 -> 022` 宽松（HMDFS 可写性），
   预置 `PWD`（getcwd 回退）与可写 `TMPDIR/TMP/TEMP`（真机 /tmp 只读），然后
   `configure`、`make -j1`、`make check -j1`。
4. `package()` 走 `autotools.install()`（lib/libctpl、include/ctpl/*.h、lib/pkgconfig/ctpl.pc、
   以及 CLI 启用时的 bin/ctpl）；上游测试结果 JSON 复制进 `res/upstream_test_result.json`。

## 上游测试

- `testsuite/Makefile.am`: `TESTS = parsing-tests float-test read-number-test (+tests.sh)`。
  `parsing-tests` 遍历 `testsuite/success/` 14 个模板与 `testsuite/fail/` 6 个模板，
  以 `testsuite/environ` 为环境解析并比对 `-output` 期望输出；`float-test` 穷举浮点
  格式化；`read-number-test` 覆盖数字字面量；`tests.sh` 用 CLI 复跑全集（CLI 启用时）。
- 配方解析各 `test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP`（兼顾 XFAIL/XPASS/ERROR），
  校验 `testsuite/success` 参照非空，零执行或失败即阻断构建，并输出
  `HMBS_UPSTREAM_TEST_RESULT` 标记。
- test_package 3 用例（test.c）：模板替换端到端、environ push/lookup、未知符号错误路径；
  经 `ctest + ./test_ctpl` 真实运行后输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识 OHOS，configure 探测失败 | autotools 上游无 HarmonyOS 三元组 | 固定 `--build/--host=aarch64-unknown-linux-gnu`，绕过探测（cdecl/castget 先例） |
| 2 | `PKG_CHECK_MODULES(GLIB/GIO)` 找不到 pkg-config | 真机无系统 pkg-config | `tool_requires pkgconf/3.0.5` + `PkgConfigDeps`（cassbeam/castget 先例） |
| 3 | glib 依赖图拉起官方 zlib 导致 OHOS cmake 失败 | glib/2.88.0 依赖 plain zlib/1.3.1 | `requires zlib/1.3.1.1 override` 锁定 OHOS 专用版本（cassbeam 先例） |
| 5 | make: *** empty variable name. Stop (la-free LIBS via make argv with spaces, unquoted split) | Autotools.make joins args into shell string; GLIB_LIBS=-L..<shadow> -l.. split into separate argv, -l* misparsed as goals/options | Rewrite GLIB/GIO/CTPL_CLI LIBS in-place in all generated Makefiles post-configure (shadow -L, keep -l), plain make -j1 (E236 file-patch, bitlbee env/file precedent) |
| 6 | libtool: '//lib/libpcre2-8.la' is not a valid libtool archive + was moved (真机 2026-09-11) | 仅改 Makefile -L 未阻止 libtool 按 -lpcre2 查找缓存 .la；pcre2 包 .la 内 libdir='//lib'（prefix=/ 产物） | 双层静态化（babeltrace/libgsf 先例）：generate() 改写 .pc 的 -lpcre2-* 为绝对 .a + Makefile 同替换；其余 -l 仍走 shadow -L，缓存不动 |
| 7 | make install: libtool install -c .libs/libctpl.a DEST 后 chmod 644 报 No such file（真机 2026-09-11 package 阶段） | configure 烘焙的 HMBS 单文件双参 install shim / toybox install 与 HMDFS 不兼容（install_shim:true + chmod:0 + hardlink:0），目标目录未实际落地导致后续 chmod 找不到文件 | build() configure 后写 _ohos_install_shim/install（cp/mkdir 语义、多源支持、chmod best-effort，os.open 0o755）并重定向全部生成 Makefile 的 INSTALL 变量（xeyes/wv E182/E188 先例） |
| 8 | `CCLD test` undefined `g_libintl_*` (CI #44690 make check, NLS=no INTLLIBS empty) | AM_GNU_GETTEXT probe says no on OHOS yet ctpl-i18n.c + static libglib/libgio need proxy-libintl; recipe patched only GLIB/GIO_LIBS vars, real test link uses configure-expanded libctpl_la_LIBADD literal | generate() extra LDFLAGS absolute libintl + Makefile file-patch every LIBS/LIBADD/LDADD (stale -L->shadow, -lpcre2/-lintl->abs, append intl if missing; E015/E566); test_package GLIB_LIBINTL explicit link (zeitgeist precedent) |
| 4 | HMDFS 下 configure 临时目录不可写 | `umask 077` + 只读 /tmp | configure 内 `umask 022` 宽松 + 可写 TMPDIR（E011/E002） |

## 依赖版本

- glib/2.88.0（含 glib-2.0、gio-2.0、gio-unix-2.0；CLI 工具所需）
- zlib/1.3.1.1（override，OHOS 专用后缀版本）
- pkgconf/3.0.5（tool_requires，提供 pkg-config）
- 系统库: m（`AC_CHECK_LIB([m], [acos])`）

## 验证结果

```bash
# 待 HMBS 真机预检（conan create 全量：configure + make -j1 + make check + test_package）
# 通过后回填 test-suite.log 汇总与 HMBS markers 实测行
```

## 注意事项

- 官方 tarball 与 GitHub tag 包内容同源但形态不同：前者含生成文件可直接 configure，
  后者需 autoreconf 且真机缺 automake/libtool 链；配方锁定前者。
- CLI 工具（bin/ctpl）随 `--enable-cli-tool=auto` 在 gio-unix 可用时自动构建；
  本配方按 library 打包，不单列 commands.json（库附带二进制为 warn 级，不阻断）。
- `CtplValue` 公共 API 类型名为 `CTPL_VTYPE_*` + `ctpl_value_get_held_type()`，
  非 `CTPL_VALUE_*`/`ctpl_value_get_type()`；test.c 已按 `src/ctpl-value.h` 核对。
