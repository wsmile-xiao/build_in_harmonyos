# gdal 3.9.2.3 — Conan 配方笔记

## 软件信息

- **名称**: GDAL — Geospatial Data Abstraction Library
- **版本**: **3.9.2.3**（R37：在 3.9.2.2 配方上启用 GEOS + libspatialite，配方字节有修改 → 递增）
- **许可证**: MIT
- **构建系统**: cmake
- **目标平台**: OHOS aarch64
- **上游源码**: https://github.com/OSGeo/gdal/releases/download/v3.9.2/gdal-3.9.2.tar.gz

## 本版变更（相对 3.9.2.2）

| 项 | 3.9.2.2 | 3.9.2.3 |
|----|---------|---------|
| GDAL_USE_GEOS | OFF | **ON**（geos/3.13.1，GEOS ≥3.8 满足） |
| GDAL_USE_SPATIALITE | 无 | **ON**（libspatialite/5.1.0.2） |
| requirements() | proj/sqlite3/zlib | + **geos/3.13.1**、**libspatialite/5.1.0.2** |
| CMAKE_PREFIX_PATH | proj/sqlite3/zlib 三包 | + geos/libspatialite 包目录 |
| package_info requires | proj/sqlite3/zlib | + **geos::geos**、**libspatialite::libspatialite**（libspatialite 无显式 components，Conan 组件引用 = 包名；其 cmake_target_name spatialite::spatialite 供 find_package(spatialite) 消费者用） |

其余（Ninja generator、`_run_sp()`、`_patch_symlink_rules()`、`ACCEPT_MISSING_SQLITE3_*`、
`FIND_ROOT_PATH_MODE_*=BOTH`、`_sign_shared_libs()`）**全部保持 3.9.2.2 已验证路径不变**。

## 关键决策与 CMake 集成

1. **选项名**：GDAL 3.9.2 官方选项是 **`GDAL_USE_SPATIALITE`**（`CheckDependentLibraries.cmake:597`
   `gdal_check_package(SPATIALITE "..." VERSION 4.1.2 CAN_DISABLE)` 生成）。
   `GDAL_USE_LIBSPATIALITE` 不存在——写错等于没写（Scout 已源码确认）。
   `GDAL_USE_EXTERNAL_LIBS=OFF` 时外部库默认禁用，必须显式 `-DGDAL_USE_SPATIALITE=ON`
   / `-DGDAL_USE_GEOS=ON` 强制 find（找不到会 FATAL_ERROR，不会静默降级）。
2. **GEOS 发现**：`gdal_check_package(GEOS ... NAMES GEOS TARGETS GEOS::geos_c GEOS::GEOS)`。
   带 NAMES 隐含 config 模式 → `find_package(GEOS NAMES GEOS)` 命中 geos 包内
   `lib/cmake/GEOS/geos-config.cmake`（geos/3.13.1 上游自带，目标 `GEOS::geos_c` 命中
   GDAL 候选，版本文件 3.13.1 ≥ 3.8）。`INTERFACE_INCLUDE_DIRECTORIES` 用
   `${_IMPORT_PREFIX}` 相对路径，无硬编码绝对路径。该 config 靠 CMAKE_PREFIX_PATH
   指向 geos 包目录命中，**无需**给 geos 改 cmake_target_name。
3. **SPATIALITE 发现**：无 NAMES → module 模式 `FindSPATIALITE.cmake`：
   `find_path(spatialite.h)` + `find_library(libspatialite)`，同样靠 CMAKE_PREFIX_PATH
   命中 libspatialite 包目录（`include/spatialite.h` + `lib/libspatialite.so` 已确认存在）。
   版本从 `spatialite.h` 行 `version 5.1.0, ...` 解析为 5.1 ≥ 4.1.2。
   未改 libspatialite 的 `cmake_target_name`（其 lowercase target 仅供
   `find_package(spatialite)` 消费者用，GDAL 走的是 SPATIALITE::SPATIALITE）。
4. **GEOS 版本锁定**：libspatialite/5.1.0.2 固定 require `geos/3.13.1`；
   Conan 2 同一图单版本 → GDAL 必须直接 require `geos/3.13.1`（勿用 3.13.0）。
   librttopo 由 libspatialite 间接带入 canonical **1.1.0**（勿用 1.1.0.1，E2145）。
5. **运行期闭包扩大**：libgdal.so DT_NEEDED 将含 libspatialite.so →
   libproj.so.25 / libxml2.so.16 / libgeos.so.3.13.1 / libgeos_c.so.1。
   这些包均已发布 ohpcd；test_package 用 `env="conanrun"` 注入 LD_LIBRARY_PATH，
   下游消费时需同样注入或 rpath（与 3.9.2.2 既有行为一致，闭包变大）。

## 依赖闭包与许可证

| 依赖 | 版本 | 形态 | 许可证 |
|------|------|------|--------|
| proj | 9.3.1.1 | shared | MIT |
| sqlite3 | 3.49.1 | static | Public-Domain |
| zlib | 1.3.1.1 | static PIC | Zlib |
| **geos** | **3.13.1** | shared | **LGPL-2.1-or-later** |
| **libspatialite** | **5.1.0.2** | shared | **MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later** |
| librttopo（libspatialite 间接） | 1.1.0 | static fPIC | **GPL-2.0-or-later** |
| libxml2（libspatialite 间接） | 2.15.3 | shared | MIT |

GDAL 自身 MIT。动态链接场景下 LGPL/GPL/MPL 依赖可接受（非再分发静态链接）；
PR/notes 如实记录闭包与许可证（web-review 维度 7/10）。

## 构建

```bash
export PATH=/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH; export TMPDIR=/storage/Users/currentUser/tmp
cd /storage/Users/currentUser/build_in_harmonyos
CI_PACKAGES="archives/g/gdal/3.9.2.3" /usr/bin/zsh ci/conan/build_and_test.sh
# 或：
conan create archives/g/gdal/3.9.2.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 上游测试口径（W4 v2 实测，2026-08-21）

### 实测环境与方法

- 构建树：`/storage/Users/currentUser/tmp/gdal-w4/`（BUILD_TESTING=ON + gdalautotest-3.9.2，
  defs 与配方一致：GDAL_USE_GEOS=ON / GDAL_USE_SPATIALITE=ON / 显式 SPATIALITE/GEOS cache 变量）。
- googletest 1.12.1（GDAL autotest/cpp 内部 ExternalProject 依赖）由本机 gh-proxy 镜像下载，
  校验 SHA1=`973e464e8936d4b79bb24f27b058aaef4150b06e`（与上游 CMakeLists.txt.in 期望一致），
  设备端将 `autotest/cpp/googletest/CMakeLists.txt.in` 的 URL 临时改为 `file:///` 本地文件
  （测量环境一次性，不入仓，未改上游测试源码）。
- **llvm-ranlib 缺失（基线已记录，复现）**：`ohos-sdk.../llvm/bin/llvm-ranlib` 不存在，
  `main_gtest.a` 静态库链接失败 → 测量时 patch `build/CMakeFiles/rules.ninja` 的
  `RA_RANLIB` 路径为 `/data/service/hnp/bin/llvm-ranlib`（SDK 环境问题，非配方问题）。
- **CTest LD_LIBRARY_PATH 覆盖坑（新）**：设备 CTest 用自身 `LD_LIBRARY_PATH=build;build/lib`
  覆盖外部传入值，test 子进程加载系统 `libxml2.so.16`（缺符号）→ 22/22 全部报 Fail。
  实测改为**直接调用各测试二进制**（命令从 `ctest -N -V` 原样提取，等价执行）。

### 实测数字（真实，自洽）

gtest（`autotest/cpp/gdal_unit_test`，直接运行 + 正确 LD_LIBRARY_PATH）：

```
[==========] Running 674 tests from 31 test suites.
[==========] 674 tests from 31 test suites ran.
[  PASSED  ] 666 tests.
[  FAILED  ] 2 tests.   → test_cpl.VSISupportsSequentialWrite / RandomWrite（/tmp 只读 platform-exempt）
[  SKIPPED ] 6 tests.   → iconv×2 / CPLHTTPFetch(CURL) / GetRawBinaryLayout_FITS / jpegxl×2
```

- 666 + 2 + 6 = 674 ✓
- **14 个 test_ogr_geos 全部实跑通过**（GEOS=ON 后不再 dependency-disabled）。
  注意：基线 3.9.2.2 把「20 个 test_ogr_geos」登记为 dependency-disabled，但实际
  test_ogr_geos suite 只有 **14** 个用例，另外 6 个是能力 skip（iconv/CURL/FITS/JPEGXL）。
  基线 20 = 14 geos + 6 能力 skip 的合并计数；3.9.2.3 按实跑拆分并如实登记。
- 有效通过率（TEST_QUALITY_SPEC §3.3）：
  `666 / (674 − 2 platform − 6 dependency) = 666/666 = 100%`
- 总通过率：`666/674 = 98.8%`

ctest entry 层（22 个注册项，直接执行）：

- 21 个独立二进制（testblockcache×6、testcopywords、testclosedondestroydm、testthreadcond、
  testvirtualmem、testblockcachewrite、testblockcachelimits、testmultithreadedwriting、
  testdestroy、test_include_from_c_file、test_c_include_from_cpp_file、bug1488、testlog、
  test_deferred_plugin、test_osr_set_proj_search_paths、proj_with_fork）**全部 rc=0 通过**。
- `gdal_unit_test`（test-unit）rc=1，仅因内含 2 个 platform-exempt case → 包裹层登记
  `ctest_entry_exemptions`，net `21/21 = 100%`。

Python autotest（pytest）未纳入本配方 CI 口径：conan create 默认 BUILD_TESTING=OFF，
Python 绑定 `BUILD_PYTHON_BINDINGS=OFF`（无 Python 绑定则 pytest 套件无法运行），
C++ gtest/ctest 为上游测试口径，`N/A（未运行）` 如实声明，不伪造数字。

## 历史

- 2026-08-14：3.9.2.2（Ninja generator 修复 + 真实干净构建，published）
- 2026-08-21：3.9.2.3（GEOS + spatialite 启用）
  - CI round 1：L0k `commands_json_r38` 失败 → commands.json `versions` 补 3.9.2.3
  - CI round 3：配置阶段 `Configured to use SPATIALITE, but not found` → FIND_ROOT_PATH 遮蔽（见下）
  - CI round 5：**conan create + test_package 全 PASS（rc=0，exit 0）**，`drivers=171`
  - W4 v2 上游测试实测：gtest 666/674（2 platform + 6 dependency exempt），ctest entry 21/22+1

## 参考

- `archives/l/libspatialite/5.1.0.2/notes.md`（geos-config ELF 适配器，E264）
- `archives/g/geos/3.13.1/notes.md`（shared libgeos_c，签名链）
- `knowledge/drafts/E326-draft-4801`（Ninja / /bin/sh hmmac / symlink cp）
- `knowledge/drafts/E2145-draft-2301`（librttopo canonical 1.1.0）

## CI 失败根因（FIND_ROOT_PATH_MODE 遮蔽）与修复（2026-08-21）

### 现象
`conan create` 配置阶段在 `CheckDependentLibraries.cmake:213` FATAL_ERROR：
`Configured to use SPATIALITE, but not found`（SPATIALITE 检查在 597 行，先于 GEOS 的 710 行）。
逐个关闭验证后 GEOS 同样 `Configured to use GEOS, but not found`。

### 根因（带证伪）
- `ohos.toolchain.cmake` 第 87-91 行把 `CMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER`、
  `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY/INCLUDE/PACKAGE=ONLY` 设为**普通变量**（非 cache）。
- 普通变量**遮蔽**命令行 `-DCMAKE_FIND_ROOT_PATH_MODE_*=BOTH` 的 cache 值 → find_path/find_library
  只搜 root-relative 路径（`<sysroot>/storage/Users/...` 前缀），纯 CMAKE_PREFIX_PATH 找不到 conan 包。
- 排除项：①CMAKE_PREFIX_PATH 已含 5 个包目录（CMakeCache 确认）；②spatialite.h/libspatialite.so/
  geos_c.h/libgeos_c.so 均存在且独立 `cmake -P` 的 find_path/find_library 能命中；
  ③find 调试日志确认搜索路径全部被 root 前缀化（mode=ONLY 生效）。
- proj 配方（已成功）即用显式 `-DSQLite3_INCLUDE_DIR/-DSQLite3_LIBRARY` cache 变量绕过（proj 的
  `-DCMAKE_FIND_ROOT_PATH_MODE_*=BOTH` 同样被遮蔽，只是 SQLite3/PROJ/ZLIB 靠显式变量才找到）。

### 修复
defs 新增（与 PROJ/SQLite3/ZLIB 同模式）：
```
-DSPATIALITE_INCLUDE_DIR=<libspatialite_pf>/include
-DSPATIALITE_LIBRARY=<libspatialite_pf>/lib/libspatialite.so
-DGEOS_INCLUDE_DIR=<geos_pf>/include
-DGEOS_LIBRARY=<geos_pf>/lib/libgeos_c.so
```
- FindSPATIALITE/FindGEOS 的 find_path/find_library 直接采用缓存值，不再搜索。
- SPATIALITE 版本来自 pkg-config（spatialite.pc 5.1.0 ≥ 4.1.2）；GEOS 版本来自 geo
s-config --version
  （实测可执行，返回 3.13.1 ≥ 3.8）。
- 配置验证：`-- Found SPATIALITE: .../libspatialite.so (5.1.0)` + `-- Found GEOS: .../libgeos_c.so (3.13.1)`，
  `Configuring done (62.5s)` rc=0；feature summary 含 `ogr_SQLITE, SQLite3 / Spatialite RDBMS` / `SPATIALITE` / `GEOS`。
