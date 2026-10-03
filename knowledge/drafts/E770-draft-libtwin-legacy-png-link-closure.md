# E770 — 老 Autotools 图形库的 libpng 探测与链接闭环

## 错误特征

libtwin 的旧版 `configure` 只查 `libpng12`，而鸿蒙制品仓提供的是 libpng 1.6 的 `libpng.pc`。即使修改探测后能够编译，原始 `libtwin.so` 仍含 PNG/JPEG/zlib 的未解析符号，却只有 `libc.so` 的 `DT_NEEDED`，实际消费者无法可靠加载。

## 根因与修复

一是构建脚本依赖过时的 pkg-config 模块与已移除的灰度扩展 API；二是 `Makefile.am` 把依赖链接参数给了 demo，却没有给核心共享库的 `LIBADD`。更新 `configure.ac` 和随发布包附带的 `configure` 为 `libpng`，改用 libpng 1.6 API，并让 `libtwin_libtwin_la_LIBADD` 使用现有 `TWIN_DEP_LDFLAGS`。由于目标机没有 `autoreconf`，需同步修补发布包内的 `Makefile.in`。

## 验证与边界

鸿蒙真机上重建后，`readelf -d libtwin.so` 明确列出 `libpng16.so.16`、`libjpeg.so.62`、`libz.so`，实际消费者创建、填充、读取并销毁 ARGB pixmap 通过；Conan 配方和 `test_package` 也通过。上游 `make check` 不含任何测试，此点必须如实报告，不能声称上游测试覆盖。旧 `config.guess` 不认识 HarmonyOS 的问题已由 E007 覆盖，本条只处理依赖探测与链接闭环。
