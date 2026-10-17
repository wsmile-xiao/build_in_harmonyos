# merve/1.2.2 真机测试报告（HarmonyOS PC / aarch64）

- 任务：#8811（活动「开源鸿蒙PC专项积分赛」），分支 `feat/merve-1.2.2`
- 设备：HongMeng Kernel 1.12.0 / aarch64 / Toybox 用户态
- 工具链：harmonybrew clang 23.1.1（`Target: aarch64-unknown-linux-ohos`）、cmake 4.4.3、
  conan 2.29.1、python 3.14.7
- 缓存：`CONAN_HOME=~/work/psj/ch-mv8811`（私有 home，`conancenter` 置 disabled，只留 `ohpcd`），
  profile `ohos-aarch64`（host = build）
- 日志：`~/work/psj/mv8811-ch4.log`

## 命令

```sh
conan create archives/m/merve/1.2.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 结果

```
CREATE_EXIT:0
merve/1.2.2: HMOS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "gtest+ctest",
  "source_declared_total": 100, "configured": 101, "passed": 101, "total": 101, "failed": 0}
```

### 上游套件（`ctest --output-on-failure`，配方在 `build()` 内真实执行）

```
-- The tests are enabled.
[ 50%] Building CXX object tests/CMakeFiles/c_api_tests.dir/c_api_tests.cpp.o
[ 60%] Building CXX object tests/CMakeFiles/real_world_tests.dir/real_world_tests.cpp.o
[ 90%] Built target c_api_tests
[100%] Built target real_world_tests

Test project .../build/Release
  Test   #1: real_world_tests.esbuild_hint_style
  ...
  Test #101: c_api_compile_test

Total Tests: 101
1/101 Test   #1: real_world_tests.esbuild_hint_style .........   Passed    0.04 sec
...
101/101 Test #101: c_api_compile_test .........................   Passed    1.74 sec

100% tests passed out of 101
Total Test time (real) =   5.88 sec
```

计数交叉核对（同一份 ctest 日志）：

| 口径 | 取数命令 | 值 |
|---|---|---|
| 上游 TEST 宏声明 | `grep -cE '^  *TEST\(' tests/real_world_tests.cpp tests/c_api_tests.cpp` | 65 + 35 = **100** |
| CTest 枚举项 | `ctest -N` 中匹配 `^\s*Test\s+#\d+:` 的行 | **101**（100 个 GoogleTest 用例 + 1 个 `c_api_compile_test` 编译型用例） |
| 实跑通过 | `grep -c " Passed" hmos_ctest.log` | **101** |
| 失败/跳过 | 同日志 | **0 / 0** |

声明口径取「CTest 枚举并实跑的 101」，不小于源码宏数 100，两者差异已在上表说明
（多出的 1 项是 `tests/CMakeLists.txt` 用 `add_test` 注册的纯 C 编译用例）。

### 消费者（鸿蒙特有）套件

```
MERVE_CONSUMER_RESULT name=test_package checks=43 failed=0
MERVE_CONSUMER_RESULT name=harmonyos_test checks=29 failed=0
```

两个二进制都由 `test_package` 通过 `find_package(merve CONFIG REQUIRED)` + `merve::merve`
构建并在真机执行，退出码 0（`conan create` 未因任一断言失败而中断）。

### 产物布局（无 `bin/`）

```
include/merve.h
include/merve_c.h
include/merve/parser.h
include/merve/version.h
lib/libmerve.a
lib/cmake/merve/
lib/pkgconfig/merve.pc
licenses/LICENSE-MIT
licenses/LICENSE-APACHE
```
