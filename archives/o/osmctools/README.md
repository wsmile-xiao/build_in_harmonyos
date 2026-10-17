# osmctools

A few really fast tools to convert, filter and update OpenStreetMap data files.

## 功能

- **osmconvert**: 转换 .osm / .pbf / .o5m 格式, 依赖 zlib (gzopen) + libm (sin/cos)
- **osmfilter**: 按标签 / 边界过滤 OSM 数据, 仅依赖 libc
- **osmupdate**: 按时间增量更新 OSM 数据, 仅依赖 libc

## OHOS 适配要点

- 构建方式: **custom 直接编译**（绕开 autotools bootstrap）。上游 GitLab tag archive 仅含 configure.ac + Makefile.am + 三个 .c 源文件, 不含预生成 configure / Makefile.in。OHOS 真机工具链有 autoconf 2.72 但无 automake/aclocal, `autoreconf --install` 会失败。故 conanfile.py 的 `build()` 直接调用 clang 编译三个单文件可执行程序, 与上游头注释推荐方式一致 (`gcc osmconvert.c -lz -O3 -o osmconvert`)。
- `osmconvert.c` 内另有两个 `int main()` 位于 `#if 0` 块 (cosrk.c/cosr.c 独立测试程序), 预处理器排除后无符号冲突, 真正 main 在 line 12602。
- 编译时显式加 `-Wno-error`: 上游 configure.ac 原用 `AM_INIT_AUTOMAKE([foreign -Wall -Werror])`, 鸿蒙 libc 头文件差异会触发 warning-as-error (E063); 绕开 autotools 后不再触发, 但显式抑制以防工具链默认。
- 上游 0.9 **无任何测试套件** (经审计 configure.ac/Makefile.am/源码确认), `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` + 非空 `upstream_test_audit`。

## 依赖

- 编译/运行: zlib (制品仓 zlib/1.3.1)

## 参考资料

- 上游仓库: https://gitlab.com/osm-c-tools/osmctools
- 上游 tag 0.9: https://gitlab.com/osm-c-tools/osmctools/-/tags/0.9
- OSM 工具说明: https://wiki.openstreetmap.org/wiki/osmconvert
- License: AGPL-3.0-only
