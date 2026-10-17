# DRAFT-isutf8-cmake-configure-download-benchmarks：无开关的上游 configure 期源码下载

## 现象

is_utf8 1.4.1（https://github.com/simdutf/is_utf8）顶层 `CMakeLists.txt`：

```cmake
add_subdirectory(benchmarks)   # 无条件执行，与 BUILD_TESTING 无关
```

`benchmarks/CMakeLists.txt` 调用 `cmake/import.cmake` 的 `import_dependency(simdutf simdutf/simdutf v2.0.9)`，该函数在 **configure 阶段**执行：

```cmake
file(DOWNLOAD "https://github.com/simdutf/simdutf/archive/v2.0.9.zip" ...)
```

并把整个 simdutf 源树 `add_subdirectory` 进本工程。上游没有提供关闭 benchmarks 的选项，仅 `IS_UTF8_DEPENDENCY_CACHE_DIR`（本机缓存目录）可绕过。干净 CI/离线 worker 上，包还没开始编译就在 configure 拉外网源码——不可复现且把未经审计的第三方源码混进构建输入。

## 根因

基准测试（benchmark）目标不属于生产构建，却被上游写成无条件子目录，其依赖导入方式又是 configure 期 `file(DOWNLOAD)`。这与 E342（`BUILD_TESTING=ON` 触发测试框架 FetchContent）同族但不同点：**下载源不在测试路径内**，因此不需要牺牲上游测试覆盖来规避。

## 可复用修复模式

1. 用 `refresh-patch --auto` 生成最小源码补丁：在顶层 CMakeLists 新增**默认 OFF** 的项目选项（`IS_UTF8_BUILD_BENCHMARKS`），并把 `add_subdirectory(benchmarks)` 包进 `if (IS_UTF8_BUILD_BENCHMARKS)` 守卫。补丁不含平台条件宏（R8），全平台语义一致。
2. `conandata.yml` 声明补丁；配方 `generate()` 里显式 `tc.variables["IS_UTF8_BUILD_BENCHMARKS"] = "OFF"`。
3. 保留 `BUILD_TESTING=ON`（can_run 时）让上游真实测试照常进 `conan create`；不要照搬 E342 的“关测试”建议误伤可运行的上游套件。
4. 立项前静态排查：`grep -RnE 'file\(DOWNLOAD|FetchContent|ExternalProject' <src>/cmake <src>/*/CMakeLists.txt`，凡 configure 期外网导入且无选项守卫的目录，一律先加补丁开关再进 W3/CI。

## 实际验证结果（鸿蒙设备端，2026-09-03）

- 打补丁后 `cmake -S . -B build && make -j2`：configure 无任何下载日志，`ctest` 1/1 `unit` Passed（1.5–1.9s）。
- `ohc-run.py conan-verify is_utf8 1.4.1`（rc=0）：G0–G3 PASS，G2 的 conan create 日志中无 configure 下载行为；G4 记 PASS 但带「无法找到程序包 ID」告警，其下 L2/L4/L5 显示「跳过（无 cache 路径）」。真实门禁通过证据以本地 W3（CI 同源 `build_and_test.sh`）为准：L0/L1/L4/L5=pass、L2=skip（库包无 bin/，合法），`.ci-result.json exit_code=0`；日志 `archives/i/is_utf8/1.4.1/reports/`（工具生成物，按仓库规范不入库）。

## 适用范围与边界

- 适用：上游 CMake 项目在**非测试目录**（benchmarks/tools/examples）configure 期无条件拉外网源码且无禁用开关。
- 不适用：下载发生在 test/BUILD_TESTING 路径内（走 E342 口径）；上游本就有开关（直接传 `-D` 即可，无需补丁）。

## 查重差异

- 与 E342 主题相邻（configure-time download），但 E342 的推荐动作是关闭网络化上游测试；本条目场景是 benchmarks 目录，修复动作是**补丁添加选项**并保留测试执行，二者互补不重复。`similar_to: E342`。
