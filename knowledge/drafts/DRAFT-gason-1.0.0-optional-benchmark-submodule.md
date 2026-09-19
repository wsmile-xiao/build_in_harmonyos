# DRAFT-gason-1.0.0-optional-benchmark-submodule：可选 benchmark 目标依赖未入包子模块时用 option 门控

> Contributor: pc1-52 | Status: Draft | Updated: 2026-09-19
> Source: gason 1.0.0 HarmonyOS PC 适配（W3/finish 本地验证 + conan-verify G2 真实日志）
> 主题：CMake 构建中可选的非交付目标（benchmark/demo）引用发布 tarball 未包含的 git 子模块头文件时，
> 用 `option(... OFF)` 门控目标，并在配方 generate() 中显式置 OFF，而不是为可选目标手动下载子模块。

## 现象

gason 1.0.0 上游 CMakeLists.txt 无条件声明 `add_executable(benchmark src/benchmark.cpp)`
并 `target_include_directories(benchmark PRIVATE rapidjson/include)`。官方 v1.0.0 tag 的
release tarball（archive/refs/tags/v1.0.0）不含 rapidjson 子模块内容，因此：

```text
src/benchmark.cpp:35:10: fatal error: 'rapidjson/document.h' file not found
```

benchmark 是可选性能对照目标（非库交付物），库本体（libgason.a + gason.h）与

测试套件（test-suite 43/43）完全不受影响。若按 E150 的 manual-download 处理，会为一个
非交付目标引入额外源码下载与维护成本；更糟的是在 recipe 内执行未锁定的
`git submodule update`，破坏可复现性（见 DRAFT-release-tarball-missing-cmake-submodule 的
forbid 规则）。

## 根因

发布 tarball 由 `git archive` 生成，默认不包含子模块内容，只保留 .gitmodules 引用。
上游把所有目标（含依赖子模块的可选目标）无差别加入 build 时，干净环境编译必然在
可选目标上失败，即使交付产物与测试与该目标无关。

## 可复用处理（本任务实测）

1. 确认该目标是否为交付物：非库/工具交付、仅基准/演示用途 → 应当门控而非下载子模块。
2. 上游源码最小补丁：把目标包进 `option()`，默认 OFF（无平台宏，符合 R8）：
   ```cmake
   option(BUILD_GASON_BENCHMARK "Build the benchmark (requires rapidjson submodule)" OFF)
   if(BUILD_GASON_BENCHMARK)
       add_executable(benchmark src/benchmark.cpp)
       target_include_directories(benchmark PRIVATE rapidjson/include)
   endif()
   ```
3. 配方 generate() 中显式置 OFF（与补丁双保险，防消费方开启）：
   ```python
   tc.variables["BUILD_GASON_BENCHMARK"] = "OFF"
   ```
4. 补丁同时补 install() 规则（上游无 install，否则 package 空壳）。
5. 验证：OHOS 工具链 `cmake --build` 通过 + 上游 test-suite 43/43 + test_package
   消费者用例真实调用 API + `conan create` G2 通过。

## 证据

- gason v1.0.0 tarball SHA-256 773bc850...，`tar tzf` 无 rapidjson 目录（grep 无命中）。
- 门控前 OHOS 构建：benchmark 编译失败（rapidjson/document.h not found），lib/test-suite/gasonpp 成功。
- 补丁 + generate() OFF 后：`conan create` G2 PASS、W3 build_and_test.sh PASS、
  test_package test_gason/test_ohos 全部通过。

## 边界

- 仅适用**可选、非交付**目标（benchmark/demo/profiler）。交付目标及其子模块缺失时仍应
  按 E150 manual-download 或显式 vendoring 处理，不得用 option 门控掩盖交付缺口。
- 禁止以门控名义跳过真实上游测试或伪造产物；test-suite 等独立上游用例必须照常枚举与运行。
- 本知识不替代 R38 commands.json 判断：若门控的是唯一 CLI 产物，需另行评估 CLI 声明。

## 与既有条目关系

- caused_by / combines_with: E150（submodule 不入 tarball 的根因）
- extends: DRAFT-release-tarball-missing-cmake-submodule（该草稿处理 CMake 辅助模块
  include 失败；本条目处理可选编译目标因缺失子模块头文件而编译失败，对策是门控而非下载）
- similar_to: E342（BUILD_TESTING=OFF 避免网络自举）——同属"关闭非必要目标保构建确定性"，
  本条目触发点是"子模块头文件缺失编译失败"，对策落到上游补丁 + 配方变量双处
- conflicts_with: E150 的 manual-download（对可选目标不适用，仅交付目标适用）
- prerequisite_of: 无