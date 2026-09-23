# 测试报告 — runlim 1.10（HarmonyOS PC / aarch64）

> **项目**: runlim 1.10（https://fmv.jku.at/runlim/）
> **测试日期**: 2026-09-20
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64（HAD-W32），OHOS SDK clang 15.0.4
> **测试类型**: 上游测试清点（0 用例）+ 消费者功能测试（test_package，31 条断言）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试总数 | 0 | — |
| 上游通过 (PASS) | 0 | — |
| 适配新增测试总数 | 31 | 100% |
| 新增通过 (PASS) | 31 | 100% |
| 新增失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（31/31）**

> 上游 runlim 1.10 **不含任何测试套件**：解压树无 tests/ 目录、`makefile.in` 仅定义 runlim/clean
> 两个目标（无 check）、`configure.sh` 无测试开关，实测 `make check` 报 "No rule to make target"
> （R51 清点证据见 `test_package/MANIFEST.yml` 与 `notes.md`）。按 R51「上游无测试」场景，
> 由 `test_package/test_runlim.sh` 补 31 条消费侧功能断言。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。包可用、可安装、限制行为符合上游文档；31/31 消费者断言通过，包含 CI L1e
破坏性反向验证（移除 bin/ 后测试必须失败，实测确认测试真实依赖被测二进制）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 RLIMIT_AS 单位缺陷（已由补丁 0001 修复并回归验证） | `-t`/`--time-limit`（及 `-t -s`）路径 | 🟢（修复后正常） |

### 2.3 可用功能清单

```
✅ 进程树资源采样：/proc 采样 CPU 时间/墙钟时间/常驻内存（RSS），输出 time/real/space/samples
✅ CPU 时间限制 -t/--time-limit（RLIMIT_CPU + 采样击杀，rc=2）
✅ 墙钟时间限制 -r/--real-time-limit（采样击杀，rc=2）
✅ 内存限制 -s/--space-limit（采样击杀 rc=3；配合 -t 时同时设置 RLIMIT_AS）
✅ 日志文件 -o/--output-file（默认 stderr）
✅ 信号传播 -k/--kill（子进程信号传播给 runlim 自身）
✅ 错误路径：非法选项/缺程序/缺数字参数（rc=1 + 诊断信息）
✅ runlim 自身状态码语义：0 ok / 1 exec 失败 / 2 out of time / 3 out of memory / 4 SIGSEGV / 11 其他信号
```

### 2.4 已知限制

1. 上游无测试套件，回归保护依赖本包新增的 `test_package/test_runlim.sh`（31 断言）。
2. 子进程退出码不转发（上游设计：返回 runlim 自身状态码）；消费脚本若需子进程退出码需自行包裹。
3. 需要 Linux/OHOS 风格 `/proc`（上游设计）。

---

## 三、测试详情

### 3.1 通过的测试（test_package/test_runlim.sh，31/31）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | runlim 二进制已安装并在 PATH 上 | ✅ PASS |
| 2 | `runlim --version` 退出码 0 | ✅ PASS |
| 3 | `runlim --version` 输出 "1.10" | ✅ PASS |
| 4 | `runlim -h` 退出码 0 | ✅ PASS |
| 5 | `-h` 输出含 "usage: runlim" | ✅ PASS |
| 6 | 非法选项退出码 1 | ✅ PASS |
| 7 | 非法选项有 "invalid option" 诊断 | ✅ PASS |
| 8 | 缺程序退出码 1 | ✅ PASS |
| 9 | 缺程序有 "no program specified" 诊断 | ✅ PASS |
| 10 | `-t` 缺数字参数退出码 1 | ✅ PASS |
| 11 | 缺数字参数有 "number argument" 诊断 | ✅ PASS |
| 12 | pass-through 运行退出码 0 | ✅ PASS |
| 13 | 子进程 stdout 透传 | ✅ PASS |
| 14 | `-o` 日志记录版本 | ✅ PASS |
| 15 | `-o` 日志记录 ok 状态 | ✅ PASS |
| 16 | 子进程退出码被忽略（status ok = 0） | ✅ PASS |
| 17 | `-r 1` 实时限制退出码 2 | ✅ PASS |
| 18 | `-r 1` 日志含 "out of time" | ✅ PASS |
| 19 | `-t 1` CPU 限制退出码 2（RLIMIT_AS 修复回归） | ✅ PASS |
| 20 | `-t 1` 日志含 "out of time" | ✅ PASS |
| 21 | `--time-limit=1` 退出码 2 | ✅ PASS |
| 22 | `--real-time-limit=1` 退出码 2 | ✅ PASS |
| 23 | `-s 1` 空间限制退出码 3 | ✅ PASS |
| 24 | `-s 1` 日志含 "out of memory" | ✅ PASS |
| 25 | `--space-limit=1` 退出码 3 | ✅ PASS |
| 26 | 子进程 SIGSEGV 退出码 4 | ✅ PASS |
| 27 | SIGSEGV 日志含 "segmentation fault" | ✅ PASS |
| 28 | `-k` 信号传播（退出码 139） | ✅ PASS |
| 29 | 默认运行退出码 0 | ✅ PASS |
| 30 | 子进程 stdout 保持在 stdout | ✅ PASS |
| 31 | 默认日志输出到 stderr | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（上游 0 用例，无需跳过）。

---

## 四、关键问题分析

### 问题1: `runlim -t` 恒报 `execvp failed`（rc=1）——RLIMIT_AS 单位缺陷

**现象**：
```
$ runlim -t 1 sh -c 'i=0; while [ $i -lt 100000000 ]; do i=$((i+1)); done'
[runlim] time limit:		1 seconds
[runlim] status:		execvp failed
[runlim] result:		1
```

**根因分析**：
runlim.c 在 `time_limit < real_time_limit` 时给子进程设置两个 rlimit：
`setrlimit(RLIMIT_CPU, time_limit)`（秒，正确）与
`setrlimit(RLIMIT_AS, space_limit)`——但 `space_limit` 的单位是 **MB**（usage 与采样比较均为 MB，
默认值来自 `get_physical_mb()`），内核 RLIMIT_AS 的单位是 **字节**。于是子进程地址空间被限制在
~31 KB（31914 字节），`execvp` 在装载解释器/动态库时失败 ENOMEM，子进程随即 `kill(getppid(), SIGUSR1)`，
runlim 判定 EXEC_FAILED 返回 1。`-r`（或默认，time_limit == real_time_limit）不触发该 setrlimit 块，
因此不受影响——这正是「只有 -t 失败」的原因。

最小复现（设备实测）：
```
setrlimit(RLIMIT_AS, 31914) 后 execv("/bin/echo") → exec failed: errno=12 Out of memory
setrlimit(RLIMIT_AS, 31914<<20) 后 execv("/bin/echo") → hi-from-exec（成功）
```

**解决方案**：
补丁 `0001-runlim.c.patch`（+1/-1 行，纯单位修复，无平台宏）：
```diff
-	l.rlim_cur = l.rlim_max = space_limit;
+	l.rlim_cur = l.rlim_max = ((rlim_t) space_limit << 20);
```
修复后设备实测：`runlim -t 1 <CPU 忙循环>` → rc=2 "out of time"（time 1.01s，samples 10）；
该用例已固化为 test_package 第 19/20 条断言（未修复的构建会得到 rc=1，测试必失败）。

### 问题2: OHOS `/proc/<pid>/stat` 字段布局核验（采样正确性）

**现象/核验**：runlim 按固定索引解析 `/proc/<pid>/stat`（vsize=field 23、rss=field 24、
utime/stime=field 14/15）。需要确认 HongMeng Kernel 1.12 的布局一致，否则采样与限制会失真。

**实测**（设备，同一时刻对照）：
```
/proc/<pid>/stat field 23 = 2179141632 == VmSize (2128068 kB)
/proc/<pid>/stat field 24 = 1269 == statm resident（页），VmRSS 5076 kB
/proc/<pid>/stat field 14/15 = utime/stime（jiffies）
```
**结论**：布局与标准 Linux 一致，无需适配。行为侧证：`-r 1` 采样击杀 time=0.72s/real=1.03s、
`-s 1` 采样击杀 rc=3（space 9.1 MB）均符合预期。

---

## 五、测试环境

```
OS:        HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
Compiler:  OHOS SDK clang 15.0.4 (aarch64-linux-ohos)
Conan:     2.29.1 (OHOS-adapted)
Profile:   ohos-aarch64-device
Source:    runlim-1.10.tar.gz (sha256 619aec701e9984977832e2db2bf05cef82ad6ac4ca53b595863bec115b69bc33)
Artifacts: bin/runlim; licenses/LICENSE
```

**验证链路**（全部实测）：
- `conan-verify`：G0–G4 全 PASS（reports/conan-verify-report.md）
- 本地 CI 门禁 `ci/conan/build_and_test.sh`：L0 pass、L1 pass（含 L1a/L1b/L1e 破坏性反向验证）、
  L2 pass、L4 pass（补丁扫描无危险调用）、L5 pass；`conan create` 内 test_package 31/31
- 设备手工探针（修复前/后对照、/proc 布局核验、各限制路径 rc 实测，见 notes.md）

---

*报告生成时间: 2026-09-20*
