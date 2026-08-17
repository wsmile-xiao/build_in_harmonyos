# HarfBuzz

HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。广泛应用于 Firefox、Chrome、Pango、Flutter 等项目。

- **Homepage**: https://harfbuzz.github.io/
- **License**: MIT
- **Build System**: Meson
- **Category**: gfx (字体/文本渲染)

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 14.2.0.2 | built | 2026-08-03 | Meson 构建，含 glib/freetype 支持 |
| 14.2.0.1 | archived | 2026-07-30 | R37 修复版本（已归档） |
| 14.2.0 | archived | 2026-07-22 | Meson 构建（已废弃） |

## OHOS 适配要点

1. **构建系统**: 使用 Meson（CMake 在 HMDFS 上有 subprocess 限制）
2. **glib 支持**: Meson 选项 `glib=enabled`，OHOS 上 `shared=False` 静态链入
3. **freetype 支持**: Meson 选项 `freetype=enabled`，依赖 freetype/2.14.3
4. **共享库**: `shared=True` (默认)，OHOS 上 glib 静态链入避免 dlopen 问题
5. **禁用特性**: `graphite2=disabled`, `cairo=disabled`, `icu=disabled`, `introspection=disabled`
6. **gobject**: OHOS 上 `gobject=disabled`（PkgConfigDeps 不发射 glib_mkenums），其他平台 enabled
7. **utilities**: `utilities=enabled` 构建 hb-shape/hb-subset/hb-info 工具
8. **test_package**: 使用 C (test.c) 调用 hb_version_string/hb_buffer_create API (R34)

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.84.0.1 | Conan (ohpcd) |
| freetype | 2.14.3 | Conan (ohpcd) |
| zlib | 1.3.1.1 | Conan (ohpcd) |

## 参考
- 官网: https://harfbuzz.github.io/
- 源码: https://github.com/harfbuzz/harfbuzz
