# libdetour 1.6.0 适配笔记

## 上游信息

- 名称：libdetour（Detour 运行时导航网格查询库）
- 上游版本：v1.6.0
- 上游仓库：https://github.com/recastnavigation/recastnavigation
- 源码归档：https://github.com/recastnavigation/recastnavigation/archive/refs/tags/v1.6.0.tar.gz
- SHA-256：d48ca0121962fa0639502c0f56c4e3ae72f98e55d88727225444f500775c0074
- 许可证：Zlib
- 关系说明：本包与 archives/r/recastnavigation/1.6.0 同源，但为 Detour 拆分包，
  只构建交付 Detour 运行时库（Alpine 社区同样将该上游拆分为 libDetour、
  libDetourCrowd、libDetourTileCache、libRecast 等子包）。recastnavigation 包
  交付 5 个组件且关闭了上游测试；本包聚焦 Detour 并完整运行上游测试。

## 编译环境

- 构建系统：cmake
- 编译器：clang/clang++（HarmonyOS PC aarch64 真机，与官方 CI 同源）
- 依赖：无外部依赖（Detour 仅需 C++98 编译器）

## 编译步骤

1. `get()` 解包官方 v1.6.0 归档并校验 SHA-256。
2. `generate()` 配置 CMakeToolchain：
   - `RECASTNAVIGATION_DEMO=OFF`、`RECASTNAVIGATION_EXAMPLES=OFF`
    （Demo 依赖 OpenGL/SDL2，非运行时必需）
   - `RECASTNAVIGATION_TESTS=ON`（构建 Catch2 上游测试套件）
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 3.1，兼容新版 CMake）
3. `build()` 编译全量目标后运行 `ctest --output-on-failure`，
   再运行 Tests 二进制（`--reporter compact`）解析 Catch2 结果，
   发出 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `upstream_test_result.json`。
4. `package()` 执行 `cmake install` 后裁剪为仅 Detour：
   删除 Recast/DetourCrowd/DetourTileCache/DebugUtils 库文件，
   仅保留 `Detour*.h` 与 `version.h`，移除 pkgconfig/cmake/share，
   并将上游测试证据拷贝到 `res/upstream_test_result.json`。
5. `test_package` 链接 `libdetour::libdetour`，运行 3 个真实 API 检查，
   发出 `HMBS_TEST_PACKAGE_RESULT` 并重放上游测试证据。

## 上游测试审计

- 测试框架：Catch2（源码内 Tests/Contrib 捆绑，无需外部 Catch2）。
- 注册方式：Tests/CMakeLists.txt `add_test(Tests Tests)`，ctest 层面 1 个测试项。
- 用例计数（非基准测试）：
  - Tests/Detour/Tests_Detour.cpp：1 个 TEST_CASE（dtRandomPointInConvexPoly）
  - Tests/Recast/Tests_Recast.cpp：29 个 TEST_CASE（rcSwap、rcMin、rcMax、
    rcAbs、rcSqr、rcClamp、rcSqrt、rcVcross、rcVdot、rcVmad、rcVadd、rcVsub、
    rcVmin、rcVmax、rcVcopy、rcVdist、rcVdistSqr、rcVnormalize、rcCalcBounds、
    rcCalcGridSize、rcCreateHeightfield、rcMarkWalkableTriangles、
    rcClearUnwalkableTriangles、rcAddSpan、rcRasterizeTriangle、
    rcRasterizeTriangle overlapping、rcRasterizeTriangle smaller、
    rcRasterizeTriangles、rcVector）
  - 合计 30 个；BM() 基准测试仅在 `__unix__` 且 `_POSIX_TIMERS` 可用时编译，
    不计入本次审计基数，真机实际数字以 `Tests --reporter compact` 解析为准。
- 证伪说明：不只看 ctest 退出码，配方解析 Catch2 输出中的
  `All tests passed (N assertions in M test cases)`，M 必须大于 0 且与
  TEST_CASE 审计基数一致；失败或 M 为 0 时构建直接失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层默认开启 Demo/Tests | 上游默认 RECASTNAVIGATION_DEMO=ON/TESTS=ON | DEMO/EXAMPLES 显式 OFF，TESTS 显式 ON，仅关闭重型示例依赖 |
| 2 | 上游要求 CMake 3.1 与新版 CMake 不兼容 | CMake 4 移除了 <3.5 兼容 | generate 与 configure 均设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | Tests 目标需要 Recast 但本包只交付 Detour | 上游测试链接 Recast+Detour | 构建期全量编译运行测试，打包期裁剪为仅 Detour |
| 4 | 上游安装产物包含 5 个库的 cmake config | 直接保留会导致缺失目标引用 | 移除 lib/cmake 与 pkgconfig，自建 libdetour::libdetour 目标 |

## 验证结果

- 待 HarmonyOS aarch64 真机预检（conan create）后回填：
  ctest 输出、上游 30 例通过数、test_package 3/3 通过数。
- 本地未运行 conan（按任务守则，仅真机执行）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（Detour 拆分、ctest 接入、HMBS 证据标记） |
| conandata.yml | 官方源 + SHA-256 |
| test_package/test_detour.cpp | 真实调用 Detour API 的 3 检查消费者测试 |
| test_package/CMakeLists.txt | 链接 libdetour::libdetour |
| test_package/conanfile.py | 运行消费者测试并重放上游证据 |
| test_package/MANIFEST.yml | 上游 30 例审计与测试声明 |
| manifest.yaml | 版本级 manifest（status: built） |

## 注意事项

- 版本号 = 上游 1.6.0（首次适配，无修复后缀）。
- 消费者头文件路径为 `recastnavigation/Detour*.h`
 （includedirs 含 `include` 与 `include/recastnavigation`）。
- 默认关闭 64 位 polyref 与虚查询过滤器，与上游默认行为一致。
