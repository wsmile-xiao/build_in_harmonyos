# libhwy_contrib 1.3.0 测试报告

> **项目**: libhwy_contrib（Google Highway 上游 `hwy_contrib` 目标）
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS (OHOS) 6.0 aarch64 真机，clang 15.0.4 (libc++)，Conan 2.29.1，CMake 4.x，profile `ohos-aarch64`
> **测试类型**: 上游测试套件（HWY_TEST_STANDALONE 运行器，ctest 注册）+ test_package 消费者测试
> **计数单位**: ctest 注册用例（真机执行；含按指令集目标参数化的实例），消费者用例单独计数

---

## 一、测试摘要

| 指标 | 数值 | 说明 |
|:----:|:----:|:------:|
| 上游自动化测试（ctest 注册用例） | 801 | 651 核心（hwy/tests/ 套件）+ 150 contrib（hwy/contrib/ 套件） |
| test_package 消费者测试 | 1 | PASS（4 项断言） |

**上游测试通过率**: 801/801（100%）

**消费者测试通过率**: 1/1（100%）

---

## 二、上游测试清点与执行（R51 三步法）

1. **清点**：上游 highway 1.3.0 顶层 CMakeLists 在 `BUILD_TESTING=ON AND
   HWY_ENABLE_TESTS=ON` 下对 `hwy/tests/` 58 个 `*_test.cc` 与 `hwy/contrib/`
   16 个测试源逐文件 `add_executable` + 注册 ctest；运行器为
   `HWY_TEST_STANDALONE`（上游自带 GTest 兼容层，不下载 googletest）。
2. **运行**：W3 `conan create`（默认选项 `with_upstream_tests=True`）在
   HarmonyOS aarch64 真机编译全部测试可执行并 `cmake.test()` 实跑。两轮独立
   实测结果一致：

   ```
   100% tests passed, 0 tests failed out of 801
   Total Test time (real) =  35.71 sec
   ```

3. **申报**：上游 801 个 ctest 用例全部通过（0 fail、0 skip）。
   contrib 范围（与本包编译源直接相关）150 例，套件分布：
   HwyMathTestGroup 42、SortTestGroup 20、HwyRandomTestGroup 20、
   TransformTestGroup 12、ThreadPoolTestGroup 9、DotTestGroup 8、
   BitPackTestGroup 8、UnrollerTestGroup 6、CopyTestGroup 6、BenchSortGroup 4、
   ImageTestGroup 4、FindTestGroup 4、TopologyTestGroup 3、MatVecTestGroup 3、
   SpinTestGroup 1；其余 651 例为核心 SIMD 套件（与 highway 包共享，随同一
   conan create 执行）。

---

## 三、test_package 消费者测试（鸿蒙特有）

`test_libhwy_contrib.cpp` 经 `find_package(hwy_contrib)` +
`hwy::hwy_contrib` 目标链接本包 `libhwy_contrib.a` 与依赖包 `libhwy.a`，
在真机执行：

| 测试项 | 断言内容 | 结果 |
|--------|----------|------|
| test_libhwy_contrib | `hwy::SupportedTargets() != 0`（核心依赖头文件/库可用） | ✅ PASS |
| test_libhwy_contrib | `VQSort` 257 个 int32 升序后全序正确（本包编译导出符号） | ✅ PASS |
| test_libhwy_contrib | 升序端点一致性 `keys[0] <= keys[n-1]` | ✅ PASS |
| test_libhwy_contrib | `VQSort` 降序全序正确 | ✅ PASS |

执行日志（W3 conan create，`reports/w3-local-ci.log`）：

```
100% tests passed, 0 tests failed out of 1
libhwy_contrib consumer checks passed
```

说明：thread_pool/topology 头文件路径不进入消费者测试（上游 1.3.0 安装清单
漏装 `hwy/bit_set.h`，安装形态下 topology.h 不可用，详见 notes.md"已知限制"）；
topology.cc 编译产物的功能覆盖由上游套件 `ThreadPoolTestGroup`/`TopologyTestGroup`/
`SpinTestGroup`（13 例，从源码树执行）承担。

---

## 四、证据索引

- W3 本地 CI 日志：`archives/l/libhwy_contrib/1.3.0/reports/w3-local-ci.log`
  （finish 生成，含 conan create 全量输出与两段 ctest 摘要）
- Conan 配方验证报告：finish 生成 `reports/conan-verify-report.md/.json`
  （G0–G4、L2/L4/L5 门禁、私有缓存路径、包身份与消费者执行证据）
- 消费者链路独立探针：复用本轮已构建产物（export-pkg）+ 独立消费者工程
  实测 configure/编译/链接/运行全通（设备 ws/tmp 探针目录，记录于 notes.md
  验证过程记录）
