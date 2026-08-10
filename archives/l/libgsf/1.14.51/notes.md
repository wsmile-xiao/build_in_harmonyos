# libgsf 1.14.51 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.72 / automake 1.17 生成，tarball 自带 configure)
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 (cc/c++ 均指向 clang)
- 状态: built

## 编译步骤

```bash
# 1. 打 HarmonyOS 平台识别补丁 (config.guess/config.sub)
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
# 2. config.sub 需补充 kernel-OS 组合: linux-ohos* 加入校验表 (补丁脚本未覆盖)

# 3. configure (禁用 gdk-pixbuf: 系统未装该可选依赖头文件)
PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig \
TMPDIR=/storage/Users/currentUser/tmp \
./configure --prefix=$DEFAULT_PREFIX --without-gdk-pixbuf

# 4. 编译 + 安装
TMPDIR=/storage/Users/currentUser/tmp make -j1
TMPDIR=/storage/Users/currentUser/tmp make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 + 临时文件 Permission denied | HMDFS 上 `umask 077 && mktemp -d` 创建的 2700 目录 owner 与进程 uid 不一致，不可写 (E114) | patch-autotools-ohos.pl 加 HarmonyOS 识别；TMPDIR 指向 $HOME/tmp |
| 2 | config.sub 报 `Kernel 'linux' not known to work with OS 'ohos'` | config.sub kernel-OS 组合校验表缺 linux-ohos | 手动在 `linux-gnu* | ... | linux-uclibc*` 后追加 `\| linux-ohos*` |
| 3 | config.status 报 `can't create ./confXXX/subs1.awk` | 同上 E114：configure 生成的 config.status 也用 umask 077+mktemp | 把 configure/config.status 中 tmp 目录创建改为 `tmp=./conf$$-$RANDOM; mkdir "$tmp"` |
| 4 | gsf-input-http.c 报 xmlNanoHTTP* 未声明 | libxml2 2.16 已移除 nanohttp API (2.15 起废弃) | 应用上游补丁 (commit 5d4bb55095): configure.ac 加 `AC_CHECK_FUNCS(xmlNanoHTTPOpen xmlNanoHTTPClose)`，gsf-input-http.c 用 `#ifdef HAVE_XMLNANOHTTPOPEN/CLOSE` 守卫（修正上游笔误 HAVE_XML_NANOHTTPOPEN→HAVE_XMLNANOHTTPOPEN），无 nanohttp 时返回 NULL |
| 5 | 链接失败: libffi.so `bad shoff` (仅 10KB) | usr/local/lib/libffi.so.8.1.2 损坏 | 移走损坏 .so 符号链接，改 libffi.la (dlname/library_names 置空) 回退 libffi.a |
| 6 | tools 链接缺 g_libintl_* 符号 | glib 静态库引用 g_libintl_*，但 -lintl 解析到 libintl.so (无 g_libintl_* 符号) | 移走 libintl.so 符号链接，回退 libintl.a (含 g_libintl_* 定义) |
| 7 | thumbnailer 缺 gdk-pixbuf.h | gdk-pixbuf 头文件未安装 | configure 加 `--without-gdk-pixbuf` |
| 8 | make check 9 个测试全 FAIL | 测试脚本 shebang `#!/usr/bin/perl` 指向不存在的 /usr/bin/perl；且 LibGsfTest.pm 依赖 XML::Parser perl 模块 (cpan 网络超时无法安装) | shebang 改为 `#!/usr/bin/env perl`；XML::Parser 2.59 已从清华 CPAN 镜像源码编译安装（expat 本地库 + Makefile.PL rpath），make check 恢复为 7 PASS / 2 SKIP（剩余 SKIP 因 valgrind 不可用） |
| 9 | make 触发 aclocal/automake 1.16 重新生成失败 | 修改 configure.ac 后维护者模式规则要求重新生成构建系统，系统只有 1.17 | 理顺时间戳链: 源文件 < aclocal.m4 < configure < Makefile.in < config.status < Makefile，避免 make 重跑 autotools |

## 源码修改

- `config.guess`: 添加 HarmonyOS 系统识别 (patch-autotools-ohos.pl)
- `config.sub`: 添加 ohos-linux 三元组 + kernel-OS 组合 linux-ohos*
- `configure.ac`: 添加 `AC_CHECK_FUNCS(xmlNanoHTTPOpen xmlNanoHTTPClose)` (nanohttp 检测)
- `gsf/gsf-input-http.c`: nanohttp API 条件编译守卫
- `configure`/`config.status`: tmp 目录创建改为 mkdir 方式 (HMDFS E114)
- `tests/t*.pl`: shebang `#!/usr/bin/perl -w` → `#!/usr/bin/env perl`

## 依赖版本

- glib: 2.88.0 (usr/local, 静态)
- libxml2: 2.16.0 (usr/local)
- zlib: 1.3.1 (usr/local)
- gdk-pixbuf: 未安装 (已禁用)

## 验证结果

```bash
# 库与工具编译安装成功
$ ls usr/local/lib/libgsf-1.so* && ls usr/local/include/libgsf-1/gsf/gsf.h
$ tools/.libs/gsf --version
gsf version 1.14.51
$ PKG_CONFIG_PATH=usr/local/lib/pkgconfig pkg-config --modversion libgsf-1
1.14.51

# make check: 7 PASS / 2 SKIP (0 FAIL, 0 ERROR)
# 分析: 测试脚本 shebang 已修复; XML::Parser 2.59 已从清华 CPAN 镜像源码编译安装
#       (expat 使用本地库, Makefile.PL check_lib 加 rpath 解决 HMDFS 加载);
#       zipinfo 已存在于制品仓 (zipinfo/6.0.2 独立包已合入 main), 原 9 个 SKIP 中的
#       7 个 (t1000-t1005/t9999) 恢复实际执行并全部 PASS; 剩余 2 SKIP (t8000/t8020)
#       因 valgrind 不可用 (已编译成功, 但本环境运行时 SIGSEGV), 属测试可选依赖
```

## 注意事项

1. **make check 恢复为 7 PASS / 2 SKIP（0 FAIL/0 ERROR）**：libgsf 测试套件 (LibGsfTest.pm) 依赖 perl XML::Parser 模块——已从清华 CPAN 镜像下载 XML-Parser 2.47 源码，用本地 expat 编译安装成功（检测版本 2.59）；Makefile.PL 的 check_lib 探测需加 `-Wl,-rpath`（HMDFS 上 LD_LIBRARY_PATH 会干扰 lld 加载 libxml2）。zipinfo 已存在于制品仓（zipinfo/6.0.2 独立包已合入 main，非 unzip 包内工具），原因 zipinfo 缺失而 SKIP 的 7 个测试（t1000-t1005/t9999）恢复实际执行并全部 PASS；剩余 2 SKIP（t8000/t8020）因 valgrind 不可用——valgrind 3.24.0 已本地编译成功（--version/memcheck 工具均正常），但本环境（HMDFS）运行时 SIGSEGV 崩溃无法执行被测程序，属测试可选依赖，非编译缺陷。库本身 configure/make/install 全部通过。
2. **libffi/libintl 动态库损坏处理**：usr/local/lib/libffi.so.8.1.2 损坏 (bad shoff)，libintl.so 无 g_libintl_* 符号——均已通过 .la 调整/符号链接移走回退到静态库解决。conan 配方需注意用静态库链接。
3. **构建系统版本**：源码包 aclocal.m4 基于 automake 1.16，环境只有 1.17；修改 configure.ac 后不要重新跑 autotools，用时间戳链避免 make 重新生成。
---

**编译结束**: 2026-08-05 22:49
**最终状态**: built
