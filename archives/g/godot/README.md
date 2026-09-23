# godot — Godot Engine

多平台 2D/3D 游戏引擎（MIT）。本归档为 **4.7.2-stable** 的 HarmonyOS PC（OHOS aarch64）适配：
release **export template** 形态（`target=template_release`，editor 裁除），SCons 构建系统交叉编译。

- 上游：https://github.com/godotengine/godot
- 构建产物：`bin/godot`（60MB PIE 可执行，musl 动态器 + libc++_shared）
- 零外部依赖：69 个 thirdparty/ 内置库（freetype/harfbuzz/icu4c/mbedtls/zlib/zstd/brotli/thorvg/...）
- 测试：doctest 嵌入引擎（tests=yes），`godot --test` 运行，注册 1334 个 TEST_CASE

版本索引：
- 4.7.2-stable — 首次适配（2026-09-13）
