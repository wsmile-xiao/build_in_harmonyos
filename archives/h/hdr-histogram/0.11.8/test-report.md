# HdrHistogram_c 0.11.8（hdr-histogram）测试报告

## 测试概况

**测试日期**: 2026-10-02
**编译系统**: CMake + Clang 15 (OHOS SDK 26.0.0.18, conan CMakeToolchain)
**测试平台**: OpenHarmony/HarmonyOS PC aarch64-linux-ohos（宿主同架构直跑）
**总测试数**: 64（上游）+ 3（test_package 消费者/OHOS 专项）
**通过率**: 100%

## 执行方式

- 构建入口：`conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`
- 上游测试：从 conan 构建产物目录 `build/Release/test/` 直跑 5 个测试二进制
  （fixture jHiccup-*.hlog / test_tagged_*.txt 由上游 configure_file 复制到该目录，
  与上游 ctest 工作目录等价），逐个记录 exit code 与 `Tests run: N` 输出
- test_package：conan create 自动执行（ctest 2 例 + 二进制直跑）

## 上游测试套件执行详情（真跑实测）

| # | 测试目标 | 注册用例数 | 实例化条件 | 实际执行结果 |
|---|----------|-----------|------------|--------------|
| 1 | hdr_histogram_test | 18 | 无条件 | ✅ exit 0，`ALL TESTS PASSED / Tests run: 18` |
| 2 | hdr_histogram_atomic_test | 16 | 无条件 | ✅ exit 0，`ALL TESTS PASSED / Tests run: 16` |
| 3 | hdr_atomic_test | 4 | 无条件 | ✅ exit 0，`ALL TESTS PASSED / Tests run: 4` |
| 4 | hdr_histogram_log_test | 25 | HDR_LOG_ENABLED（zlib 注入恢复） | ✅ exit 0，`ALL TESTS PASSED / Tests run: 25` |
| 5 | hdr_histogram_atomic_concurrency_test | 1 | 补丁 0003 扩展 OHOS 守卫 | ✅ exit 0，`ALL TESTS PASSED / Tests run: 1` |
| | **合计** | **64** | | **5/5 套件全过，executed_passed_total = 64** |

### 双口径台账
- source_declared_total = 64（test/ 各源文件 mu_run_test 声明合计）
- configured_executable_total = 64（CMake 注册并构建的测试目标用例合计）
- executed_passed_total = 64 / failed = 0 / uninstantiated = 0
- 通过率：64/64（100%）

### 各套件覆盖说明
1. **hdr_atomic_test（4）**：原子原语（原子加法/比较交换/加载存储/内存屏障）
2. **hdr_histogram_test（18）**：核心直方图 API（创建/记录/纠正值/合并/重置/min/max/mean/stddev/百分位/桶计数/等价判定）
3. **hdr_histogram_atomic_test（16）**：原子直方图 API（并发记录/原子统计/原子重置/纠正/合并）
4. **hdr_histogram_log_test（25）**：log 组件（hlog 编解码 V0-V3/压缩往返/标签校验/错误 fixture 4 例——本轮经 sysroot zlib 注入恢复入口）
5. **hdr_histogram_atomic_concurrency_test（1）**：多线程并发原子记录一致性（补丁 0003 纳入 OHOS）

## test_package 消费者测试（conan create 自动执行）

| 测试 | 结果 | 说明 |
|------|------|------|
| test_hdr_histogram | ✅ Passed（ctest 1/2 + 直跑 `hdrhistogram smoke test passed: total=4 max=1000`） | 消费者冒烟：hdr_init/hdr_record_value/hdr_record_values/total_count/hdr_max |
| test_ohos_platform | ✅ Passed（ctest 2/2） | OHOS 专项 3 断言：hdr_gettime/hdr_getnow 时钟路径、4 线程原子并发记录一致性（200000 值）、累积/百分位正确性 |

ctest 汇总：`100% tests passed, 0 tests failed out of 2`

## 制品完整性

- lib/libhdr_histogram.so（DT_SONAME=libhdr_histogram.so 已补 + binary-sign-tool 重签，patchelf 实测回显）
- lib/libhdr_histogram_static.a
- include/hdr/ 7 个公共头
- lib/cmake/hdr_histogram/ + lib/pkgconfig/hdr_histogram.pc
- bin/：5 个测试可执行 + hdr_histogram_perf + hdr_decoder

## 结论

- 上游测试用例通过率：64/64（100%）
- 新增（test_package/OHOS 专项）测试用例通过率：3/3（100%）
- conan create（OHOS profile）：CONAN_RC=0，SONAME+重签完成
