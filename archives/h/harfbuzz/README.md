# HarfBuzz

HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。广泛应用于 Firefox、Chrome、Pango、Flutter 等项目。

- **Homepage**: https://harfbuzz.github.io/
- **License**: MIT
- **Build System**: Meson
- **Category**: gfx (字体/文本渲染)

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 14.3.1 | in progress | 2026-08-19 | FreeType-only shared candidate; W3/upstream 75/75 and consumer PASS, finish pending |
| 14.2.0.2 | built | 2026-08-03 | Meson 构建，含 glib/freetype 支持 |
| 14.2.0.1 | archived | 2026-07-30 | R37 修复版本（已归档） |
| 14.2.0 | archived | 2026-07-22 | Meson 构建（已废弃） |

## OHOS 适配要点

1. **构建系统**: 使用 Meson，`tests=enabled`、`utilities=enabled`
2. **14.3.1 依赖**: 只启用 `freetype/2.14.3`；FreeType 禁用 HarfBuzz，依赖图无环
3. **共享库**: `shared=True` 为默认和 Pango 消费变体；OHOS 上签名真实版本库，并把 `.so.0`/`.so` 兼容名实体化为普通文件
4. **Python 入口**: 在隔离源码副本中把不可达的 `/usr/bin/env python3` shebang 绑定到当前可执行 Python
5. **禁用特性**: 14.3.1 关闭 glib/gobject/cairo/zlib/icu/graphite2/Rust/平台专用 shaper 等非必要 provider
6. **LLVM 工具**: 从 Conan 编译器配置解析绝对 `ar`/`ranlib`/`nm`/`objdump`/`readelf`/`objcopy` 路径
7. **上游测试**: Meson 原始 inventory 与 JSONL 严格重放，OHOS/aarch64 为 75/75 PASS、零跳过
8. **test_package**: 使用 C API 验证版本、塑形、glyph 信息/位置和 14.3.x `hb_ot_fetch_number` 符号

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| freetype | 2.14.3 | 14.3.1 唯一 Conan 依赖（ohpcd） |
| glib | 2.84.0.1 | 仅历史 14.2.0.2 配方 |
| zlib | 1.3.1.1 | 仅历史 14.2.0.2 配方 |

## 参考
- 官网: https://harfbuzz.github.io/
- 源码: https://github.com/harfbuzz/harfbuzz
