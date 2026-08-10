# gegl 0.4.70 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# Dependencies installed via conan:
# babl/0.1.126, glib/2.84.0.1, json-glib/1.10.6, libpng/1.6.58,
# libjpeg/10, libtiff/4.7.2, libwebp/1.6.0, cairo/1.18.4,
# pango/1.56.4, fftw/3.3.10.1

# Patch applied:
# 0001-skip-check-def-files-harmonyos.patch

# Meson configure and build
meson setup _build --prefix=$DEFAULT_PREFIX \
  --default-library=shared \
  -Dwrap_mode=nodownload \
  -Dintrospection=disabled \
  -Ddocs=false \
  -Dcairo=enabled -Dpango=enabled -Dwebp=enabled \
  -Dlibtiff=enabled \
  -Dgexiv2=disabled -Dlcms=disabled -Dlibrsvg=disabled -Dopenexr=disabled
ninja -C _build -j2
ninja -C _build install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | check-def-files fails | libintl/gnulib symbol leak on OHOS | Patch: skip check-def-files when host_machine.system() == 'harmonyos' |
| 2 | json-glib missing | Not in ohpcd repo | Adapted json-glib 1.10.6 as dependency |
| 3 | glib .pc missing glib_mkenums | PkgConfigDeps generates simplified .pc | _fix_glib_pc_files() adds glib_mkenums variable |
| 4 | glib .pc missing -lintl | PkgConfigDeps doesn't include -lintl | _fix_glib_pc_files() adds -lintl to Libs |
| 5 | meson can't find llvm-ar | Not in PATH | _inject_meson_binaries() injects ar/ranlib into native file |

## 依赖版本

- babl/0.1.126 (from ohpcd)
- glib/2.84.0.1 (from ohpcd)
- json-glib/1.10.6 (locally adapted)
- libpng/1.6.58 (from ohpcd)
- libjpeg/10 (from ohpcd)
- libtiff/4.7.2 (from ohpcd)
- libwebp/1.6.0 (from ohpcd)
- cairo/1.18.4 (from ohpcd)
- pango/1.56.4 (from ohpcd)
- fftw/3.3.10.1 (from ohpcd)

## 补丁

### 0001-skip-check-def-files-harmonyos.patch
Skip the check-def-files custom_target on HarmonyOS. The check uses nm to verify .def
files for Windows linking, but on HarmonyOS libintl/gnulib symbols cause false positives.

## 注意事项

- json-glib 1.10.6 was adapted as a new dependency package (not previously in ohpcd)
- poly2tri-c and libnsgif are bundled as subprojects in GEGL source (no external dep needed)
- Optional deps not in ohpcd (gexiv2, lcms, librsvg, libraw, openexr, etc.) are disabled
