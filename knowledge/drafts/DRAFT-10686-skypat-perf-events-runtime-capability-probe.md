# DRAFT: perf_event_open 编译可用但运行期被拒（EACCES）——头文件门控不足与优雅降级

- **草稿 ID**: DRAFT-10686-skypat-perf-events-runtime-capability-probe
- **来源库**: skypat 3.2.0（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18, HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 问题（三层，真机实测）

skypat 把 perf_events 计数与计时合入测试框架：`PERFORM(event)` 宏构造
`PerfIterator`，同时实例化 `internal::Timer` 与 `internal::Perf`。这两个类在
`HAVE_LINUX_PERF_EVENT_H` 下调用 `syscall(__NR_perf_event_open, ...)`。
在 OHOS 真机上是**"编译全通、运行全挂"**：

1. **头文件层（编译通过）**：OHOS sysroot 内
   `sysroot/usr/include/linux/perf_event.h` 存在，`configure` 的
   `AC_CHECK_HEADERS([linux/perf_event.h])` 判定为 yes；
   `asm/unistd.h` 也在（位于架构子目录
   `sysroot/usr/include/aarch64-linux-ohos/asm/unistd.h`，`__NR_perf_event_open=241`）。
   → `HAVE_LINUX_PERF_EVENT_H` 与 `HAVE_ASM_UNISTD_H` 均定义，编译无错。

2. **权限层（运行期被拒）**：真机上 `perf_event_open` 对 **HW 与 SW 事件一律**
   返回 `-1, errno=13 (EACCES)`：

   ```
   SW TASK_CLOCK: fd=-1 errno=13 (Permission denied)
   HW CPU_CYCLES: fd=-1 errno=13 (Permission denied)
   ```

   即便 `/proc/sys/kernel/perf_event_paranoid` 为 `-1`（无限制）依旧被拒——
   说明拦截来自内核/安全域策略（受限进程域），编译期能力检测无法发现。

3. **断言/未初始化层（静默错误数据）**：上游对 `fd=-1` 不做检查：

   ```cpp
   unsigned long long counter;
   read(m_Fd, &counter, sizeof(unsigned long long));   // 失败，counter 未初始化
   return counter;
   ...
   assert(-1 != m_Start && "fail to get performance counters");
   ```

   真机实测效果（未修复的 3.2.0 上游）：`examples/performance` 运行
   `[ TIME (ns)] 156863262856 156863262856 ...`（fib(10) 报 156.9 秒、各测量块
   数值完全一致），`[RESULT NUM]` 全 0；Release 为伪数据，未定义 NDEBUG 时
   断言可能随机中止。

## 根因

`AC_CHECK_HEADERS` 检测的是**头文件存在性**，与**运行期 syscall 权限**是两个维度；
OHOS 上二者分离（头文件在、权限无）。库作者常见的 `#if defined(HAVE_LINUX_PERF_EVENT_H)`
编译期门控在这种平台上给出"能力可用"的错误结论，而运行期失败路径没有任何降级逻辑，
`read()` 的返回值又未检查，于是失败被转化为未初始化读取（UB）与断言。

## 方案（推荐：运行期能力探测 + 优雅降级）

以 **fd 有效性**作为运行期能力位，全部逻辑保持通用（无平台宏）：

- `PerfImpl`：构造函数初始化 `m_Fd = -1`；`getCounter()` 在 `m_Fd < 0` 或
  `read()` 返回值不等于缓冲区大小时返回 0；`start()/stop()` 仅在 `m_Fd >= 0`
  时 `ioctl`；析构仅在 fd 有效时 `close`。首次 `perf_event_open` 失败时向
  stderr 报告一次原因（探测→降级→报告）。
- `TimerImpl`：同样维护 `m_Fd` 有效性；`clock()` 改为运行期分支——
  fd 有效时读 perf 计数器，否则回退到标准时钟链
  （`clock_gettime(CLOCK_MONOTONIC)` → `gettimeofday` → `times`）。
  原实现只有编译期 `#if/#elif`，运行期不可达。

补丁：`archives/s/skypat/3.2.0/patches/0001-lib-Support-Unix-Perf.inc.patch`、
`0002-lib-Support-Unix-Timer.inc.patch`（均为现有文件修改，`-p1` 可用）。

## 验证（真机命令与输出）

```sh
# 1) 最小探针：证明"编译可用、运行被拒"
cat > perf_probe.c <<'EOF'
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <linux/perf_event.h>
int main(void) {
  struct perf_event_attr attr; memset(&attr, 0, sizeof(attr));
  attr.type = PERF_TYPE_SOFTWARE; attr.config = PERF_COUNT_SW_TASK_CLOCK;
  attr.size = sizeof(attr); attr.disabled = 1; attr.inherit = 1;
  errno = 0;
  long fd = syscall(241, &attr, 0, -1, -1, 0);   /* aarch64 __NR_perf_event_open */
  printf("fd=%ld errno=%d (%s)\n", fd, errno, strerror(errno));
  return 0;
}
EOF
$CC perf_probe.c -o perf_probe && ./perf_probe
# 输出: fd=-1 errno=13 (Permission denied)

# 2) 框架级验证（修复前 vs 修复后，同一 PERFORM() 示例）
./performance/performance
# 修复前: [ TIME (ns)] 156863262856（常数级伪值）, [RESULT NUM] 0
# 修复后: [ TIME (ns)] 7656 20093125（真实递增）, [RESULT NUM] 0
#         stderr 报告一次 "skypat: perf_event_open is unavailable (errno=13); ..."
#         [  PASSED  ] 2 tests.
```

消费者测试（`test_package/test_skypat.cpp`）把该契约固化为回归断言：经
`CSVResultPrinter` 读取两个 `PERFORM()` 的真实间隔，断言 `0 < fast < 10s`、
`slept >= 20ms`、`slept > fast`——未修复的伪数据（各块相等且量级荒谬）无法通过。

## 适用边界

- 所有以 `perf_event_open`/perf_events 计数或计时的 C/C++ 库（性能测试框架、
  profiler、采样/缓存分析工具）——在"头文件存在但运行期权限被拒"的平台
  （OHOS 受限域、容器、LSM 限制的 Linux）都会命中同一模式。

### 本仓库语料内的对照与复用面

| 包 | 与 perf 的关系 | 对本条的意义 |
|----|----------------|--------------|
| `libcpucycles` 20260625（已合入） | 上游 backend selection 在运行期尝试 `arm64-perfpmc`/`default-perfevent`，失败走 SKIP 并回退 `arm64-pmc`/单调时钟 | **已自愈的对照实现**：证明"运行期失败可被安全吸收"；其 notes 亦已记录 OHOS perf 不可用事实（见查重差异） |
| `libpfm` 4.13.0（已合入） | 只做 PMU 事件**编码**（`pfm_get_event_encoding`），不打开计数器；其下游消费者才真正调用 `perf_event_open` | 判别参考："谁才是真正的 perf 使用者"；下游消费者在 OHOS 启用计数时会命中本条 |
| `google-benchmark` 1.9.5（已合入） | 上游具备 perf 计数器支持（硬件计数器路径）；当前适配未启用该功能 | **潜在复用面**：一旦在 OHOS 启用硬件计数器/采样即命中本条 |
| `strace`/`ltrace`/`bpftrace-tools`（已归档） | 追踪/采样家族，`knowledge/operations/ptrace-alternatives.md` 已证在受限域被阻止 | 广义同类：**运行期被安全域拒绝的能力**（ptrace/eBPF/io_uring 等）共享"探测→降级→报告"骨架 |

- 一般化为：**编译期能力检测（`AC_CHECK_HEADERS`/`#ifdef`）≠ 运行期可用性**，
  凡"探测到的能力在运行期可能失败"的库（GPU、后端设备、特权 syscall）都应
  使用"探测 → 降级 → 报告"骨架而不是裸调用 + 断言。

## 反例与限制

- **禁止**不检查 `read()` 返回码继续使用缓冲（UB；优化下行为不可预测）；
- **禁止**通过提权 / 修改 `/proc/sys/kernel/perf_event_paranoid` 来"修复"：
  超出三方库适配边界、CI 与用户环境不可复现；
- 降级语义必须诚实：计数器不可用时输出 0（本框架在头文件缺失时的既有语义），
  不能伪造或复用上一次的数值；
- 若无法修改源码，可在配置期强制关闭头文件门控
  （`ac_cv_header_linux_perf_event_h=no`）——代价是真机支持 perf 时也失去计数。

## 查重差异

### 与仓库既有记录的边界（先行记录 → 本条增量）

OHOS 上 perf 运行期受限并非首次出现，仓库内已有两处**先行记录**，本条目与其划清增量：

1. `archives/l/libcpucycles/20260625/notes.md`（已合入）：记录「OHOS 内核未开放用户态
   perf_event_open（syscall 返回 -1）」，其上游自带 backend selection + SKIP 语义、
   未造成故障。该记录完成了"事实告知"（本轮实测复核为真），但缺少三点：
   ① errno 级语义（HW/SW 事件均 `-1/EACCES`，且 `perf_event_paranoid=-1` 不放行）；
   ② "无运行期处理"时的失效模式（未初始化读取 → 伪时长/断言中止，即本条目问题面）；
   ③ 可复制的运行期探测 + 双通道降级实现模板与回归测试方法。**本条补全 ①②③。**
2. `knowledge/operations/ptrace-alternatives.md`：记录「perf 不可用……`perf_event_paranoid`
   可能也被锁定」——该结论**不精确**：实测 `perf_event_paranoid` 可读且为 `-1`，被拒的
   是 `perf_event_open` syscall 本身（安全域策略）。本条以 errno 级实测修正该认知，
   并给出精确验证命令（见"验证"节探针）。

### 与正式条目的差异

- **E270**（`CLOCK_SGI_CYCLE` declared but unsupported at runtime）：同为"运行期
  拒绝时回退时钟"，但 E270 是 `clock_gettime` 特定时钟源返回 `EINVAL`、主体是
  时钟源选择；本条是 `perf_event_open` 系统调用被安全域以 `EACCES` 拒绝、
  主体是**权限型能力探测 + 未初始化读取修复**，且额外覆盖断言与伪数据问题。
- **E303**（受限域 `opendir("/")` EACCES 误判）：同为"受限域拒绝 + 运行期能力
  判断"的理念，但 E303 是文件系统身份探测（hostfs/GRUB），本条是性能计数
  系统调用；两者共享原则 P013/P015，不构成重复。
- **E008**（鸿蒙 SELinux 策略对管道/终端/套接字 `fstat()/lseek()` 返回 EACCES）：
  同为"受限域 syscall 权限"家族，但 E008 是被动受影响的 libc 调用（返回码语义
  差异），本条是**主动能力自检与降级策略**（fd 有效性 + 时钟回退 + 报告），
  且额外覆盖未初始化读取与断言中止问题。
- **E387**（LLVM lit 测试框架适配）：不同域（测试驱动/工具链），与本条无重叠。
- **E011**（HMDFS `umask 077` 临时目录）：本包构建期使用 mktemp wrapper 规避，
  属 E011 的既有覆盖面（cln 1.3.7 已补 `mktemp -d` 变体），不重复入库。

### 增量声明（与原则的关系）

库内已有原则 P013（平台限制必须降级而非绕过）与 P015（内核 syscall 行为差异必须源码适配），
本条**不主张新原则**。其增量是：把该原则落到"**测量类能力的双通道语义**"上的具体治理——
计数通道不可用（诚实 0）与计时通道必须可用（真实时钟）**分离降级**，辅以 fd 有效性探测、
一次性报告，以及"用库自身输出通道（CSV）做测量语义契约回归"的测试方法。这是既有原则
在 perf 场景下缺失的实现模板与失效模式，而非原则本身的重复。

## 参考

- 上游源码：`lib/Support/Unix/Perf.inc`、`lib/Support/Unix/Timer.inc`
  （<https://github.com/skymizer/SkyPat/blob/v3.2.0/lib/Support/Unix/Perf.inc>）
- 本仓库归档：`archives/s/skypat/3.2.0/`（补丁、消费者测试、notes.md 实测输出）
- 探针对象：aarch64 `__NR_perf_event_open=241`（asm-generic syscall 表）
