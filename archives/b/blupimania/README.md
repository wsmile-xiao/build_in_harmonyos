# blupimania

Blupimania — A mind boggling (brain twisting) game of logic（益智逻辑游戏，Blupi 系列）。

- 上游仓库: https://github.com/blupi-games/blupimania
- 上游版本: 1.6.3（tag v1.6.3）
- 语言/构建系统: C / CMake
- 产物类型: 单可执行文件 `blupimania`（GUI 游戏，SDL2 抽象平台层）+ share/blupimania 数据资源
- 许可证: GPL-3.0

## OHOS 适配

- 依赖: sdl2/2.30.10、sdl2-image/2.8.12、sdl2_mixer/2.8.2、libwebp/1.6.0（均已在 ohpcd 制品仓发布）
- 关键适配点见 `1.6.3/notes.md` 与 `1.6.3/manifest.yaml`（CMake 4 policy、E092 系统名、WebP::webpdemux 注入、CMakeDeps target 命名对齐、ELF 签名）
