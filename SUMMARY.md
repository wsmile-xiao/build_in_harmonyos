# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-04-21
> 已收录软件：66 款 / 70 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **66** 款 |
| 软件版本 | **70** 个 |
| ✅ 完全成功 | 43 |
| ⚠️ 部分成功 | 25 |
| ❌ 编译失败 | 0 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 51 |
| CMake | 7 |
| Makefile | 5 |
| unknown | 2 |
| Script | 1 |
| Custom Perl | 1 |
| python | 1 |
| manual | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **argp-standalone** | latest | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/a/argp-standalone/latest/) |
| **automake** | 1.16.5 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | perl    # 运行时必需（纯 Perl 项目）,autoconf  # 配合 autoreconf 使用,gnu-make   # 构建 Autotools 项目时需要 | [📄](archives/a/automake/1.16.5/) |
| **bash** | 5.3 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/b/bash/5.3/) |
| **bear** | 3.1.6 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/b/bear/3.1.6/) |
| **boxes** | 2.3.1 | ⚠️ 部分成功 |  | Makefile | 1 | libunistring-1.0,pcre2-10.40 | [📄](archives/b/boxes/2.3.1/) |
| **bsd-compat-headers** | latest | ✅ 完全成功 |  | Autotools | 0 | - | [📄](archives/b/bsd-compat-headers/latest/) |
| **bzip2** | 1.0.8 | ✅ 完全成功 | 🟢 高 | Makefile | 0 | - | [📄](archives/b/bzip2/1.0.8/) |
| **ccache** | 4.12.1 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/c/ccache/4.12.1/) |
| **coreutils** | 9.10 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | []  # 无额外依赖 | [📄](archives/c/coreutils/9.10/) |
| **curl** | 8.19.0 | compiling |  | Autotools | - | - | [📄](archives/c/curl/8.19.0/) |
| **distcc** | 3.4 | ⚠️ 部分成功 |  | Autotools | 5 | - | [📄](archives/d/distcc/3.4/) |
| **doctest** | 2.5.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/d/doctest/2.5.2/) |
| **dos2unix** | 7.5.4 | ✅ 完全成功 | 🟢 高 | Makefile | 1 | name: gettext | [📄](archives/d/dos2unix/7.5.4/) |
| **file** | 5.45 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/f/file/5.45/) |
| **ftxui** | 6.1.9 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/f/ftxui/6.1.9/) |
| **gawk** | 5.3.0 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/g/gawk/5.3.0/) |
| **gdbm** | 1.23 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/g/gdbm/1.23/) |
| **glib** | latest | ⚠️ 部分成功 |  | Autotools | 4 | - | [📄](archives/g/glib/latest/) |
| **gzip** | 1.13 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/g/gzip/1.13/) |
| **help2man** | 1.49.3 | ✅ 完全成功 | 🟢 高 | Script | 0 | - | [📄](archives/h/help2man/1.49.3/) |
| **htop** | 3.4.1 | ⚠️ 部分成功 | 🟡 中 | Autotools | 3 | - | [📄](archives/h/htop/3.4.1/) |
| **intltool** | 0.51.0 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/i/intltool/0.51.0/) |
| **jna** | 5.19.0 | ✅ 完全成功 |  |  | - | bishengjdk17 (signed),libffi (static, already ported to HarmonyOS) | [📄](archives/j/jna/5.19.0/) |
| **jq** | 1.7.1 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/j/jq/1.7.1/) |
| **lemon** | 3.53.0 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/l/lemon/3.53.0/) |
| **libassuan** | 3.0.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libassuan/3.0.2/) |
| **libdeflate** | 1.25 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/l/libdeflate/1.25/) |
| **libffi** | 3.4.4、3.5.2 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/l/libffi/3.5.2/) |
| **libgpg-error** | 1.55 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libgpg-error/1.55/) |
| **libpipeline** | 1.5.8 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/l/libpipeline/1.5.8/) |
| **libqrcodegen** | 1.8.0 | ✅ 完全成功 |  | CMake | 3 | - | [📄](archives/l/libqrcodegen/1.8.0/) |
| **libtasn1** | 4.21.0 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libtasn1/4.21.0/) |
| **libtool** | 2.4.7 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/l/libtool/2.4.7/) |
| **libunistring** | 1.0 | ✅ 完全成功 |  | Autotools | 1 | [] | [📄](archives/l/libunistring/1.0/) |
| **man-db** | 2.13.1 | ✅ 完全成功 | 🟡 中 | Autotools | 4 | gdbm 1.23,bzip2 1.0.8,libpipeline 1.5.8,groff 1.23.0  # 运行时依赖 | [📄](archives/m/man-db/2.13.1/) |
| **meson** | 1.11.0 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/m/meson/1.11.0/) |
| **musl-fts** | latest | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/m/musl-fts/latest/) |
| **musl-obstack** | 1.2.3 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/m/musl-obstack/1.2.3/) |
| **ncurses** | 6.4 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/n/ncurses/6.4/) |
| **nettle** | 3.10.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/n/nettle/3.10.2/) |
| **notcurses** | 3.0.17 | ✅ 完全成功 |  | CMake | 10 | ncursesw-6.4,libunistring,libdeflate | [📄](archives/n/notcurses/3.0.17/) |
| **openssl** | 1.1.1w | ✅ 完全成功 | 🟢 高 | Custom Perl | 1 | - | [📄](archives/o/openssl/1.1.1w/) |
| **patch** | 2.7.6 | ⚠️ 部分成功 | 🟡 中 | Autotools | 1 | - | [📄](archives/p/patch/2.7.6/) |
| **pcre2** | 10.40 | ✅ 完全成功 |  | Autotools | 1 | [] | [📄](archives/p/pcre2/10.40/) |
| **perl** | 5.42.2 | ⚠️ 部分成功 |  | unknown | - | - | [📄](archives/p/perl/5.42.2/) |
| **pkg-config** | 0.29.2 | ✅ 完全成功 |  | Autotools | 6 | - | [📄](archives/p/pkg-config/0.29.2/) |
| **python** | 3.12.9、3.9.0、3.9.25 | tested |  | Autotools | 82 | - | [📄](archives/p/python/3.9.25/) |
| **ragel** | 6.10 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/r/ragel/6.10/) |
| **re2c** | 4.3.1 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/r/re2c/4.3.1/) |
| **readline** | 8.2 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | name: ncurses | [📄](archives/r/readline/8.2/) |
| **rsync** | 3.3.0 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | - | [📄](archives/r/rsync/3.3.0/) |
| **samurai** | 1.2 | ✅ 完全成功 |  | Makefile | 2 | - | [📄](archives/s/samurai/1.2/) |
| **scintilla** | 5.6.1 | ⚠️ 部分成功 | 🟡 中 | Makefile | 0 | - | [📄](archives/s/scintilla/5.6.1/) |
| **scons** | 4.10.0 | ✅ 完全成功 |  | python | - | - | [📄](archives/s/scons/4.10.0/) |
| **sed** | 4.9 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/s/sed/4.9/) |
| **sqlite3** | 3.49.1 | ✅ 完全成功 |  | manual | 2 | - | [📄](archives/s/sqlite3/3.49.1/) |
| **strace** | 6.19 | ⚠️ 部分成功 | 🔴 低 | Autotools | 3 | - | [📄](archives/s/strace/6.19/) |
| **swig** | 4.4.0 | ✅ 完全成功 |  | Autotools | 4 | - | [📄](archives/s/swig/4.4.0/) |
| **tar** | 1.35 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/t/tar/1.35/) |
| **texinfo** | 7.3 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/t/texinfo/7.3/) |
| **vala** | 0.56.18 | ⚠️ 部分成功 |  | Autotools | 3 | - | [📄](archives/v/vala/0.56.18/) |
| **waf** | 2.1.9 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/w/waf/2.1.9/) |
| **wget** | 1.19.1 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | - | [📄](archives/w/wget/1.19.1/) |
| **xz** | 5.6.2 | ⚠️ 部分成功 |  | unknown | 12 | - | [📄](archives/x/xz/5.6.2/) |
| **zlib** | 1.3.1 | ✅ 完全成功 | 🟢 高 | CMake | 0 | - | [📄](archives/z/zlib/1.3.1/) |
| **zlib-ng** | 2.3.3 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/z/zlib-ng/latest/) |

---

*本文档由 `ohc summary` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区