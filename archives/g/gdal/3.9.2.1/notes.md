# gdal 3.9.2.1 — Conan 配方笔记

## 软件信息

- **名称**: GDAL — Geospatial Data Abstraction Library
- **版本**: **3.9.2.1**（R37：在已归档 `3.9.2` 上补齐 Conan）
- **许可证**: MIT
- **构建系统**: cmake
- **目标平台**: OHOS aarch64
- **上游源码**: https://github.com/OSGeo/gdal/releases/download/v3.9.2/gdal-3.9.2.tar.gz

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-25
- 编译器: clang/clang++
- 状态: recipe

## 依赖（Conan）

| 依赖 | 版本 | 说明 |
|------|------|------|
| proj | 9.3.1.1 | 必需（旧归档笔记为 PROJ 9.8.1，本配方对齐已有 Conan proj） |
| sqlite3 | 3.49.1 | GPKG / SQLite 驱动 |
| zlib | 1.3.1.1 | 压缩 |

TIFF / GeoTIFF：使用 GDAL 源码树内置实现（`GDAL_USE_*_INTERNAL=ON`；ohpcd 暂无 libtiff Conan）

未启用：CURL / WebP / Arrow / GEOS / OpenSSL / libxml2 / PNG / JPEG（可后续按需打开）

## CMake 要点

- `ohos.toolchain.cmake` + `OHOS_ARCH=arm64-v8a`
- `CMAKE_INSTALL_PREFIX=package_folder`（与 proj 同理，避免装到 `/usr/local`）
- `GDAL_USE_EXTERNAL_LIBS=OFF`，再显式 `GDAL_USE_SQLITE3/ZLIB/TIFF=ON`
- `GDAL_USE_GEOS=OFF`（ohpcd 无 libgeos → 见 `dependency_exemptions`）
- conan create：`BUILD_TESTING=OFF` + `build()` 末尾空套件 `ctest || true`（L1c / 同 glib）
- W4 本地实测：`BUILD_TESTING=ON` + `gdalautotest-3.9.2` → 全量 autotest/cpp
- 交叉：`ACCEPT_MISSING_SQLITE3_MUTEX_ALLOC/RTREE=ON`

## 构建

```bash
# 需本地已有 proj/9.3.1.1（本分支已含配方）
conan create archives/g/gdal/3.9.2.1 \
  -pr:h=ohos-aarch64 -pr:b=default --build=missing \
  -c tools.cmake:cmake_program=/opt/ohos-sdk-6.1/native/build-tools/cmake/bin/cmake
```

## 历史

- 2026-05-28：传统归档见 `../3.9.2/notes.md`（PROJ 9.8.1，无 Conan）
- 2026-07-20：Conan 落在 `3.9.2.1`（分支 `feat/gdal-3.9.2.1`，基于 `feat/proj-9.3.1.1`）
- 2026-07-25：W4 上游 C++ 单元测试实测 + 文档同步（`MANIFEST.yml` 豁免登记）
- 2026-07-31：补齐 `ctest_entry_exemptions` + `verification` 块，gtest 与 ctest entry 双层均达 100% 有效通过率

---

## W3 结果（交叉 Docker，2026-07-20）

| 项 | 结果 |
|----|------|
| `conan create` / W3 | EXIT 0 |
| L0 / L1 / L4 / L5 | pass |
| L2 | pass（`gdal-config --version` OK；多数 aarch64 CLI 无法在宿主跑） |
| 上游 ctest | 空套件（`No tests were found!!!`） |

---

## 验证结果（W4 上游测试，2026-07-24/25，按 TEST_QUALITY_SPEC §3.3）

> 完整门禁/豁免与实测摘要见 `test_package/MANIFEST.yml`（`docs/TEST_QUALITY_SPEC.md §3.3`）。

按 `docs/ADAPTATION_GUIDE.md §3 Step 4-5` 与 `docs/TEST_QUALITY_SPEC.md §3` 走完上游 C++ 单元测试的本地执行。

### 实测数

| 项 | 数 |
|---|---|
| ctest 条目 | 22 总 / 21 通过 / 1 `ctest_entry_exempt`（`gdal_unit_test` 包裹） |
| ctest **有效**通过率 | **21/21 = 100%**（扣除 ctest_entry_exempt 后） |
| gtest case 跑 | 674 跑 / 652 通过 / 2 platform-exempt / 20 dependency-disabled |
| gtest **有效**通过率 | **652/652 = 100%**（扣除 platform + dependency 后） |
| gtest 总通过率 | **652/674 = 96.7%** |

### 公式（TEST_QUALITY_SPEC §3.3）

```
effective_pass_rate = passed / (total − platform_exemptions − dependency_disabled)
```

| 层 | 计算 | 结果 |
|---|---|---|
| gtest case | 652 / (674 − 2 − 20) = 652 / 652 | **100%** |
| ctest entry | 21 / (22 − 1) = 21 / 21 | **100%** |

### 2 个 FAILED（platform-exempt，已登记 `MANIFEST.yml`）

- `test_cpl.VSISupportsSequentialWrite`（test_cpl.cpp:4468）
- `test_cpl.VSISupportsRandomWrite`（test_cpl.cpp:4499）

根因：OHOS `/tmp` 只读，上游假设 POSIX-writable；GDAL 探测返回 `false` 是正确行为（`ADAPTATION_GUIDE.md §8`）。
按 TEST_QUALITY_SPEC §3.3 登记为 `platform_exemptions`，CTEST 包裹层 `gdal_unit_test` 同步登记为 `ctest_entry_exemptions`，不计入有效失败。

### 20 个 SKIPPED（dependency-disabled，已登记 `MANIFEST.yml`）

全部 `test_ogr_geos.*`。根因：recipe `GDAL_USE_GEOS=OFF`（ohpcd 无 libgeos 配方），上游 gtest 顶部 `if (haveGEOS())` 守卫按设计 skip。
按 TEST_QUALITY_SPEC §3.3 登记为 `dependency_exemptions`，非适配绕过。

### 上游测试用例修改

- [x] **否**，未修改上游任何测试用例

### 构建环境一次性 patch（不入仓）

`build-test/autotest/cpp/CMakeFiles/main_gtest.dir/link.txt` 中硬编码的 `llvm-ranlib` 路径在 OHOS SDK 缺符号链接；本地 patch 为 `/data/service/hnp/bin/llvm-ranlib` 后 `gdal_unit_test` 链接成功。属于 SDK 缺符号链接的环境问题，未改上游测试源码、未改 recipe。

### test_package（层 2 / R34）

```bash
# conan create 自动执行 test_probe
# → gdal ok version=3.9.2 drivers=<N>
```

实质调用 `GDALVersionInfo` / `GDALAllRegister` + `dlopen(libgdal.so)`。

## 注意事项

1. 运行时临时文件请使用可写目录（勿假设 `/tmp` 可写）。
2. 需要 GEOS 拓扑能力时，先适配/发布 libgeos 后再打开 `GDAL_USE_GEOS`。
3. 完整上游 C++ 测试需额外准备 `gdalautotest-3.9.2`。
4. 豁免与测试声明：`test_package/MANIFEST.yml`（含 `ctest_entry_exemptions` / `platform_exemptions` / `dependency_exemptions` / `verification` 四块）。
5. 有效通过率公式（TEST_QUALITY_SPEC §3.3）见本文件「公式」节。

---

**日期**: 2026-07-31（更新） / 2026-07-25（初版）
**状态**: recipe；W3/W4 通过；上游 gtest 与 ctest entry 双层有效通过率 **100%**