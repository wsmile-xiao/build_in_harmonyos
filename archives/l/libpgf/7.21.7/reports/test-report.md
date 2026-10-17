# 测试报告 — libpgf 7.21.7 OHOS 适配

> **项目**: libpgf
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS HongMeng Kernel aarch64（OHOS 设备原生，clang 15.0.4，profile ci/conan/profiles/ohos-aarch64）
> **测试类型**: 上游官方测试套件（无——见 2.4）+ test_package 消费者功能测试
> **验证 HEAD**: 以任务审计输入绑定为准（audit-input.json 的 head_sha = 交付 HEAD）；本报告所述测试结果在交付 HEAD 的 W3 日志 reports/w3-local-ci.log 与其 task-data 原件副本中可复核

---

## 一、测试摘要

计数单位说明：上游无任何测试入口；消费者测试按"程序 / 断言"两级分别计数，不混加。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试程序 | 0 | 不适用 |
| 消费者测试程序 | 1 | 100% |
| 消费者断言 | 5 | 100% |
| 通过 (PASS) | 1 程序 / 5 断言 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **编译与功能验证全部通过**：conan create 干净构建成功，消费者程序 test_libpgf 实际执行，5 项断言全部通过（日志原文 `5 checks, 0 failures`）；W3 本地 CI 模拟 L0/L1/L4/L5 全部 pass。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无阻断问题 | — | 🟢 |

### 2.3 可用功能清单

```
✅ PGF 无损编码：SetHeader + ImportBitmap + Write(内存流) 全流程
✅ PGF 解码：Open + Read + GetBitmap 往返
✅ 头字段保持：width/height/channels/bpp/mode 往返一致
✅ 静态库产物：lib/libpgf.a（L1e 破坏性反向验证确认消费者真实依赖本包）
⚠️ 有损质量模式：本次未测（quality=0 无损路径已覆盖编解码主链路）
⚠️ OpenMP 加速：未启用（_OPENMP 门控，不传 -fopenmp 即禁用，属设计行为）
```

### 2.4 已知限制

1. 上游 7.21.7 不带任何测试套件（无 test/ 目录、Makefile.am 无 TESTS、configure.ac 无测试宏），清点证据见 test_package/MANIFEST.yml；上游测试通过率记 0/0（不适用——上游 0 个可运行测试入口）。
2. L2 smoke（--version 可执行检查）按纯库包跳过：无 bin/ 目录（W3 日志披露 `L2_RESULT=skip: no bin/ dir`）。
3. RGB 颜色模式下 PGF 通道序为 BGR（上游 API 约定），消费者如需 RGBA 需经 channelMap 转换。
4. finish 的 G0 干净构建验证提示"找不到原始 tarball"（非阻塞警告）：本轮私有 CONAN_HOME 缓存布局下原始 zip 未留存于其预期位置；实际干净构建由 G2 conan create（全新源码下载+构建）覆盖并通过。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_libpgf（消费者程序，断言 5 项） | PGF 无损编解码往返 | ✅ PASS（0.02s） |

消费者断言明细（日志原文）：

```
PASS: encoded PGF stream is not empty
PASS: encoded stream smaller than raw 24bpp raster
PASS: decoded header keeps width/height
PASS: decoded header keeps channels/bpp/mode
PASS: lossless round trip restores every pixel
5 checks, 0 failures
```

W3 门禁结果（reports/w3-local-ci.log）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Pass rate: 100.0% (1/1)
```

L1e 破坏性反向验证：移走 lib/ 与 include/ 后 test_package 必然失败（`[ok] L1e: Negative test confirmed — test genuinely depends on libpgf`），确认消费者测试真实依赖被测包。

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| L2 smoke（--version 执行检查） | 纯库包无 bin/ 目录，无命令行入口可冒烟（W3 日志披露） |

---

## 四、关键问题分析

### 问题1: 首轮 W3 L0d 误判 stub_test_method

**现象**：
```
[fail] libpgf/7.21.7 — L0 quality gate failed: stub_test_method
```

**根因分析**：
L0d 以 `grep "self.run"` 检查 test_package/conanfile.py 的 test() 是否实际执行被测物；首版 test() 仅调用 `cmake.test()`，无该字面量。

**解决方案**：
test() 改为直接执行编译出的消费者二进制（`self.run(binary, env="conanrun")`），实跑证据强于 ctest 汇总；修复后 W3 全绿。提交 9d421587。

---

## 五、测试环境

```
libpgf 7.21.7（上游 SourceForge libpgf.zip, sha256 cba8f7cd…）
Conan 2.29.1（/storage/Users/currentUser/.local/bin/conan，OHOS 适配版）
profile: ci/conan/profiles/ohos-aarch64（clang 15, os=OHOS, arch=armv8, cppstd=17, libc++）
构建: conan create --build=missing（jobs=2, 私有 CONAN_HOME）
测试: test_package 消费者程序 test_libpgf（CMake + CMakeDeps/CMakeToolchain 消费 libpgf::libpgf）
```

---

*报告生成时间: 2026-09-18*
