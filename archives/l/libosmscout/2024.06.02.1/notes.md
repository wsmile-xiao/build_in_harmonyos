# libosmscout 2024.06.02.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists，最低要求 3.20；实测 cmake 4.1.2）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK，-stdlib=libc++，C++17）
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（os=OHOS 6.0，arch=armv8）
- 状态: built（静态库，BUILD_SHARED_LIBS=OFF）

## 编译步骤

上游 2024.06.02.1 官方 release tarball（内部库版本 1.1.1）解包后按如下组件切分构建：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 `generate()` 注入的关键 CMake 变量：

- `BUILD_SHARED_LIBS=OFF`（静态库）
- `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`（让 `find_package(LibXml2 QUIET)` 命中 Conan 配置）
- 启用组件：`OSMSCOUT_BUILD_IMPORT / GPX / CLIENT / TESTS / MAP_SVG`
- 关闭组件：`MAP_AGG / MAP_CAIRO / MAP_OPENGL / MAP_QT / CLIENT_QT / DEMOS /
  TOOL_IMPORT / TOOL_DUMPDATA / TOOL_PUBLICTRANSPORTMAP / TOOL_OSMSCOUT2 /
  TOOL_OSMSCOUTOPENGL / TOOL_STYLEEDITOR / DOC_API / WEBPAGE / EXTERN_MATLAB`
- `OSMSCOUT_BUILD_WITH_OPENMP=OFF` **且** `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON`
- 唯一外部依赖：`libxml2/2.15.3.1`

`build()` 末尾执行上游 CTest 全套（`ctest --output-on-failure --timeout 900 -j4`），
`package()` 中删除 `share/osmscout/tests` 与 `share/osmscout/demos`（上游把测试与基准
可执行文件装到这两个目录，未签名的 OHOS 可执行文件对消费者无意义）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者链接 `libosmscout_import.a` 报 `undefined symbol: __kmpc_*`（`-fopenmp` 产物） | 上游 `libosmscout-import/CMakeLists.txt` 只按 `if(TARGET OpenMP::OpenMP_CXX)` 无条件链接 OpenMP，不看 `OSMSCOUT_BUILD_WITH_OPENMP`；OHOS clang SDK 自带 libomp 使 `find_package(OpenMP QUIET)` 成功 → 即便选项为 OFF 仍以 `-fopenmp` 编译（源码 `#pragma omp` 无 `#ifdef _OPENMP` 守卫），而 `package_info()` 不声明 libomp | 追加 `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON` 让目标不存在；无 OpenMP 时 `#pragma omp critical` 为空操作，语义等价 |
| 2 | 消费者运行报 `Error loading shared library libxml2.so.16`（errno 为空） | libxml2 包内共享库以 `libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3` 符号链接链安装，OHOS 存储侧加载器拒载符号链接；对照实验：同一实体文件 `cp -L` 成普通文件即可，软链接版本必败 | test_package `generate()` 遍历依赖 `cpp_info.libdirs`，`shutil.copy2`（跟随符号链接）实体化到 `<build>/realdep_libs`，`Environment().prepend_path("LD_LIBRARY_PATH", …)` 保存为 run 作用域，`test()` 以 `env="conanrun"` 运行 |
| 3 | 每次 configure 刷出 `System is unknown to cmake, create: Platform/HarmonyOS` | cmake 无 `Platform/HarmonyOS.cmake`，`uname -s` = HarmonyOS 无法匹配已知系统 | 仅告警，配置/编译/运行全部正常，无需覆盖 `CMAKE_SYSTEM_NAME`，也无需绕开 conan_toolchain |
| 4 | `cmake.test()` 报 `No rule to make target 'test'` | test_package 的 CMakeLists 用了 `add_test` 但未 `enable_testing()` | CMakeLists 增加 `enable_testing()` |
| 5 | 包内混入 `share/osmscout/tests/*`、`share/osmscout/demos/PerformanceTest` | 上游 `osmscout_test_project` 宏 `install(TARGETS … RUNTIME DESTINATION share/osmscout/tests)`，基准走 demos 目录 | `package()` 中递归删除这两个目录 |
| 6 | Marisa / protobuf / Qt / cairo 等可选依赖在 OHOS 不可得 | 制品仓无对应 OHOS 包 | 上游全部用 `find_package(... QUIET)` 探测并静默降级，无需补丁；文本检索索引与 Qt/agg/cairo 后端相应关闭 |

## 源码修改

无补丁。全部适配通过配方侧 CMake 变量与 `package()` 裁剪完成，上游源码保持原样
（`patches_applied: []`，`conandata.yml` 的 `patches` 为空）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxml2 | 2.15.3.1 | 唯一外部依赖；启用 OSM XML 读入器（PreprocessOSM）与 GPX 读入器 |
| Marisa | 未使用 | 制品仓无 OHOS 包 → 文本检索索引关闭，上游 `TextLookupTest` configure 阶段不注册 |
| protobuf | 未使用 | 未选用 → PBF 读入器关闭（`PreprocessPBF` 不编译） |
| Qt6 / libagg / cairo / Pango / GLEW / GLM | 未使用 | 对应绘制后端与命令行工具关闭 |
| TBB / OpenMP | 未使用 | `HAVE_STD_EXECUTION` 探测为负；OpenMP 探测被显式禁用 |

## 验证结果

```bash
# 上游官方测试套件（在 conanfile.py 的 build() 内执行）
$ ctest --output-on-failure --timeout 900 -j4
100% tests passed, 0 tests failed out of 69
Total Test time (real) = 31.94 sec

# 消费者端到端用例（test_package，conanrun 环境）
$ ./test_libosmscout
[stage 1] core geometry and number codec            -> 11 checks
[stage 2] GPX parsing through libxml2               ->  4 checks
[stage 3] OSM XML import through libxml2            ->  2 checks
[stage 4] database open and client directory check  ->  8 checks
[stage 5] packaged style sheet compilation          ->  3 checks
[stage 6] tile lookup and SVG rendering             -> 11 checks
checks: 39  failures: 0
RESULT: PASSED (39/39)

# 消费者用例的实质动作（非空壳断言）
#   内联 9 节点 / 4 条 way 的 OSM XML -> Importer 建库（含 bicycle/foot/car router）
#   -> Database::Open -> 类型配置含 highway_primary / building
#   -> 客户端 MapDirectory 判定目录合法 -> 编译包内 standard.oss（零错误）
#   -> MapService 切片检索 4 个切片 -> MapData 取到 1 节点 2 道路
#   -> MapPainterSVG 渲染 1277 字节 SVG 文档
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libosmscout.a | 6.02 MB | 核心库（数据模型、数据库、路由、位置检索、投影） |
| lib/libosmscout_import.a | 3.78 MB | 导入库（OSM XML 经 libxml2 + 全部索引生成） |
| lib/libosmscout_map.a | 2.55 MB | 地图库（样式表编译、绘制抽象、切片服务） |
| lib/libosmscout_client.a | 1.57 MB | 客户端库（数据库/地图目录抽象） |
| lib/libosmscout_gpx.a | 500 KB | GPX 库（经 libxml2） |
| lib/libosmscout_map_svg.a | 226 KB | SVG 绘制后端 |
| lib/libosmscout_test.a | 203 KB | 上游测试辅助库 |
| include/osmscout*/**/*.h | 284 个 | 公开头文件 |
| lib/pkgconfig/*.pc | 7 个 | 上游 pkg-config 元数据 |
| share/osmscout/stylesheets/ | 25 个文件 | `*.ost` 类型配置（map.ost 等 4 个）与 `*.oss` 样式表（含 include/ 21 个），渲染期必需数据 |

## 注意事项

1. **OpenMP**：仅设 `OSMSCOUT_BUILD_WITH_OPENMP=OFF` **不够**，必须同时
   `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON`，否则导入库带 `__kmpc_*` 未定义符号，任何消费者
   都会链接失败。这是本包最容易被漏掉的坑。
2. **依赖共享库的符号链接**：libxml2 以符号链接链安装，OHOS 加载器拒载；任何依赖它的
   消费者（不只是本 test_package）在本环境下都需要把 `.so` 实体化后放进 `LD_LIBRARY_PATH`。
3. **静态库切分**：`osmscout` 与 `osmscout_map` 之间存在依赖（`map` → `osmscout`），
   `client` → `osmscout + map`，`import` → `osmscout (+ libxml2)`，`test` → `osmscout + import`；
   Conan 的 component 依赖已按此声明，消费者只需
   `find_package(libosmscout)` 后链接 `OSMScout::OSMScout`/`OSMScout::Map` 等上游同名目标。
4. **样式表路径**：上游自带的 `libosmscoutConfig.cmake` 里 `LIBOSMSCOUT_STYLES_DIR` 指向
   `<prefix>/share/stylesheets`，而实际安装位置是 `<prefix>/share/osmscout/stylesheets`
   （上游笔误，非本包问题）。本配方的 `package_info()` 暴露自定义属性
   `libosmscout:stylesheets` 给出真实相对路径 `share/osmscout/stylesheets`。
5. **测试可执行文件不入包**：上游把 69 个测试与基准程序装进 `share/osmscout/tests|demos`，
   本配方在 `package()` 中删除，保证这是纯库包（无需软件级 `commands.json`）。

## 对话记录

### 对话 #1 — 2026-09-29
**操作**: 适配 libosmscout 2024.06.02.1 到 HarmonyOS PC（aarch64），建立 `feat/libosmscout-2024.06.02.1` 分支与 worktree
**结果**: ✅ 上游 CTest 套件 69/69 通过；消费者端到端用例 39/39 断言通过；conan-verify G0–G4 + L2/L4/L5 全部 PASS；W3 本地 CI 通过；归档状态 `built`
**发现的问题**:
  - `conan create` 首次配置即报 `System is unknown to cmake, create: Platform/HarmonyOS`——实测为原生构建（build==host==OHOS）下的无害告警，无需覆盖 `CMAKE_SYSTEM_NAME`（已沉淀草稿 E545）
  - `libosmscout-import` 被 `OpenMP::OpenMP_CXX` 以 `-fopenmp` 编译（上游只判 target 存在，不看 `OSMSCOUT_BUILD_WITH_OPENMP`），消费者链接缺 `__kmpc_*`；须追加 `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON`（草稿 E429）
  - 依赖包 `libxml2/2.15.3.1` 以 `libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3` 符号链接链安装，OHOS 加载器拒载（errno 为空）；test_package 需把依赖 .so 实体化（草稿 E479）
  - test_package 的 `cmake.test()` 报 `No rule to make target 'test'`：CMakeLists 缺 `enable_testing()`
  - 上游测试宏把 69 个测试/基准可执行文件装进 `share/osmscout/tests|demos`，须在 `package()` 中裁剪（草稿 E546）
  - `finish` 首轮 W3 因未先 commit 版本目录而回落 `junk_check` full 模式，误扫到 `archives/c/cloog`、`archives/k/kics`、`archives/l/libbfio`、`archives/t/thc` 的遗留隐藏文件（均属 origin/main，非本次改动）；commit 后恢复增量模式即通过
  - `finish` 的 W3 EXIT 还原逻辑把 `conandata.yml` 写回 `gh-proxy.com` 镜像多值列表，并留下 `conandata.yml.ghfast-bak`/`conandata.yml.orig`；提交前已手工逐行核对 diff 并还原为官方单值 URL、删除备份文件
**当前状态**: 已完成
**遗留问题**: 文本检索索引（Marisa）与 Qt/agg/cairo/OpenGL 绘制后端在 OHOS 不可得，相应功能不可用（与上游缺依赖时的默认降级一致）；`E092` 的处方不适用于原生构建，已沉淀草稿 E545 供主编复核

---

**编译结束**: 2026-09-29 19:31
**最终状态**: built
