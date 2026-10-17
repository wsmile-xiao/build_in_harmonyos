# libosmscout 2024.06.02.1 测试报告

> **项目**: libosmscout
> **测试日期**: 2026-09-29
> **测试环境**: HarmonyOS 6.0 / OpenHarmony PC aarch64（clang 15.0.4, libc++, cmake 4.1.2, ninja）
> **测试类型**: 官方测试套件（上流 CTest）+ 消费者端到端用例（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 69 | 100% |
| 通过 (PASS) | 69 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（69/69）**

消费者端到端用例（`test_package/test_libosmscout.cpp`）：

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总断言数 | 39 | 100% |
| 通过 (PASS) | 39 | 100% |
| 失败 (FAIL) | 0 | 0% |

**消费者用例通过率**: ✅ **100%（39/39）**

---

## 二、测试结论

### 2.1 总体评价

✅ **上游官方测试套件 69/69 全通过，消费者端到端用例 39/39 全通过**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游无条件链接 `OpenMP::OpenMP_CXX` | 导入库被 `-fopenmp` 编译，消费者链接缺 `__kmpc_*` | 🟡 已在配方中关闭 OpenMP 探测解决 |
| 依赖共享库以符号链接安装 | OHOS 加载器拒载 `libxml2.so.16` | 🟡 已在 test_package 中实体化依赖 .so 解决 |

### 2.3 可用功能清单

```
✅ 核心库 libosmscout：OSM 数据模型、数值/几何、Database、路由、POI/位置检索、投影
✅ 地图库 libosmscout_map：样式表编译（.ost/.oss）、绘制抽象、标签布局、MapService 切片
✅ SVG 后端 libosmscout_map_svg：MapPainterSVG 输出 SVG 文档
✅ 导入库 libosmscout_import：经 libxml2 读 OSM XML，完整索引生成 + router 建库
✅ GPX 库 libosmscout_gpx：经 libxml2 解析 GPX 轨迹
✅ 客户端库 libosmscout_client：MapDirectory 等数据库/地图目录抽象
⚠️ 文本检索索引（Marisa）：未启用（OHOS 无 marisa 制品），TextLookupTest 在 configure 阶段不注册
❌ Qt / agg / cairo / OpenGL / Pango 绘制后端：未启用（依赖不可得）
❌ 命令行工具（Import / DumpData / PublicTransportMap / OSMScout2 / StyleEditor）与 Demos：未启用
❌ OpenMP 多线程导入：关闭（见 2.4）
```

### 2.4 已知限制

1. 未依赖 Marisa，故上游 `TextLookupTest` 在 configure 阶段即不被注册（上游自身行为，`Skip TextLookupTest test, Marisa library is missing.`），不计入跳过。
2. 上游 `libosmscout-import` 只按 target 是否存在就 `target_link_libraries(... OpenMP::OpenMP_CXX)`，`OSMSCOUT_BUILD_WITH_OPENMP=OFF` 不足以关闭编译期 `-fopenmp`；本配方额外用 `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON` 才能真正关闭，导入流水线为单线程（`#pragma omp critical/parallel for` 编译为空操作，逻辑等价）。
3. 依赖 `libxml2/2.15.3.1` 为共享库，其包内以 `libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3` 符号链接链安装；OHOS 存储侧加载器拒载符号链接，消费者侧需将该 .so 实体化（test_package 已内置该处理），属环境约束而非配方缺陷。
4. TBB / `std::execution`（`HAVE_STD_EXECUTION`）探测为负，导入不启用并行执行策略。

---

## 三、测试详情

### 3.1 通过的测试（上游，节选分组）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 单元测试 40+ 项（AccessParse / Bearing / GeoBox / Geometry / EncodeNumber / StringUtils / TimeParse / TransPolygon / ScreenBox / WorkQueue / Thread / Signal / …） | 核心几何、字符串、号码编解码、异步与工作队列 | ✅ PASS |
| CheckStyleSheet-{boundaries,cycle,motorways,public-transport,railways,standard,winter-sports} | map.ost 与 7 个 .oss 样式表交叉校验 | ✅ PASS（7/7） |
| PerformanceTest-{none,noop}-{7 个样式表} | 无操作绘制器基准，样式解析 + 标签布局实跑 | ✅ PASS（14/14） |
| LocationLookupTest | 自行驱动 Importer 用 XML/OLT 建库，再用 Database + LocationService 检索行政区/邮编/街道/门牌 | ✅ PASS |
| MultiDBRouting / ThreadedDatabase / ReaderScannerPerformance / CoordinateEncoding / WaterIndex / MapRotate / FileScannerWriter / GeoCoordParse / MercatorProjectionTest | 基于 Tests/data/testregion 预置库的数据库级集成测试 | ✅ PASS |
| HeaderCheck / OSTAndOSSCheck | 头文件自包含性与样式表语法 | ✅ PASS |
| CachePerformance / NumberSetPerformance / CachePerformance | 性能类用例（实测 0.03–30 s） | ✅ PASS |

完整日志：`ctest --output-on-failure` 输出 `100% tests passed, 0 tests failed out of 69`，`Total Test time (real) = 31.94 sec`。

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| — | — | 无 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| — | 无（TextLookupTest 属未注册，不属于跳过） |

### 3.4 消费者端到端用例分组

| 阶段 | 覆盖组件 | 断言数 | 结果 |
|------|----------|--------|------|
| 1 核心几何 / 数字编解码 | OSMScout::OSMScout | 11 | ✅ PASS |
| 2 GPX 解析（libxml2） | OSMScout::GPX | 4 | ✅ PASS |
| 3 OSM XML 导入建库（libxml2 + 导入流水线） | OSMScout::Import | 2 | ✅ PASS |
| 4 数据库打开 + 客户端目录校验 | OSMScout::OSMScout / Client | 8 | ✅ PASS |
| 5 包内样式表编译 | OSMScout::Map | 3 | ✅ PASS |
| 6 切片检索 + SVG 渲染 | OSMScout::Map / MapSVG | 11 | ✅ PASS |
| **合计** | 6 个库全部 | **39** | ✅ **39/39** |

---

## 四、关键问题分析

### 问题1: 消费者链接导入库时报 `__kmpc_*` 未定义

**现象**：
```
ld.lld: error: undefined symbol: __kmpc_end_critical
>>> referenced by GenWayWayDat.cpp.obj in archive .../libosmscout_import.a
ld.lld: error: undefined symbol: __kmpc_for_static_init_8
```

**根因分析**：
上游 `libosmscout-import/CMakeLists.txt` 中
`if(TARGET OpenMP::OpenMP_CXX) target_link_libraries(OSMScoutImport OpenMP::OpenMP_CXX) endif()`
**只判断 target 是否存在，不判断 `OSMSCOUT_BUILD_WITH_OPENMP`**。OHOS clang SDK 自带
`libomp`/`omp.h`，于是 `find_package(OpenMP QUIET)` 成功 → 导入库以 `-fopenmp` 编译（源码里
`#pragma omp critical/parallel for` 无 `#ifdef _OPENMP` 守卫）→ 静态归档里留下 `__kmpc_*`
未定义符号，而 Conan 的 `package_info()` 并不声明 libomp，消费者链接必然失败。

**解决方案**：
`generate()` 中除 `OSMSCOUT_BUILD_WITH_OPENMP=OFF` 外，追加
`CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON`，令 `find_package(OpenMP)` 直接返回未找到、目标不存在，
`-fopenmp` 不再注入。`#pragma omp critical` 在无 OpenMP 时是空操作，语义等价。

### 问题2: 消费者运行时 `Error loading shared library libxml2.so.16`（errno 为空）

**现象**：
```
Error loading shared library libxml2.so.16: (needed by .../test_libosmscout)
Error relocating .../test_libosmscout: xmlCreatePushParserCtxt: symbol not found
```

**根因分析**：
`libxml2/2.15.3.1` 包内共享库以符号链接链安装：
`libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3`。OHOS 存储侧动态加载器**拒载符号链接**
（失败时 errno 被吞为空）。对照实验确证：把同一个实体文件 `cp -L` 成普通文件挂到
`LD_LIBRARY_PATH` 即正常运行；而在自建目录里放一个指向该文件的**符号链接**则复现同样失败。

**解决方案**：
`test_package` 的 `generate()` 遍历依赖的 `cpp_info.libdirs`，用 `shutil.copy2`（跟随符号链接）
把共享库实体化到 `<build>/realdep_libs`，并以 `Environment().prepend_path("LD_LIBRARY_PATH", ...)`
`.vars(self, scope="run")` 保存为运行环境；`test()` 用 `env="conanrun"` 执行 ctest 与消费者二进制
（`LD_LIBRARY_PATH` 优先于 `DT_RUNPATH`，故实体目录必然命中）。

---

## 五、测试环境

```
OS:            HarmonyOS 6.0 (uname -s = HarmonyOS), aarch64
Compiler:      clang 15.0.4 (/data/service/hnp/bin/clang++), -stdlib=libc++
CMake:         4.1.2, generator: Unix Makefiles（conan 默认）
Conan:         2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64
Build:         BUILD_SHARED_LIBS=OFF（静态库），build_type=Release，C++17
Dependencies:  libxml2/2.15.3.1
Configure:     -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON
               -DOSMSCOUT_BUILD_WITH_OPENMP=OFF -DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON
               -DOSMSCOUT_BUILD_{IMPORT,GPX,CLIENT,TESTS,MAP_SVG}=ON
               -DOSMSCOUT_BUILD_{MAP_AGG,MAP_CAIRO,MAP_OPENGL,MAP_QT,CLIENT_QT,DEMOS,TOOL_*}=OFF
```

---

*报告生成时间: 2026-09-29*
