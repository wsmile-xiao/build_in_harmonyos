# 测试报告 — tacopie 3.1.0

> **项目**: tacopie 3.1.0（Multi-platform TCP Client & Server C++11 library）
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS aarch64（OHOS userland, clang 15.0.4, libc++）
> **测试类型**: 官方 tag 测试入口核查 + Conan 消费者验证（test_package）

---

## 一、测试摘要

| 指标 | 数值 |
|:----:|:----:|
| 官方 tag 独立 TEST_CASE 声明数（source_declared_total） | 0 |
| 当前 OHOS 配置可实例化/注册用例数（configured_executable_total） | 0 |
| 实际执行并通过（executed_passed_total） | 0 |
| 上游 gtest runner 实例化运行结果 | 0 tests, PASSED（gtest/1.17.0） |
| 消费者用例（test_package） | 2/2 通过（100%） |

**消费者验证通过率**: ✅ **2/2（100%）**
**上游全量通过率**: 0/0 不适用（官方 3.1.0 tag 未携带独立 TEST_CASE 声明，仅 gtest runner main.cpp）

## 二、测试结论

### 2.1 总体评价

✅ **tacopie 3.1.0 在 HarmonyOS PC (aarch64) 上适配成功**：库本体编译、test_package
消费者往返验证、OHOS 专项验证全部通过。

### 2.2 上游测试说明

官方 3.1.0 tag 的 `tests/` 目录仅包含 `tests/CMakeLists.txt` 与
`tests/sources/main.cpp`（gtest runner 主函数），**无任何 spec/*.cpp 用例源文件**，
全仓 grep `TEST_CASE|TEST(` 零命中。用 ohpcd registry 的 gtest/1.17.0 实际编译链接
运行 runner：`Running 0 tests from 0 test suites … PASSED 0 tests`（runner 本身在
OHOS 工具链编译运行正常，用例数为 0 是 tag 内容决定的，非平台问题）。

### 2.3 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 bug：unix connect() select() nfds=0 | 任何带超时的 connect 必抛 timed out | 高（已修复） |
| 无其他阻塞问题 | — | — |

### 2.4 可用功能清单

```
✅ tcp_server::start / stop / is_running（OHOS bind + io_service）
✅ tcp_client::connect（超时路径修复后正常）/ is_connected / disconnect
✅ async_read / async_write 回环数据往返（payload 一致性校验）
✅ io_service select 轮询 + self-pipe 唤醒（OHOS epoll/select 路径）
```

## 三、测试执行明细

| 用例 | 命令 | cwd | 退出码 | 结果 |
|------|------|-----|:------:|:----:|
| test_tacopie | ctest (conan create test_package) | archives/t/tacopie/3.1.0 | 0 | PASS |
| test_tacopie_hmos | ctest (conan create test_package) | archives/t/tacopie/3.1.0 | 0 | PASS |
| 上游 runner 实例化 | ./upstream_tacopie_tests | $HOME/oh-tmp/tacopie-src | 0 | 0 tests PASSED |

完整台账与逐项映射见 `notes.md`「上游测试台账」节。
