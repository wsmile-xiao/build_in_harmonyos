# DRAFT-geojson-cpp-0.5.1-cppinfo-requires-transitive-includes

> flat conanfile 配方缺失 cpp_info.requires 转发导致下游 CMakeDeps 不生成传递依赖配置、消费者编译缺头文件

## 问题特征（真实日志片段/标记）

- test_package 编译失败（conan create 内）：
  ```
  In file included from test_package.cpp:1:
  .../p/include/mapbox/geojson.hpp:3:10: fatal error: 'mapbox/geometry.hpp' file not found
  ```
- 同一失败前，`test_package/build/.../generators/` 目录只有 `geojson-cpp-*` 配置，
  没有 `mapbox-geometry-config.cmake` / `mapbox-variant-config.cmake`；
  `geojson-cpp-release-armv8-data.cmake` 中 `FIND_DEPENDENCY_NAMES` 为空列表。

## 根因

- geojson-cpp 配方 `requirements()` 已声明 `mapbox-geometry/2.0.3`、
  `mapbox-variant/1.2.0`、`rapidjson/1.1.0`（其公开头 geojson.hpp 无条件
  `#include <mapbox/geometry.hpp>`、`<mapbox/variant.hpp>`、rapidjson 头）。
- 但 `package_info()` 只设置了 `cpp_info.libs` 与 cmake 属性，未通过
  `self.cpp_info.requires` 把依赖目标转发给消费者。
- Conan 2 CMakeDeps 依据配方 `cpp_info.requires` 决定是否生成并
  `find_dependency()` 传递依赖配置；缺失时消费者侧完全拿不到依赖 include 路径。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. `archives/g/geojson-cpp/0.5.1/conanfile.py` `package_info()` 增加：
   ```python
   self.cpp_info.requires = [
       "mapbox-geometry::mapbox-geometry",
       "mapbox-variant::mapbox-variant",
       "rapidjson::rapidjson",
   ]
   ```
2. `test_package/CMakeLists.txt` 显式 find + link（与 mapbox-geometry 自身
   test_package 同模式）：
   ```cmake
   find_package(geojson-cpp REQUIRED)
   find_package(mapbox-geometry CONFIG REQUIRED)
   find_package(mapbox-variant CONFIG REQUIRED)
   find_package(RapidJSON CONFIG REQUIRED)
   target_link_libraries(test_geojson-cpp PRIVATE
       geojson-cpp::geojson-cpp mapbox::geometry mapbox::variant RapidJSON::RapidJSON)
   ```
3. `conan-verify` 通过：generators/ 出现三个依赖配置，FIND_DEPENDENCY_NAMES 非空。

## 禁止策略

- 禁止只加 libs 不加 requires 转发（消费者仍缺 include）。
- 禁止用 -I 硬编码 .conan2 缓存路径注入（不可复现、跨机失效）。
- 禁止删改消费者测试仅为了绕过头文件依赖。

## 与相近条目的边界（查重）

- 官方只读快照 E216（glib/libxml2 components INTERFACE_INCLUDE_DIRECTORIES 不传播）
  根因是 components 子目标 + cmake_file_name 大小写，非 flat cpp_info.requires 缺失；非等价。
- E499（运行时 LD_LIBRARY_PATH/runenv_info libdir 传播）为运行期，本条目为编译期 include 传播；非等价。
- E300/E447/E451/E473 均为特定 Find 模块/Clang/WebP 场景，非本模式。
- 本条目为 flat 配方 cpp_info.requires 转发通用模式，可跨库复用。

## 适用判断

- 适用：Conan 2 库配方，公开头无条件 include 第三方依赖头，下游 CMakeDeps 消费者
  报 `fatal error: '<dep>.hpp' file not found`，且 generators 目录缺传递依赖配置。
- 不适用：依赖仅为链接期（头不自包含）、或消费者已显式 requires 全部依赖的配方。
