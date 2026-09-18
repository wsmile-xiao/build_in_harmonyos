# skypat 3.2.0 测试报告

> **项目**: skypat 3.2.0（C++ 性能分析与单元测试框架）
> **测试日期**: 2026-09-16
> **测试环境**: HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64（clang 15.0.4, OHOS SDK 26.0.0.18, Conan 2.29.1 OHOS 适配版）
> **测试类型**: 适配回归消费者测试（上游无官方测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游官方测试 | 0（无 tests/、无 check/TESTS 注册） | — |
| 消费者测试（test_package） | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**（2/2 测试；6 个框架断言 + 6 项运行期校验全通过）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 库在 OHOS aarch64 可构建、可链接、可运行；单元测试/断言/监听器/CSV 输出全部可用；
`PERFORM()` 在 perf_event_open 被内核拒绝（EACCES）的环境下按契约优雅降级（计时真实、计数诚实为 0、不中止）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OHOS 运行期拒绝 perf_event_open（EACCES，HW/SW 均拒绝） | `PERFORM()` 的 perf 事件计数不可用（框架降级为 0）；计时不受影响 | 🟡 |
| 上游异常规范不匹配（`tryLock()` 缺 `throw()`） | C++17 工具链下编译失败（profile cppstd=17） | 🟢（已修复） |

### 2.3 可用功能清单

```
✅ 测试注册与运行: SKYPAT_F / SKYPAT_C / Test::Initialize / Test::RunAll
✅ 断言: EXPECT_* / ASSERT_* 全家族、SKYPAT_MESSAGE、自定义 Listener
✅ 性能测量: PERFORM() 计时（真实时钟回退），多事件枚举
✅ 结果输出: Pretty 控制台（PASSED/FAILED 汇总）、CSVResultPrinter（-c <file>）
⚠️ perf 硬件/软件事件计数: OHOS 运行期权限拒绝时为 0（诚实降级，stderr 报告一次）
❌ 无: 无
```

### 2.4 已知限制

1. OHOS 上 `perf_event_open` 运行期返回 `EACCES`，硬件/软件事件计数不可用：
   `[RESULT NUM]` 输出 0，`PERFORM()` 仅提供时间维度；库会向 stderr 打印一次原因。
2. 上游发布包不含任何自动化测试（`--enable-unittest` 开关无实现），无历史通过率可对比。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `ConsumerFixture.assertions_evaluate`（SKYPAT_C fixture） | fixture SetUp 状态、EXPECT_EQ/NE/LT/GE、ASSERT_TRUE 共 5 断言 | ✅ PASS |
| `ConsumerFixture.perform_reports_plausible_intervals`（SKYPAT_F） | 两个 `PERFORM()` 时段（快体 + `Sleep(20)`）；断言执行 + CSV 间隔校验（0<fast<10s、slept≥20ms、slept>fast） | ✅ PASS |

**运行实测证据**（conan create 的 test_package 阶段，CSVResultPrinter 输出）：

```
perform_reports_plausible_intervals,5156,20227968
```

**真机直接运行（examples + 消费者程序）**：

```
skypat: perf_event_open is unavailable (errno=13); performance counters are disabled
skypat: perf_event_open is unavailable (errno=13); falling back to clock-based timing
[ TIME (ns)] 7656 20093125
[RESULT NUM]            0            0
[  PASSED  ] 2 tests.
skypat consumer test: PASSED (2 tests, PERFORM() intervals 12656 ns / 20269218 ns)
```

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 上游官方测试套件 | 上游发布包内不存在（无 tests/ 目录；顶层 Makefile.am SUBDIRS 仅 include/lib/examples；`make -n check` 无检查程序注册；`--enable-unittest` 的 AM_CONDITIONAL 无引用） |

---

## 四、关键问题分析

### 问题1: OHOS 运行期拒绝 perf_event_open 导致伪时长/未初始化读取

**现象**：
```
# 未修复的上游 3.2.0（真机 examples/performance）:
[ TIME (ns)] 156863262856 156863262856 156863262856 156863262856 156863262856
[RESULT NUM]            0            0            0            0            0
# 其中 fib(10) 不应耗时 156 秒；且各测量块数值完全相同
```

**根因分析**：
`linux/perf_event.h` 与 `__NR_perf_event_open(=241)`（`sysroot/usr/include/aarch64-linux-ohos/asm/unistd.h`）
均存在，configure 编译期门控 `HAVE_LINUX_PERF_EVENT_H=1`，但真机 `perf_event_open` 对
HW/SW 事件一律返回 `-1, errno=13 (EACCES)`（`/proc/sys/kernel/perf_event_paranoid=-1` 也不放行）。
上游对 `fd=-1` 不检查，`read()` 未初始化栈缓冲并以 `assert` 兜底：Release 输出伪数据，Debug 可能中止。

**解决方案**：
补丁 0001/0002 改为运行期能力探测：`fd<0` 时跳过 read/ioctl、计数返回 0，计时按
`fd 有效 → perf 计数器；否则 clock_gettime/gettimeofday` 的运行期分支回退，并 stderr 报告一次。
`test_package` 以 CSV 间隔校验（递增且量级正确）把该契约固化为回归测试。

### 问题2: C++17 下 `Mutex::tryLock()` 异常规范缺失

**现象**：
```
lib/Thread/Pthread/Mutex.inc:46:22: error: 'tryLock' is missing exception specification 'throw()'
```

**根因分析**：
OHOS profile `compiler.cppstd=17` 的 `-std=c++17` 位于编译命令尾部，覆盖 Makefile 内的 `-std=c++11`；
C++17 将异常规范纳入函数类型，声明（`Mutex.h: Status tryLock() throw();`）与定义不匹配即硬错误。

**解决方案**：
补丁 0003 为定义补 `throw()`（与声明一致；`lock()`/`unlock()` 上游本就匹配），不改工具链参数。

---

## 五、测试环境

```
skypat 3.2.0（首次适配版本 3.2.0）
构建: GNU Autotools（autogen.sh 引导 → configure --build/--host=aarch64-unknown-linux-gnu
      --without-zlib --enable-clock_gettime --enable-shared --disable-static → make -j1）
工具链: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18, libc++, cppstd=17）
Conan: 2.29.1（OHOS 适配版），profile ohos-aarch64-device
设备: HarmonyOS PC aarch64 / HongMeng Kernel 1.12.0（3120x2080）
验证: conan-verify G0-G4 PASS；test_package 经 conan create 实跑通过
```

---

*报告生成时间: 2026-09-16*
