# osmium-tool

> osmium-tool（`osmium`）—— 处理 OpenStreetMap 数据的多功能命令行工具，基于 libosmium。

## 简介

osmium-tool 提供 `osmium` 命令，内置 23 个子命令（cat、extract、export、diff、
merge、sort、renumber、tags-filter、tags-count、fileinfo、getid、getparents、
time-filter、changeset-filter、check-refs、apply-changes、derive-changes、
removeid、show、create-locations-index、query-locations-index、
add-locations-to-ways、merge-changes），支持 OSM XML / PBF / OPL 三种格式的读写，
PBF 支持 zlib 与 lz4 压缩。

## OHOS 适配要点

- CMake 构建，`package_type = "application"`，产物为 `bin/osmium`。
- **libosmium / protozero 采用 vendored（构建时下载 header-only 源码）**：
  上游 `cmake/FindOsmium.cmake` 要求 Osmium >= 2.23.1，而制品仓只有
  libosmium/2.23.0；且 2.23.1 回退了 2.21.0 的对象排序改动
  （`object_order_type_id_reverse_version` 不再考虑 visible），直接影响
  `osmium sort/apply-changes/merge-changes` 的输出结果，2.23.0 头文件会产出
  错误结果。故按官方 tarball（固定 sha256）下载 libosmium v2.23.1 与
  protozero v1.8.2，通过 `OSMIUM_INCLUDE_DIR` / `PROTOZERO_INCLUDE_DIR`
  注入上游 find 模块。
- 上游自带模块式 find 模块只认旧式大写变量；Conan 工具链默认
  `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，因此需要在配方 `generate()` 中补齐
  `ZLIB_LIBRARIES` / `EXPAT_LIBRARIES` / `BZIP2_LIBRARIES` /
  `LZ4_INCLUDE_DIRS` / `LZ4_LIBRARIES` 等变量。
- CMake 4.x 的 `FindBZip2` 只设置 `BZip2_FOUND`，上游仍检查 `BZIP2_FOUND`
  → 补丁 `0001-cmake4-findbzip2-compat.patch` 增加兼容别名。
- `cmake --install` 会重写 RPATH 破坏 OHOS `.codesign` 哈希，故 `package()`
  按字节复制构建树中的可执行文件（保持签名有效）。

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| boost | 1.90.0.4 | ohpcd（program_options）|
| nlohmann-json | 3.11.2 | ohpcd |
| zlib | 1.3.1.1.1 | ohpcd |
| bzip2 | 1.0.8 | ohpcd |
| expat | 2.8.2.1 | ohpcd（共享库）|
| lz4 | 1.10.0 | ohpcd |
| libosmium | v2.23.1 | vendored（header-only）|
| protozero | v1.8.2 | vendored（header-only）|

## 测试

- 上游 CTest：375 个用例（`ctest -N` 实测）全部执行通过 375/375。
- 消费者验证：`test_package/test.sh` 18 项断言（版本契约 / 帮助 / XML→OPL /
  XML→PBF + fileinfo / PBF→OPL 往返一致 / tags-filter）全部通过。

## 参考

- [官网](https://osmcode.org/osmium-tool/)
- [源码仓库](https://github.com/osmcode/osmium-tool)
