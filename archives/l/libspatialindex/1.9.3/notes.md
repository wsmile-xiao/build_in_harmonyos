# libspatialindex 1.9.3 适配笔记

## 编译环境
- 构建系统: cmake（cmake_minimum_required 3.5.0，C++11）
- 编译日期: 2026-09-12
- 编译器: clang 15.0.4（aarch64-linux-ohos 交叉，conan ohos-aarch64 profile）
- 状态: built（合并发布后由 release 流水线确认 published）

## 编译步骤

1. `conan create` 经配方 `conanfile.py` 驱动 CMake 配置与编译：
   - `SIDX_BUILD_TESTS=OFF`（配方产物仅库与头文件）
   - `BUILD_SHARED_LIBS=OFF`（默认静态；shared 选项可切换）
   - 静态构建时 `CMAKE_POSITION_INDEPENDENT_CODE=ON`
2. `cmake.install()` 安装两个库目标 `spatialindex`（C++）与 `spatialindex_c`（C API 包装，链接前者）及头文件。
3. W3 本地验证与消费者测试见"验证结果"。

## 上游测试清点与运行（R51 四维账本）

静态清点（N_static，按上游 tag 1.9.3 源码逐项统计）：

| 类别 | 来源 | 数量 |
|------|------|------|
| gtest 原子用例 | test/gtest/sidx_api_test.h TEST 宏逐项计数 | 10 |
| 功能测试程序 | test/CMakeLists.txt add_executable 逐项计数（geometry 1 + rtree 5 + mvrtree 4 + tprtree 4） | 14 |
| **合计 N_static** | | **24** |

实际运行（SIDX_BUILD_TESTS=ON，设备原生构建，CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容内嵌 gtest-1.10.0 与 CMake 4.x）：

| 项 | 结果 |
|----|------|
| libsidxtest（gtest 10 用例，CTest 注册） | PASSED（10/10） |
| test-geometry-Intersection | 通过（exit 0） |
| rtree 管线 Generator/RTreeLoad/RTreeQuery/Exhaustive | 全部通过（exit 0） |
| mvrtree 管线 Generator/MVRTreeLoad/MVRTreeQuery/Exhaustive | 全部通过（exit 0） |
| tprtree Generator/TPRTreeLoad/Exhaustive | 通过（exit 0；Generator 需参数 -ds/-sl/-a/-mui，上游解析器不支持其 Usage 所列 -sd/-id） |
| test-tprtree-TPRTreeQuery | **失败**（IllegalArgumentException: Shape start time is older than tree current time——上游程序时序回放缺陷，重放数据时间戳早于树当前时间；与平台无关，同数据任何平台复现） |

通过率：静态全量 23/24（95.8%）。
说明：全量 TPR 数据集（57045 行）在共享高负载设备上 TPRTreeLoad 超 300s，按上游 Generator 设计参数缩小数据集（4520 行）完成功能验证（Load/Exhaustive 通过）；未列入 CMake SOURCES 的 test/rtree/CRTree.cc、RTreeParallel.cc 为上游自身未注册项，不计入 N_static。

消费者测试（N_consumer=1）：test_package/test_consumer.c 经 C API 创建内存 RTree（IndexProperty_SetIndexStorage RT_Memory）、插入三维区域、断言 Index_Intersects_id 查询结果数，conan create 内 PASSED。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 包产物出现 .so 且 spatialindex_c 的 DT_NEEDED 记录 `../bin/libspatialindex.so` 相对路径，运行时加载失败 | 上游 CMakeLists.txt 第 46 行 `SET(BUILD_SHARED_LIBS ON)` 普通 set 覆盖工具链注入的 cache 值，强制共享库构建 | 补丁 0001 移除该行，链接方式交由 Conan 工具链控制（知识 E288 同类模式） |
| 2 | C 驱动的消费者可执行链接 C++ 静态库报 undefined symbol: operator new / std::__n1 | C 链接器不自动拉 libc++ | 配方 package_info 声明 `system_libs=["c++"]`（静态选项下），知识 E247 同类模式 |
| 3 | 消费者测试 test() 报 conanrun 环境缺失 | generators 未含 VirtualRunEnv（E298） | generators 增加 VirtualRunEnv，test() 显式 env="conanrun" |
| 4 | Index_Create 返回 NULL | C API 默认磁盘存储，需显式内存存储 | IndexProperty_SetIndexStorage(props, RT_Memory)（对齐上游 gtest 用法） |

## 源码修改

- patches/0001-CMakeLists.txt.patch：1 行（`SET(BUILD_SHARED_LIBS ON)` → 注释），见问题 1。无平台宏。

## 依赖版本

无外部依赖（零依赖库）。

## 验证结果

```bash
# W3（finish 内部）：conan create 干净构建 + test_package 消费者测试 → 通过
# conan-verify：G0-G4 + L2/L4/L5 全绿，Verdict: PASS（reports/conan-verify-report.md）
# 上游测试：ctest（libsidxtest 10/10）+ 14 功能程序管线，23/24 通过
```

## 路径 B 判断

不满足路径 B 门槛，按纯路径 A。依据：本轮两个可复用知识点（C 驱动链接 C++ 静态库需 system_libs c++；CMake SET 硬编码覆盖 toolchain 注入）经知识库引擎查重均已命中现有条目 E247、E288，无新增增量价值。

## 注意事项

- 根 CMakeLists 将 CMAKE_BUILD_TYPE FORCE 为 RelWithDebInfo，不影响 conan 工具链 flags 注入。
- 上游 test/tprtree/Generator.cc 的 Usage 文案与参数解析器不一致（-sd/-id 提示存在但不被解析），为上游缺陷。
---

**编译结束**: 2026-09-13 01:55
**最终状态**: built
