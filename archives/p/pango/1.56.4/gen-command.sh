#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name pango --version 1.56.4 --build-system meson --test-lang c --sign-so --pkgconfig-deps --libs pango-1.0,pangocairo-1.0,pangoft2-1.0 --pkgconfig-name pango --requires glib/2.84.0.1,harfbuzz/14.2.0.1,fribidi/1.0.16,cairo/1.18.4,fontconfig/2.18.1,freetype/2.14.3,libthai/0.1.29 --cli-tool '文字排版命令行工具（pango-view 渲染文本、pango-list 列出可用字体）' --homepage https://pango.gnome.org/ --source-url https://download.gnome.org/sources/pango/1.56/pango-1.56.4.tar.xz --sha256 17065e2fcc5f5a5bdbffc884c956bfc7c451a96e8c4fb2f8ad837c6413cb5a01 --pc-var 'glib-2.0:glib_mkenums=${bindir}/glib-mkenums' --pc-var 'glib-2.0:glib_genmarshal=${bindir}/glib-genmarshal' --pc-var 'glib-2.0:gobject_query=${bindir}/gobject-query' --pc-var 'gobject-2.0:glib_mkenums=${bindir}/glib-mkenums' --pc-cflags 'fribidi=-I${includedir}/fribidi' --alias-pc cairo-ft=cairo,freetype2 --alias-pc cairo-fc=cairo,fontconfig --meson-option fontconfig=enabled --meson-option cairo=enabled --meson-option freetype=enabled --meson-option libthai=enabled --meson-option xft=disabled --meson-option sysprof=disabled --meson-option introspection=disabled --meson-option documentation=false --meson-option man-pages=false --meson-option build-testsuite=false --meson-option build-examples=false --out <输出根目录>
