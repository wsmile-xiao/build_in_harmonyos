# json-glib 1.10.6.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# Install glib via conan
conan install --requires=glib/2.84.0.1 -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -g=PkgConfigDeps

# Build json-glib
meson setup _build --prefix=$DEFAULT_PREFIX \
  --default-library=shared \
  -Dintrospection=disabled \
  -Dtests=false \
  -Ddocumentation=disabled \
  -Dman=false
ninja -C _build -j2
ninja -C _build install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson can't find clang | PATH not set | Set CC/CXX/AR to full paths in /data/service/hnp/bin/ |
| 2 | libpcre2-8 not found via pkg-config | glib internal .pc references pcre2 | Use PkgConfigDeps generator .pc files instead |
| 3 | glib_mkenums variable not in .pc | PkgConfigDeps generates simplified .pc | Manually add glib_mkenums to generated .pc |
| 4 | undefined symbol: g_libintl_* | Generated .pc missing -lintl | Add -lintl to generated .pc Libs |

## 依赖版本

- glib/2.84.0.1 (from ohpcd)

## 验证结果

```bash
# Library installed
ls /usr/local/lib/libjson-glib-1.0.so*
# pkg-config
pkg-config --modversion json-glib-1.0
# Result: 1.10.6
```
