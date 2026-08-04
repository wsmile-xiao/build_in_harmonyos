# librsync

## 简介

librsync provides binary delta encoding based on the rsync rolling checksum algorithm.

## OHOS 适配

- 构建系统: CMake
- 打包内容: static `rsync` library, public `librsync.h` headers, and `rdiff` CLI
- `rdiff` CLI 已启用，消费已发布的 Conan 依赖 `popt/1.16`

## 依赖

- 必需 Conan 依赖: `popt/1.16`，从 `ohpcd` 远端解析，已验证
  recipe revision `cca44e0c65c2ff043d329f27a068a956`
- 构建/测试工具依赖: `perl/5.42.2`
- 上游可选压缩/哈希依赖 `zlib`、`bzip2`、`libb2` 未启用

依赖解析证据见 `2.3.4/reports/dependency-resolution.md`。

## 功能验证

- upstream CTest 在 `conan create` 的 `build()` 阶段执行：15 个测试注册并全部通过
- `test_package` 编译并运行消费者 C 程序，验证 `find_package(librsync)`、链接和核心 API

## 参考

- https://github.com/librsync/librsync
