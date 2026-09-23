# verstable 2.2.1 功能测试报告

**测试日期:** 2026-09-19
**测试环境:** HarmonyOS PC (aarch64)
**编译器:** clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-linux-ohos)
**构建系统:** 无（单头文件库，header-only）

## 1. 编译测试

### 1.1 编译状态
✅ header-only 库: 无需编译（配方 build() 无编译步骤，R34 不伪造编译日志）
✅ 上游测试编译: unit_tests.c + tests_against_stl.cpp 均编译通过
✅ test_package 消费者测试: conan create 内实际编译运行通过（1/1 Passed）
✅ 鸿蒙专项测试: tests/ohos_smoke.c 用 OHOS SDK clang 编译运行通过

### 1.2 源码修改
- 0 补丁（patches/ 为空），纯 header-only 适配，无源码改动

## 2. 上游测试（双口径台账）

### 2.1 枚举（source_declared_total）

| 测试源文件 | 独立用例数 | 分类 | 说明 |
|---|---|---|---|
| tests/unit_tests.c | 30 | 用户测试源独立 TEST_CASE（static void test_* 函数） | map 15 + set 15，main() 循环 1000 轮注入随机分配失败 |
| tests/tests_against_stl.cpp | 10 | 用户测试源独立用例（5 map + 5 set 对照，N_TESTS=5 × N_OPS=50000） | 与 std::unordered_map/set 随机操作比对 |
| verstable.h | 0 | 框架头/源码 | 库主体头文件，不含独立用例 |
| images/、README、docs | 0 | 样例/文档 | 非测试 |

**source_declared_total = 40**（源码声明可复制枚举：C 文件 30 个 test_* 函数 + C++ 文件 5×2 轮对照测试）

### 2.2 configured_executable_total / executed_passed_total

| 配置化可执行用例 | 实际执行 | 结果 |
|---|---|---|
| unit_tests（clang -std=c11 -O2 -I. 编译） | 运行 | ✅ 通过 (exit 0, "All done", 64969 次模拟分配失败) |
| tests_against_stl（clang++ -std=c++17 -O2 -I. 编译） | 运行 | ✅ 通过 (exit 0, "All done", 32509 次模拟分配失败) |

**configured_executable_total = 2，executed_passed_total = 2，失败 = 0，未运行/未实例化 = 0**

### 2.3 全量通过率

- 全量口径: **40/40 (100.0%)**（以发现的全部独立上游用例数为分母）
- 当前配置可执行集合: **2/2 (100.0%)**
- 声明数与可执行数差异: 上游测试均为单文件 self-contained 程序，main() 内循环调用全部用例；
  无 ctest/GTest 注册层，故 40 个源码用例聚合为 2 个可执行程序，二者一致无遗漏

### 2.4 运行证据

```bash
# C 测试
cd /storage/Users/currentUser/tmp/builds/verstable-2.2.1.work
clang -std=c11 -O2 -I. tests/unit_tests.c -o ~/tmp/verstable-2.2.1/logs/unit_tests   # exit 0
~/tmp/verstable-2.2.1/logs/unit_tests                                              # exit 0: All done. Simulated realloc failures: 64969

# C++ 测试
clang++ -std=c++17 -O2 -I. tests/tests_against_stl.cpp -o ~/tmp/verstable-2.2.1/logs/tests_against_stl  # exit 0
~/tmp/verstable-2.2.1/logs/tests_against_stl                                                          # exit 0: All done. Simulated allocation failures: 32509
```

## 3. 鸿蒙专项测试 (test_package + consumers)

### 3.1 消费者用例（test_package/test.c）
仅使用安装头文件 `verstable.h` 的公开 C11 通用 API：实例化 int set，
插入 10 键 → 擦除 3 个 → 检索 6 键断言 → 迭代计数断言 → 清理。
`conan create` 内实际运行: `1/1 Test #1: test_verstable ... Passed 0.04 sec`

### 3.2 鸿蒙专项用例（tests/ohos_smoke.c）
用 OHOS SDK clang 15 编译（-std=c11，target aarch64-linux-ohos）：
set 5000 键批量插入/擦除/检索/迭代断言 + map 10000 键值对映射断言。
运行输出: `OHOS smoke test: PASS (set 5000 keys/2500 remain, map 10000 pairs verified)`

## 4. 验证结果汇总

| 门禁 | 结果 |
|---|---|
| upstream unit_tests.c (C) | ✅ 40/40 用例, exit 0 |
| upstream tests_against_stl.cpp (C++) | ✅ exit 0 |
| OHOS 专项 smoke test | ✅ PASS |
| test_package 消费者 (conan create) | ✅ 1/1 Passed |
| conan-verify 8 道门禁 | ✅ PASS |
| W3 本地 CI (build_and_test.sh) | ✅ exit_code=0 (.ci-result.json) |