# osm2pgrouting

## 简介

osm2pgrouting 把 OpenStreetMap 的 `.osm` XML 文件导入 PostgreSQL/PostGIS 数据库，
生成 pgRouting 做路径规划所需的拓扑表。它读取一份 `mapconfig*.xml` 描述哪些
OSM 标签对应哪些道路类型/代价，然后建表、导入结点与边、处理兴趣点。

- 上游: https://github.com/pgRouting/osm2pgrouting
- 许可证: GPL-2.0-or-later
- 平台: OpenHarmony PC (aarch64-linux-ohos), clang 15, libc++
- 构建: CMake
- 产物: `bin/osm2pgrouting` 与 `share/osm2pgrouting/{mapconfig.xml, mapconfig_for_cars.xml, mapconfig_for_bicycles.xml, mapconfig_for_pedestrian.xml, COPYING, README.md}`
- 版本状态: 3.0.0 = built（test_package 22 断言全过）

## OHOS 适配（3.0.0）

- 上游 tag 是 `v3.0.0`（`refs/tags/v3.0.0.tar.gz`）；不带 `v` 的
  `refs/tags/3.0.0.tar.gz` 是 404。
- 依赖：`libpq/18.1`、`libpqxx/8.0.1`、`expat/2.8.2.1`、`boost/1.84.0`。
  **不需要 libosmium** —— 上游虽然带了 `cmake/FindOsmium.cmake`，但 `src/` 与
  `include/` 里没有任何 osmium 引用，真正的 osmium 导入在独立辅助程序
  `tools/osmium/`，顶层 CMakeLists 不构建它。
- 唯一补丁 `patches/0001-CMakeLists.txt.patch` 做两件事：
  1. **依赖发现绕开描述构建主机的 bundled find 模块**。上游 `cmake/FindPostgreSQL.cmake`
     会去调 `pg_config` 并扫 `/usr/include/postgresql*`，`cmake/FindPQXX.cmake` 扫
     `/usr/include` —— 交叉构建下这会拿到宿主的头/库（或干脆找不到）。改为
     `find_package(libpq CONFIG)` / `find_package(libpqxx CONFIG)` /
     `find_package(EXPAT CONFIG)`，Boost 也用 `CONFIG` 模式以免被 CMake 内建
     FindBoost 截胡。
  2. **C++ 标准抬到 20**。上游按 “PQXX>=7 → C++17” 选标准，而 libpqxx 8.x 要求
     C++20；且 profile 钉的是 `cppstd=17`，CMakeLists 里的
     `set(CMAKE_CXX_STANDARD ...)` 会遮蔽 toolchain 的 cache 变量，所以补丁与配方
     `generate()` 里的 cppstd block 必须同时改。
- 运行期动态链接 `libexpat.so` + `libpq.so`，静态链接 `libpqxx.a`；测试脚本把
  `/system/lib64`（libc++_shared.so 所在）前插到 `LD_LIBRARY_PATH`，不覆盖
  VirtualRunEnv 提供的依赖目录。

设计细节见 `3.0.0/notes.md`；版本索引见 `manifest.yaml`；命令行声明见
`commands.json`（R38）。
