# osmcoastline 2.5.0 适配笔记

## 上游信息

- **仓库**: https://github.com/osmcode/osmcoastline
- **版本**: 2.5.0 (tag v2.5.0)
- **许可证**: GPL-3.0-or-later
- **构建系统**: CMake 3.10+
- **类型**: 命令行应用程序（非库）

## OHOS 适配策略

### 依赖处理

osmcoastline 的直接必需依赖中有两个在 ohpcd remote 不可用：
- **libosmium** (header-only): `archives/l/libosmium` 仅有 manifest/notes，无 conanfile.py
- **protozero** (header-only): 完全无 archive

本 recipe 采用"构建时下载并注入头文件路径"的策略：
1. 在 `build()` 中用 `conan.tools.files.get()` 下载 libosmium v2.20.0 和 protozero v1.7.1 的源码 tarball
2. 通过 CMake 缓存变量 `OSMIUM_INCLUDE_DIR` 和 `PROTOZERO_INCLUDE_DIR` 注入头文件路径
3. 上游 `cmake/FindOsmium.cmake` 的 `find_path()` 会优先检查缓存变量

### C++ 标准

- 上游默认 `CMAKE_CXX_STANDARD=14` (USE_CPP_VERSION=14)
- Conan profile 设置 `compiler.cppstd=17`
- Recipe 同步: `-DCMAKE_CXX_STANDARD=17 -DUSE_CPP_VERSION=17`

### LZ4 支持

- 上游默认 `WITH_LZ4=ON`
- lz4/1.10.0 在 ohpcd 可用
- Recipe 开启 LZ4 支持

## 测试

- 上游 CTest: 42 用例 (21 shell 脚本 × 2 SRID)
- 测试依赖 spatialite (设备端缺失), GDAL 运行时工具
- test_package: 运行 `osmcoastline/osmcoastline_filter/nodegrid2opl --version` 验证 3 个二进制可用（test.sh，conanrun 环境）

## 已知限制

1. libosmium 和 protozero 作为 vendored 依赖在构建时下载，非 Conan 标准做法
2. CTest 上游测试需要 spatialite 运行时，设备端缺失
3. GDAL minimal 驱动可能不含 osmcoastline 所需的全部 OGR vector 输出能力

## Web Review 修复记录（round-9，REVISE）

### L2 smoke test 非阻塞 warning 说明
- CI L2 冒烟测试在**无 conanrun 环境**下直接执行二进制，osmcoastline/osmcoastline_segments/osmcoastline_ways 的 --version/--help 失败（exit 126: Operation not permitted），nodegrid2opl/osmcoastline_filter 通过。
- 根因：这些二进制是动态链接 ELF，无 LD_LIBRARY_PATH 时加载依赖（libgdal.so.35 等）失败；L2 属 CI 脚本环境限制，**非阻塞**（L2_RESULT=pass）。
- 真实可用性由 test_package（conanrun 环境）验证：round-8/9 中 `osmcoastline --help`/`--version` 均成功输出（exit 0）。PR 报告如实声明该 L2 warning。

### 上游 CTest 42 用例未运行
- 上游 42 个 CTest 用例（21 脚本 × 2 SRID）依赖 spatialite 运行时与 GDAL 工具，设备端无 spatialite，本轮不运行。PR 报告写 N/A（未运行）。

### 依赖 vendored 说明（libosmium/protozero）
- ohpcd remote 与本地 cache 均无 libosmium/protozero Conan 制品；交付策略禁止一个分支含多库，故在 build() 内下载 header-only 源码注入 include 路径（有 sha256 校验）。若后续 remote 提供制品应迁移到标准 requires。

### 签名修复（关键）
- 设备 OHOS 内核按 .codesign fs-verity 哈希校验 ELF，`cmake --install` 会重写 RPATH 使哈希失效 → exec EPERM。package() 改用 shutil.copy2 字节级复制，签名保持有效（round-8 CI 实证 PASS）。

### 手动 cmake 命令行偏离说明
- 本 recipe 直接调用 cmake 命令而非 conan.tools.cmake.CMake helper：因需要注入大量依赖 include/lib 缓存变量（OHOS find_path/find_library 在 CMAKE_FIND_ROOT_PATH 下无法自动定位 Conan 包路径），CI 接受该方式（L0-L5 PASS）。


## 上游 CTest 集成（round-11）

### 依赖方案与 graph 解析结果

- 在 requirements() 中新增 libspatialite/5.1.0.2 和 sqlite3/3.49.1
- geos 从 3.13.0（静态 libgeos.a）升级到 3.13.1（共享 libgeos.so.3.13.1），因 mod_spatialite.so 的 NEEDED 链需要 libgeos.so.3.13.1 和 libgeos_c.so.1
- conan graph info 验证：依赖图成功解析，无版本冲突
  - geos/3.13.1 (shared=True) 满足 libspatialite 的 geos/3.13.Z 版本范围
  - libspatialite/5.1.0.2 (shared=True) 从 ohpcd 解析
  - 所有传递依赖（librttopo, libxml2, proj, sqlite3）均在图中

### conanfile.py 改动

1. requirements(): geos/3.13.0 -> geos/3.13.1, 新增 libspatialite/5.1.0.2 和 sqlite3/3.49.1
2. 新增 _ctest_bin() 方法：定位 ctest 二进制
3. 新增 _build_spatialite_shim() 方法：构造 spatialite CLI shim 脚本
   - 使用 sqlite3 CLI（来自 sqlite3 包的 bin/sqlite3）
   - 通过 .load mod_spatialite 加载扩展
   - 设置 LD_LIBRARY_PATH 包含 geos/proj/libxml2/libspatialite/sqlite3 的 lib 目录
   - cd 到 mod_spatialite.so 所在目录以便 dlopen 解析 NEEDED 链
4. 新增 _run_upstream_ctest() 方法：运行 ctest --test-dir build-ohos --output-on-failure
5. build() 末尾：cmake --build 后调用 shim 构建和 ctest 运行

### spatialite shim 实现验证

- shim 脚本在 build() 中通过 save() 生成，chmod 755
- 基础功能验证：spatialite_version() 返回 5.1.0，InitSpatialMetadata(1) 成功
- shim 被正确放置在 PATH 前端（ctest_env 中 PATH={shim_dir}:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:/usr/local/bin:/data/app/bin:/data/service/hnp/bin:/usr/bin:/vendor/bin）

### 实测通过/失败数

- **总用例数**: 42（21 脚本 × 2 SRID）
- **通过**: 2（test-usage-and-help-4326, test-usage-and-help-3857）
- **失败**: 40
- **通过率**: 2/42 = 4.8%

### 失败项证伪段

#### 根因：GDAL 3.9.2.1 OHOS 构建缺少 GEOS 和 libspatialite 支持

**证据**:
- gdal-driver-gpkg-4326.log: `ERROR 6: GEOS support not enabled.` -> `Error: No polygons created!`
- valid-island-from-one-way-4326.log: `ERROR 6: OGR was built without libspatialite support`
- gdal-driver-shapefile-4326.log: `ERROR 6: GEOS support not enabled.`
- invalid-direction-4326.log: `ERROR 6: OGR was built without libspatialite support`

**根因假设**: GDAL 3.9.2.1 的 ohpcd 制品在构建时未启用 GEOS 和 libspatialite 支持选项，导致：
1. 无法创建多边形几何（GEOS support not enabled）
2. 无法创建/写入 Spatialite 数据库（OGR built without libspatialite support）

**排除尝试**:
1. spatialite shim 是否工作？-> shim 基础功能已验证（spatialite_version() = 5.1.0），但 40 个失败用例中 osmcoastline 在创建数据库阶段就失败（OGR 无法创建 Spatialite DB），从未到达 shim 查询阶段
2. 是否是 LD_LIBRARY_PATH 问题？-> 不是。osmcoastline 本身能启动并处理 OSM 输入，失败发生在 GDAL/OGR 创建数据库时
3. 是否是 geos 版本问题？-> 不是。问题不在 geos 本身，而在 GDAL 编译时未链接 geos

**置信度**: 99%。GDAL 的 GEOS/spatialite 支持是编译时选项，ohpcd 上的预构建制品无法更改。40 个用例失败模式一致（GEOS support not enabled 或 OGR built without libspatialite support），且均发生在 osmcoastline -> GDAL/OGR 创建输出数据库阶段。

### 40 个失败用例分类

1. **GPKG/Shapefile 驱动测试**（4 用例）: gdal-driver-gpkg × 2, gdal-driver-shapefile × 2
   - 失败原因: GEOS support not enabled -> No polygons created
   
2. **默认 Spatialite 数据库测试**（36 用例）: 其余 18 个脚本 × 2 SRID
   - 失败原因: OGR built without libspatialite support -> failed to create dataset

### 结论

上游 42 个 CTest 用例已在 build() 中真实运行。2 个通过（usage-and-help），40 个因 GDAL 缺少 GEOS/libspatialite 支持而失败。此限制源于 ohpcd 上 gdal/3.9.2.1 的预构建配置，非 recipe 可控范围。


## 上游 CTest round-12（GDAL 3.9.2.3 合入后，42/42 全过）

- **依赖升级**: gdal/3.9.2.1 -> gdal/3.9.2.3（官方合入：`GDAL_USE_GEOS=ON` / `GDAL_USE_SPATIALITE=ON`，新增 libspatialite/5.1.0.2、geos/3.13.1 依赖）。
- **实测结果**: ctest --test-dir build-ohos → `100% tests passed, 0 tests failed out of 42`（round-12 CI 日志实证）。
- **结论**: round-11 的 40 个失败用例（GEOS support not enabled / OGR built without libspatialite support）全部消除；42/42 上游用例真实通过，PR 报告不再写 N/A。
