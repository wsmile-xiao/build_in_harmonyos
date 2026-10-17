# tmx

Portable C library to load [Tiled](https://www.mapeditor.org/) maps in games
(upstream: https://github.com/baylej/tmx, BSD-2-Clause).

- 构建系统：CMake；依赖 `libxml2`（强制）与 `zlib`（`WANT_ZLIB=ON`）。
- 上游 1.10.1 无自动化测试套件，验证由版本目录下 `test_package/` 的 14 项消费者断言承担。
- 适配版本见 `manifest.yaml`；单版本适配细节见对应版本目录的 `notes.md`。
