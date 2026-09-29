# pxlib

pxlib 是读写 Paradox 数据库文件的 C 库（SourceForge，LGPL-2.1）。

## 已适配版本

| 版本 | 状态 | 构建日期 |
| --- | --- | --- |
| 0.6.9 | built | 2026-09-19 |

## OHOS 适配要点

- 无强制第三方 conan 依赖：iconv 由 OHOS musl 系统 libc 提供；libgsf-1 为可选特性（`ENABLE_GSF`，默认 OFF，未启用）。
- 构建系统：CMake（上游自带 `CMakeLists.txt`，≥3.12）。
- 上游 `CMakeLists.txt` 无 `install()` 规则 → 配方 `package()` 中手动拷贝 `libpxlib.a/.so` 与公开头文件。
- 上游版本宏写死 `0.6.8` → patch `0001-fix-version-macro-0.6.9.patch` 对齐 0.6.9 release tag。
- 目标硬编码 `SHARED` → patch `0002-honor-BUILD_SHARED_LIBS.patch` 使其遵循 conan `shared` 选项。
- 公开头 `paradox.h`、`paradox-gsf.h`、`pxversion.h` 由 `*.h.in` 在构建期 `configure_file` 生成，安装进包 `include/`。
- 上游无自动化测试入口（无 `enable_testing()`/`add_test()`/`tests/` 目录），test_package 将 512B 最小 Paradox 4.x 头写入 `$HOME/tmp`，经 `PX_new()` + `PX_open_file()` 做解析冒烟（Paradox 4.0 → pxlib 内部 fileversion=40）。

## 构建命令

```bash
conan create archives/p/pxlib/0.6.9 -pr:h ohos-aarch64 -pr:b ohos-aarch64
```
