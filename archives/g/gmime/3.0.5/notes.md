# gmime 3.0.5 适配笔记

## 编译环境
- 构建系统: autotools（GitLab archive 无生成文件，配方内自举）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: published
- 目标平台: HarmonyOS PC (aarch64, musl, libc++)
- 任务背景: pan 0.165 的前置依赖（开源鸿蒙PC专项积分赛-依赖）

## 编译步骤

1. **源码**：GitLab archive
   `https://gitlab.gnome.org/GNOME/gmime/-/archive/3.0.5/gmime-3.0.5.tar.gz`
   （注意：gmime **3.0.5** 不存在于 download.gnome.org release——那里只有
   3.0.4/3.0.6 的 tarball；ftp.gnome.org/清华/中科大镜像均 404。GitLab
   archive 实测 6.2MB 可下载，sha256=
   `71d4da89e6a1a039e091f7192cce6928fcf2a62f1e8c00fa39c456a9af61c9d3`）

2. **autotools 自举**（GitLab archive 只有 configure.ac/Makefile.am）：
   - `tool_requires automake/1.18 + libtool/2.5.4.1`（制品仓已发布）
   - autoconf/autoheader 2.72 用 hnp 自带（/data/service/hnp/bin/）
   - aclocal 需要 ACLOCAL_PATH 含：glib2 包 share/aclocal（glib-2.0.m4 的
     AM_PATH_GLIB_2_0 宏）+ libtool 包 share/aclocal + hnp pkg-config 的
     pkg.m4 + 源码 m4/（gpgme/introspection/vapigen）+ patches/gtk-doc.m4
   - 补缺失文件：`ChangeLog`（automake dist 规则要求）、`gtk-doc.make`
     （EXTRA_DIST 引用，占位即可）
   - 顺序：aclocal → autoconf → autoheader → libtoolize（先于 automake，
     ltmain.sh 是 automake 依赖）→ automake --add-missing --copy

3. **configure**：
   ```
   ./configure --build=aarch64-linux --host=aarch64-linux \
     --disable-crypto --enable-static --disable-shared \
     --disable-gtk-doc --disable-introspection --enable-vala=no \
     --without-libidn PKG_CONFIG_PATH=<fixed-pc-dir>
   ```

4. **make -j4 && make install**：无错误。

5. **上游测试**：`make check`（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 生成后报 `syntax error near unexpected token '1.8'`（GTK_DOC_CHECK 未展开） | OHOS 无 gtk-doc 包，gtk-doc.m4 宏文件缺失 | 从 gtk-doc 上游取 gtk-doc.m4 放 patches/，自举时拷入 m4/ |
| 2 | `PKG_PROG_PKG_CONFIG: command not found` | pkg.m4 不在任何 conan 包中 | ACLOCAL_PATH 加 hnp pkg-config 的 share/aclocal |
| 3 | automake 生成 Makefile.in 后编译报 `glib.h not found`（GLIB_CFLAGS 空） | automake wrapper 无 PERL5LIB 时 perl 模块加载失败，静默不生成 @GLIB_CFLAGS@ 替换行（RC 仍 0） | VirtualBuildEnv 已注入 PERL5LIB；配方 build() 前置检查 Makefile.in 存在 |
| 4 | pkg-config 报 `Package 'pcre2', required by 'glib-2.0', not found` | glib2 制品包 pc 文件 Requires: pcre2，但 pcre2 包模块名是 libpcre2-8 | 复制 glib2 pc 修 prefix + 生成 pcre2.pc 别名（-lpcre2-8） |
| 5 | `required file './ChangeLog' not found` / `cannot open < gtk-doc.make` | git archive 不带这两个文件（上游 git 不追踪） | touch ChangeLog + 写占位 gtk-doc.make |
| 6 | configure 报 `Cannot find GLIB`（AM_PATH_GLIB_2_0 失败） | glib2 制品包 .pc 文件 prefix=/ 导致 Cflags/Libs 指向 /include /lib | 复制全部 glib2 pc 到临时目录，prefix 改为真实包路径 |
| 7 | test-iconv 失败（27 个 charset 1 个失败） | musl iconv 无 glibc 独有的 `windows-cp1251` 别名（实测 cp1251/windows-1251 均可用） | 平台 libc 限制，记录豁免；非 gmime 代码缺陷 |
| 8 | test-autocrypt 直接 EXIT_FAILURE | 测试开头 `g_find_program_in_path("gpg2"/"gpg")` 找不到 gpg 二进制 | OHOS 无 gpg；crypto 已 --disable-crypto，此测试本属 PGP 相关；记录豁免 |
| 9 | check-local 对 test-mbox/test-partial 显示 "no tests performed" | 构建目录只有运行时生成的 data/cat、data/streams；check-local 先查 $(srcdir)/data/<name>，构建目录（VPATH）无则退化为空路径 | 手工验证：用源码目录 data 实跑两者均 PASS；make check 计为 passed（rc=0） |

## 源码修改

无源码补丁。patches/ 目录只携带 `gtk-doc.m4`（aclocal 宏文件，非源码修改）。

## 依赖版本

- glib2/2.88.0（制品仓，静态，OHOS armv8 clang15）
- zlib/1.3.1.1（制品仓）
- pcre2/10.45（制品仓，glib2 传递依赖，显式声明以生成 pc 别名）
- automake/1.18、libtool/2.5.4.1（tool_requires，制品仓）

## 验证结果

```bash
# conan create（W3，finish 内部执行）
# exit_code=0，test_package L1 测试通过

# 上游测试（make check，8 个 AUTOMATED_TESTS 全量）
Results: 6 tests passed; 2 tests failed.
Failed tests:
 test-iconv      # musl 无 windows-cp1251 别名（glibc 独有）；27 项中 26 项通过
 test-autocrypt  # 需要 gpg/gpg2 二进制，OHOS 环境未提供
# 两个失败均为平台/环境限制，非 gmime 代码缺陷（豁免理由逐条见上表 #7/#8）
# 补充：test-mbox/test-partial 用源码数据目录手工复跑均 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 自举 + glib2 pc 修复 + 上游测试集成 |
| conandata.yml | GitLab archive URL + 实测 sha256 |
| patches/gtk-doc.m4 | aclocal 宏（GTK_DOC_CHECK） |
| test_package/ | 真实 API 测试（GMimeParser/RFC2047/地址列表/主题往返） |

## 注意事项

- pan 0.165 引用 gmime 时用 `gmime/3.0.5`，链接 `-lgmime-3.0`，
  头文件目录 `include/gmime-3.0`。
- crypto（PGP/S/MIME，GpgME）已禁用：OHOS 无 gpgme，pan 的 NNTP 场景不需要。
- 静态库模式（shared=False 默认）：与制品仓 glib2 静态栈一致。
---

**编译结束**: 2026-09-03 20:09
**最终状态**: published
