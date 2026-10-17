# gmime 3.2.15 适配笔记

## 编译环境

- 构建系统: autotools（**上游 release tarball 自带 configure/Makefile.in**）
- 编译日期: 2026-09-13
- 编译器: clang 15（OHOS aarch64，`/data/service/hnp/bin/clang`）
- 状态: built
- 目标平台: HarmonyOS PC (aarch64, musl, libc++)
- 任务背景: pan 等邮件/新闻客户端的 MIME 解析依赖（开源鸿蒙PC专项积分赛-依赖）

## 与 3.0.5 的关系

3.0.5 的源码取自 GitLab git-archive，只带 `configure.ac` / `Makefile.am`，
配方里必须自举 aclocal/autoconf/autoheader/libtoolize/automake（并补
`gtk-doc.m4`、`ChangeLog`、`gtk-doc.make`）。**3.2.15 用的是上游 GitHub
release tarball `gmime-3.2.15.tar.xz`，其中已包含全部生成物**
（`configure`、各层 `Makefile.in`、`aclocal.m4`、`ltmain.sh`、`config.guess`、
`config.sub`、`compile`、`missing`、`install-sh`、`depcomp`、`gtk-doc.make`），
所以配方**不需要 autotools 自举，也不需要 automake/libtool 的 tool_requires**；
只需 `--disable-maintainer-mode` 关掉重建规则即可。

## 源码与校验

- URL: `https://github.com/jstedfast/gmime/releases/download/3.2.15/gmime-3.2.15.tar.xz`
- SHA-256: `84cd2a481a27970ec39b5c95f72db026722904a2ccf3fdbd57b280cf2d02b5c4`
- 该值与上游随版本发布的 `gmime-3.2.15.sha256sum` 一致。

## 依赖决策

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib2 | 2.88.0 | `PKG_CHECK_MODULES(GLIB: glib-2.0>=2.68 gobject-2.0 gio-2.0 gthread-2.0)` |
| pcre2 | 10.45 | glib2 的传递依赖（`glib-2.0.pc` 的 `Requires: pcre2`） |
| zlib | 1.3.1.1 | `PKG_CHECK_MODULES(ZLIB: zlib)`；override 到 PIC 变体 |

- **gpgme（PGP / S-MIME）**：OHOS 无 gpgme，且下游邮件客户端不需要 → `--disable-crypto`。
- **libidn2**：OHOS 无 libidn2 → `--without-libidn`。
- 两者都是 configure 里的可选分支，关闭后 `ENABLE_CRYPTO` / `LIBIDN` 条件为假，
  相应的测试程序也不参与构建。

## 构建要点

1. **本地原生构建**：configure.ac 用 `AC_RUN_IFELSE` 跑 `iconv-detect.c` 探测
   目标 libc 支持哪些字符集别名（交叉编译时会直接报错要求提供
   `ac_cv_have_iconv_detect_h=yes`）。CI profile 在 OHOS 设备上原生构建，
   因此配方以 `--build=aarch64-linux --host=aarch64-linux` 明确原生三元组，
   让该探测正常执行。
2. **glib2 .pc 修补**：制品仓的 glib2/2.88.0 安装的 `.pc` 文件 `prefix=/`
   （Cflags/Libs 指向 `/include`、`/lib`），且 `glib-2.0.pc` 声明
   `Requires: pcre2`，而 pcre2 包只提供 `libpcre2-8.pc`。`generate()` 把
   glib2 的全部 `.pc` 拷到临时目录并把 `prefix=` 改写为真实包路径，同时补一个
   `pcre2.pc` 别名（`Libs: -lpcre2-8`）；`zlib.pc` 同样修 prefix。
3. **.la 清理**：从制品仓下载的依赖包（如 pcre2/10.45）带 `libdir='//lib'`
   的 `.la`，libtool 链接时会报 not a valid libtool archive。`generate()` 在
   构建前删除 host 依赖里 libdir 不在包内的 `.la`（conan 通过 cpp_info 解析
   链接信息，不依赖 `.la`）。
4. **HMDFS umask**：`configure` 里 `umask 077` 建的 mktemp 目录在鸿蒙安全
   框架下首次写入被拒，改写为 `umask 022`（E114 家族）。
5. **OHOS 工具名**：profile 导出的 `AR/AS/STRIP/NM/RANLIB` 是 llvm-* 名字，
   不一定在 PATH 上；配方解析真实工具路径并写入 `gmime_ohos_buildenv`。

## 上游测试

`tests/Makefile.am` 用自定义 `check-local` 规则逐个跑 `AUTOMATED_TESTS`
（无 crypto 时 11 个）：

```
test-iconv test-streams test-cat test-encodings test-filters test-headers
test-mime-part test-partial test-mbox test-autocrypt test-mime
```

配方 `build()` 里执行 `make check`，输出汇总行
`Results: N tests passed; M tests failed.` 完整落在构建日志中。
两个已知失败与适配无关（平台/环境限制）：

| 测试 | 原因 |
|------|------|
| `test-iconv` | musl iconv 没有 glibc 独有的 `windows-cp1251` 别名（`cp1251` / `windows-1251` 均可用） |
| `test-autocrypt` | 测试开头用 `g_find_program_in_path()` 找 `gpg`/`gpg2`，OHOS 未提供 gpg 二进制 |

另外 7 个测试程序**不属于 `make check` 的自动化集合**：
`test-best` / `test-parser` / `test-html` 是 `MANUAL_TESTS`（交互式），
`test-pgp` / `test-pgpmime` / `test-pkcs7` / `test-smime` 受 `ENABLE_CRYPTO`
门控（本次 `--disable-crypto`）。

## 源码修改

无源码补丁（`patches_applied: []`）。全部适配在 Conan 配方层完成。
