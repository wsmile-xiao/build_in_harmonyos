# robin-hood-hashing 3.11.5 测试报告

## 测试环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC (aarch64-linux-ohos) |
| 编译器 | clang 15.0.4 (OHOS SDK 26.0.0.18) |
| 构建系统 | CMake 4.1.2（上游测试）/ Conan 2.29.1（配方验证） |

## 上游测试（本机实际运行）

构建单一测试可执行 `rh`（doctest 2.4.6）：

```bash
cd $BUILD_SRC_DIR/build
cmake .. -DCMAKE_CXX_STANDARD=14 -DCMAKE_BUILD_TYPE=Release \
  -DCLANG_TIDY_PROGRAM= -DCMAKE_CXX_FLAGS="-fPIC -O2 -Wno-sign-conversion -Wno-error=sign-conversion"
make rh -j4
./rh
```

结果：

```
test cases:     127 |     127 passed | 0 failed | 73 skipped
assertions: 2164686 | 2164686 passed | 0 failed |
Status: SUCCESS!
```

- 127/127 test cases 通过，2,164,686 assertions 全部通过，0 failed。
- 73 skipped 为 doctest 默认略过的性能 bench/count 类型用例（非失败）。

上游测试构建说明：
- 需禁用 clang-tidy（上游 CMake 在 Clang 下自动启用 `CMAKE_CXX_CLANG_TIDY`，
  warnings-as-errors 风格检查会误伤测试代码风格告警）：
  `-DCLANG_TIDY_PROGRAM=`
- 需关闭 `-Wsign-conversion`（OHOS sysroot `PERF_EVENT_IOC_ID` 宏触发）。

## 消费者测试（conan create / test_package）

`conan create` 真实执行 test_package（实际 include robin_hood.h 并验证 API）：

```
1/1 Test #1: test_robin-hood-hashing ..........   Passed    0.03 sec
100% tests passed, 0 tests failed out of 1
```

## 结论

- 上游测试：127/127 通过（2164686/2164686 assertions，0 failed）。
- 消费者测试：1/1 通过。
- 整体通过率 100%，无失败用例。