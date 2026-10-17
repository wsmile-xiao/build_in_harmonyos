# unarr

`unarr` 是一个用于读取 RAR / 7z / ZIP / TAR 归档的解压库（selmf/unarr），
被漫画阅读器（如 MComix/YACReader 等）作为归档读取后端使用。

- 上游仓库：https://github.com/selmf/unarr
- 许可证：LGPL-3.0-or-later

## 已适配版本

| 版本 | 状态 | 构建系统 | 依赖 | 说明 |
|------|------|---------|------|------|
| 1.1.1 | built | CMake | zlib/1.3.1、bzip2/1.0.8、liblzma/5.8.1（`USE_SYSTEM_*` 命中后链接平台库） | 首次适配；上游 20 项集成测试 + 1 项 crc32 单元测试（共 21 项）由 `cmake.test()` 执行，实测 21/21 通过；`test_package` 提供消费者测试 |

## 适配要点

1. 平台 CMake 为 4.x，上游 `cmake_minimum_required(VERSION 3.3)` 会被拒绝，配方用
   `cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 兼容。
2. 上游用 `find_package(ZLIB/BZip2/LibLZMA)` 并检查 `ZLIB::ZLIB` / `BZip2::BZip2` / `LibLZMA::LibLZMA`
   规范目标名，配方在 `CMakeDeps` 中用 `set_property(..., "cmake_target_name", ...)` 对齐；CONFIG 模式设置的
   混合大小写 `BZip2_FOUND`/`LibLZMA_FOUND` 由补丁归一化为上游检查的大写拼写（否则两个后端被静默跳过）。
3. 本配方默认构建静态库；补丁 `patches/0001-CMakeLists.txt.patch` 把上游对压缩库的
   `PRIVATE` 链接改为 `PUBLIC`，使静态库的消费方可以解析依赖符号。

详细过程见 `1.1.1/notes.md`。
