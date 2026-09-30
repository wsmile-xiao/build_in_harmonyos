# ifcplusplus 0-git20190402.13744d5 适配笔记

## 编译环境
- 构建系统: cmake（上游 `CMAKE_MINIMUM_REQUIRED(3.7.2)`）
- 编译日期: 2026-09-30
- 编译器: clang/clang++ 15（OHOS 6.0 SDK，target `aarch64-linux-ohos`，`compiler.cppstd=17`，libc++）
- profile: `ohos-aarch64`（构建）/ `ohos-aarch64-run`（本地测试，CTest 经 qemu 执行）
- 状态: built

## 上游版本
- git 快照 `13744d58f9b99ce3b4d49567b7085917cd7a6a3c`（2019-04-02，
  "Merge pull request #143 from shenqiuyao/fix_random_crash"）
- tarball SHA-256 = `fbc1dcd4f89ff14282bf656374934da3dce8bd6871f04ca7b6257321f7791012`
- 同仓 `archives/i/ifcplusplus/2.5/` 为前作，本配方按其结构改造；两版差异见下表。

### 与 2.5 的关键差异

| 维度 | 2.5 | 0-git20190402.13744d5 |
|------|-----|------------------------|
| Boost | 源码内置（vendored），无 Conan 依赖 | **不内置**，公开头直接 `#include <boost/...>` → 必须真实依赖 `boost/1.84.0` |
| CMake option | `BUILD_CONSOLE_APPLICATION` + `BUILD_VIEWER_APPLICATION` | 只有 `BUILD_VIEWER_APPLICATION` + `BUILD_STATIC_LIBRARY` |
| 窄化编译错误 | `BuildingGuid.cpp` 的 `char` mask 数组 | 本快照无该文件，改为 `BuildingGuid.h` 的 lambda 返回类型问题 |
| Carve 链接方式 | — | 上游对 GNU/Clang 硬编码 `SHARED`，需补丁改 STATIC |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Find_package(Boost REQUIRED)` 找不到 Boost | boost 包用组件化 `cpp_info`，include 目录挂在 `boost_headers` 组件上（`cmake_target_name Boost::headers`）；聚合目标 `boost::boost` **不带 includedirs** | 配方 `tc.cache_variables["BOOST_ROOT"]`/`Boost_INCLUDE_DIR` 指向 Conan boost 包目录 + `Boost_NO_SYSTEM_PATHS=ON`；`package_info` 用 `self.cpp_info.requires = ["boost::boost_headers"]`，并在 `requirements()` 加 `transitive_headers=True` 让公开头的 Boost 依赖传递给消费者（同 `archives/n/numcpp` 的既有范式） |
| 2 | 消费者编译报 `boost/unordered_map.hpp file not found` | 同上：`cpp_info.requires` 只把依赖名接进 CMakeDeps，include 目录必须由被 require 的**组件**承载 | 见 #1 |
| 3 | `pthread_setcancelstate` 未声明 | OHOS musl 不提供该函数；`boost/core/detail/sp_thread_sleep.hpp` 由 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 守卫 | `CMAKE_CXX_FLAGS=-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost 1.84.0 配方已 patch 该守卫） |
| 4 | Carve 编译报 `no member named 'auto_ptr' / 'bind2nd' / 'bind1st' in namespace 'std'` | C++17 已移除这些设施，libc++ 按标准直接删除 | 补丁 0002：`auto_ptr`→`unique_ptr`(8 处)、`bind2nd`→lambda(2 处)、`bind1st`→lambda(1 处)，并补 `#include <memory>` |
| 5 | 交付物含 `libcarve.so` | 上游 Carve 对 GNU/Clang 硬编码 `ADD_LIBRARY(carve SHARED ...)`（`BUILD_SHARED_LIBS` 无效） | 补丁 0001：把该分支改为 `STATIC`；交付 `libIfcPlusPlus.a` + `libcarve.a` |
| 6 | 消费者一调用 `decodeBase64Uuid()` 就编译失败 | `BuildingGuid.h` 模板体内 lambda 同时 `return i`(uint8_t) 与 `return 0`(int)，无尾置返回类型；上游零调用点故从不实例化 | 补丁 0003：显式标注 `-> uint8_t` |
| 7 | 消费者 4 个 API 用法错误（编译期暴露） | 该快照 API 与 2.5 不同：无 `loadModelFromStream`，应为 `loadModelFromString`；`ReaderSTEP` 不继承带 stream 接口的基类 | test_package 改用 `loadModelFromString(std::string&, shared_ptr<BuildingModel>&)` |
| 8 | 鸿蒙专项用例 SIGABRT | `MeshSet` 的 `face_indices` 是**每面 `[N,i0..iN-1]` 扁平编码**，不是三角形三元组；`CARVE_ASSERT(face_indices[p] > 1)` 拒绝后抛 `carve::exception` | 测试改为正确编码；**未**关闭 `CARVE_ASSERT`（关断言只会掩盖误用） |

## 源码修改（补丁清单）

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-carve-static-link-ohos.patch` | `external/Carve/CMakeLists.txt` | `ADD_LIBRARY(carve SHARED)` → `STATIC`（仅 GNU/Clang 分支） |
| `0002-carve-cxx17-removed-facilities.patch` | `external/Carve/src/lib/intersect.cpp`、`src/lib/mesh.cpp`、`src/include/carve/spacetree.hpp` | `std::auto_ptr`→`std::unique_ptr`(8)、`std::bind2nd`→lambda(2)、`std::bind1st`→lambda(1)、补 `#include <memory>` |
| `0003-buildingguid-lambda-return-type.patch` | `IfcPlusPlus/src/ifcpp/model/BuildingGuid.h` | lambda 显式返回类型 `-> uint8_t` |

均为 portability 修复：无平台宏（符合 R8），无行为变更。

## 依赖版本
- `boost/1.84.0`（OHOS 适配版，提供 header-only 使用所需的 include 与 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 定义）
- 传递：`zlib/1.3.1`（boost iostreams 需要）
- Carve / RapidJSON / glm 等内置第三方源码随上游源码树一起编译，不单独成包

## 验证结果

### 本地交叉构建 + 真实执行测试
```bash
$ bash outputs/local-validate-recipe.sh .../archives/i/ifcplusplus/0-git20190402.13744d5
==> conan exit=0
1/2 Test #1: test_ifcplusplus .................   Passed    0.36 sec
2/2 Test #2: test_ifcplusplus_ohos ............   Passed    0.42 sec
100% tests passed, 0 tests failed out of 2
```
- 执行方式：`ohos-aarch64-run` profile，`CMAKE_CROSSCOMPILING_EMULATOR=/root/ohpc/bin/ohos-qemu-aarch64`
  经 qemu + 真机 musl 运行根执行（非纯构建校验）。
- `test_ifcplusplus`：16 项检查全过（解析 64 实体 → 几何遍历 6 面/24 顶点 → 回写 3770 字节 → 再解析仍 64 实体）。
- `test_ifcplusplus_ohos`：13 项检查全过（CSG 交集 10 面/8 顶点、并集 26 面/20 顶点；GUID 64/64 回环；50 墙回写守恒）。

### 真机验证（润和 DAYU200-RK3568 · OpenHarmony 6.0.0.47 · aarch64）
```bash
$ bash automation/device_runner.sh run ifcplusplus_e2e /root/ohpc/scratch/ifcplusplus_device './test_ifcplusplus_ohos'
=== OHOS suite: 13 checks, 0 failed ===
RESULT: PASS
[device_runner] exit=0
[device_runner] evidence -> /root/ohpc/scratch/ifcplusplus_device/_device_evidence.json
```
静态链接 aarch64 ELF，无运行库依赖。证据 JSON：`exit_code=0`、`result_json_received=true`。

## 上游测试用例说明

**该快照上游测试用例数 = 0。** 可复现的核查：

```bash
grep -rn "add_test\|enable_testing" . --include=CMakeLists.txt   # 无输出
grep -rniE "gtest|catch2|doctest|boost/test" . --include=CMakeLists.txt  # 无输出
find . -iname '*test*'                                            # 无匹配
ls -a | grep -iE 'github|travis|ci|appveyor'                      # 无 CI 配置
```

上游唯一可执行目标是 `examples/SimpleViewerExampleQt`（依赖 Qt + OpenGL 的桌面 viewer，
非测试、且不属于 OHOS PC 库交付范围，配方以 `BUILD_VIEWER_APPLICATION=OFF` 关闭）。

因此"上游用例通过率"这一栏不存在可执行口径；适配后新增 2 个消费者端到端用例
（共 29 项检查）并 100% 通过，作为等价（且更强）的质量证据。

## 注意事项
- 该快照的 `ReaderSTEP` **没有** `loadModelFromStream()`（2.5 有），消费者应使用
  `loadModelFromString(std::string&, shared_ptr<BuildingModel>&)`。
- `BuildingModel::getMapIfcEntities()` 返回实体表，`IfcProject` 等具体类型需显式 `#include` 对应头，
  `BuildingModel.h` 只做前置声明。
- Carve 的 `MeshSet` 从点集构造时，`face_indices` 必须是每面 `[N, i0, ..., iN-1]` 扁平编码；
  写错会触发 `CARVE_ASSERT` 抛异常。不要用 `-DCARVE_NODEBUG` 规避。
- pip/消费端 32 位与 64 位差异：`char` 无符号相关的旧问题在 2.5 的 `BuildingGuid.cpp`，
  本快照该文件不存在，对应风险点是 `BuildingGuid.h` 的 lambda（见补丁 0003）。
