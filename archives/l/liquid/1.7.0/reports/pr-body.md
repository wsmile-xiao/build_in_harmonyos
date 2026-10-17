- **三方库名称**：liquid（上游 liquid-dsp）
- **上游版本**：v1.7.0
- **上游仓库地址**：https://github.com/jgaeddert/liquid-dsp
- **适配路径**：路径 A（基础适配）
- **使用知识库**：ohos-ohc-conan-pipeline

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1320 | 来源：上游 `src/**/tests/*.c` 与 `autotest/` 目录下的 `autotest_*` 用例函数（按测试函数级 `^void autotest_` 枚举）；其中 1317 项由 CMake `AUTOTESTS` 聚合清单（`CMakeLists.txt:416-575`，158 个测试程序 / 156 个 package）登记，构建期由上游 `scripts/autoscript.c` 生成 `autotest_include.h` 的 `NUM_AUTOSCRIPTS = 1317` |
| 集成测试 | 0 | 来源：上游未提供独立集成测试入口，全部由 `xautotest` 聚合程序承载（CTest 注册 1 个 test） |
| 其他测试 | 0 | 框架函数 `autotest_print_results()` 不计入用例 |
| **合计** | **1320** | 清点证据：`archives/l/liquid/1.7.0/reports/upstream-autotest-1.7.0.md` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1320 | 不变 | 未修改、未删除任何上游用例；其中聚合登记的 1317 项已在 HarmonyOS aarch64 真机全量执行，1317/1317 通过 |
| 集成测试 | 0 | 不变 | 上游无独立集成测试入口 |
| 鸿蒙特有测试 | 2 | 新增 | 针对鸿蒙平台特性的测试：① `test_package/test.c` L1 链接测试；② `test_package/consumer-case/liquid-ohos-test.c` 消费者用例（`resamp_crcf` 端到端运算） |
| **合计** | **1322** | **+2** | 上游 1320 + 鸿蒙特有 2 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 未选择「是」，不存在对上游测试用例的修改，无需逐条列出。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：新增 2 个鸿蒙平台测试用例（1 个 L1 链接测试 + 1 个鸿蒙消费者端到端用例）
> - **补全原因**：上游 `xautotest` 套件需在构建期执行 `autoscript` 代码生成器，交叉编译下无法构建（配方 `BUILD_AUTOTESTS=OFF`）；且上游 `test_package` 仅覆盖对象创建/销毁的链接阶段，未覆盖实际 DSP 运算链路
> - **新增测试文件清单**：
>   1. `archives/l/liquid/1.7.0/test_package/test.c` — 创建/销毁 `agc_crcf`、`nco_crcf` 对象，验证头文件、链接与 `libm` 链路
>   2. `archives/l/liquid/1.7.0/test_package/consumer-case/liquid-ohos-test.c` — `resamp_crcf` 创建 → 逐样本执行 → 输出样本数校验 → 销毁全链路

## 验证结果

- 编译状态：通过（`Building from source` + `Package created`，非缓存命中）
- 上游测试用例通过率：1317/1317（100%）
- 新增测试用例通过率：2/2（100%）

## 补充说明

### 上游用例数口径

上游 v1.7.0 用例数按测试函数级枚举为 **1320** 项；其中 1317 项由 CMake `AUTOTESTS` 聚合清单在构建期登记并实际执行（`NUM_AUTOSCRIPTS = 1317`），另有 2 项为上游 CMake 未登记的 `src/buffer/tests/sbuffer_autotest.c`、1 项为 `autotest/` 目录的库版本自检。**通过率分母取实际执行条数 1317，与「上游清单 1320」分开表述**，避免口径混用。

### 上游测试独立验证（R51 三步法）

上游 `BUILD_AUTOTESTS` 在配方中关闭（交叉编译下 `autoscript` 代码生成器无法执行），上游测试按 R51 在 HarmonyOS aarch64 真机独立构建执行并回填实测值：

```
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_AUTOTESTS=ON \
  -DBUILD_BENCHMARKS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_SANDBOX=OFF \
  -DBUILD_DOC=OFF -DENABLE_SIMD=OFF -DCOVERAGE=OFF
ninja xautotest
LD_LIBRARY_PATH=$PWD ./xautotest -o upstream-autotest-1.7.0.json
LD_LIBRARY_PATH=$PWD ctest --output-on-failure
```

产物平台：`xautotest: ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`

```
autotest seed: 1790338242
==================================
 WARNINGS : 57
==================================
 PASSED ALL 716451 CHECKS
==================================

1/1 Test #1: test .............................   Passed  127.66 sec
100% tests passed, 0 tests failed out of 1
```

上游用例清单 N = **1320**；聚合登记并实际执行 N′ = **1317**，**1317/1317 通过（100%）**，0 失败、0 跳过，`rc=0`。断言检查 **716451** 条全部通过；57 条 warning 均为上游刻意构造的非法配置用例（预期行为，对应用例 `pass: true`）。证据：`reports/upstream-autotest-1.7.0.md`（清点与实跑原始输出）、`reports/upstream-autotest-1.7.0.json`（1317 条逐用例机器可读结果）。

### CMake 配置说明

上游 v1.7.0 的 `CMakeLists.txt:14-20` 声明的 option 中，配方设置 `ENABLE_SIMD=OFF`（`cmake/FindSIMD.cmake` 用 `CHECK_C_SOURCE_RUNS()` 即 `try_run` 探测 SIMD，交叉编译下报 `try_run() invoked in cross-compiling mode`，探测值退化为 `PLEASE_FILL_OUT-FAILED_TO_RUN`，SIMD 结论不可用）、`BUILD_AUTOTESTS=OFF`、`BUILD_BENCHMARKS=OFF`、`BUILD_EXAMPLES=OFF`、`BUILD_SANDBOX=OFF`、`BUILD_DOC=OFF`、`COVERAGE=OFF`。

v1.7.0 的 CMakeLists **未集成 FFTW**（`CMakeLists.txt:47` 仅遗留注释 `# TODO: check for FFTW`），不存在 `FIND_FFTW` 开关，也无 GPL 许可污染问题；`FIND_SIMD`、`ENABLE_STRICT` 同样不是 v1.7.0 的 CMake 选项，故未传入（不存在的变量会触发 CMake `Manually-specified variables were not used by the project` 警告）。

### L5 SONAME 门禁（非阻塞）

`libliquid.so` 无 DT_SONAME（readelf 确认）。OHOS conanrun 通过 `LD_LIBRARY_PATH` 注入加载，运行期正常。W3 L5 门禁标记为失败但属非阻塞项。

### R38 命令声明

本包为库类型（无 `bin/` 目录、无 `RUNTIME DESTINATION`），不生成 `commands.json`。

### 已知限制

1. **SIMD 优化关闭**：OHOS 交叉编译下 SIMD 探测（`try_run`）不可用，DSP 运算使用通用 C 实现，性能低于 SIMD 优化版本。
2. **autotests 不纳入 conan 包**：交叉编译限制，上游测试未纳入 conan 构建流程，按 R51 在真机独立执行并回填实测值，未跳过或缩圈上游任何用例。
