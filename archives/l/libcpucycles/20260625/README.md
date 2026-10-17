# libcpucycles 20260625 — HarmonyOS PC (OHOS aarch64) Conan 适配

## 上游

- 官方主页: <https://cpucycles.cr.yp.to>
- 官方源码仓库: <https://git.cr.yp.to/cpucycles/>（镜像: c9s.me/git/libcpucycles）
- 版本: 20260625
- 源码 tarball: <https://cpucycles.cr.yp.to/libcpucycles-20260625.tar.gz>
- SHA256: `74a815bfb5ab645e5d07617125824c946ce5039db139e5233467d1ff33f69afa`
- License: Unlicense（公共领域，无任何条件）
- 构建系统: `./configure`（python3 脚本）+ `scripts-build/` + Makefile

## 包信息

Conan 2 recipe，面向 HarmonyOS PC（aarch64-unknown-linux-ohos / musl）。

| | |
|---|---|
| 聚合位置 | `archives/l/libcpucycles/` |
| 版本目录 | `archives/l/libcpucycles/20260625/` |
| 上游测试 | 无正式测试套件（见下） |
| patch 数 | 0 |
| 本包 test_package | 1 个 suite（10 断言，API 契约测试） |

## OHOS 适配要点

1. **零 patch**：上游 20260625 在 OHOS aarch64 上无需任何源码修改。

2. **交叉编译安全性**：上游 `./configure`（python3 脚本）的全部探测都是
   **compile-only**（`try-*.c` 只用 `$CC` 试编译判断符号/头文件存在性，
   从不运行 target 二进制）。工具链注入仅通过环境变量：
   `CC`/`CFLAGS`/`AR`/`RANLIB`。无 `--host` 参数（上游没有这个概念）。

3. **后端选择 100% 运行时**：8 个后端（arm64-perfpmc/arm64-pmc/arm64-vct/
   default-perfevent/default-mach/default-monotonic/default-gettimeofday/
   default-zero）由 `cpucycles_init()` 在首次调用时逐个 `sigsetjmp` 实测
   （捕获 SIGILL/SIGFPE/SIGBUS/SIGSEGV/SIGABRT），选精度最高者。构建期
   **无任何**硬件能力探测或后端硬编码——这正是本库的设计核心，无需
   OHOS 特殊处理。

4. **make install 不可用 → 直接收集产物**：上游 `scripts-build/install`
   在 OHOS hmfs 文件系统上失败：它在目标目录内创建 `tempfile.TemporaryDirectory`
   （umask 077 + setgid 目标目录 → 临时目录 mode 0700 且属主为另一个 uid），随后
   `copy2` 抛 `PermissionError [Errno 13]`。该脚本除了 copy+rename 外无编译
   动作，recipe 因此直接从 `build/arm64/package/` 收集产物，语义等价。

5. **musl 兼容性**：无问题。后端源码仅用 POSIX API（`clock_gettime`、
   `gettimeofday`、`perf_event_open`、`mrs` 指令），全部在 musl 中存在。

## 实测结果（OHOS PC, aarch64-unknown-linux-ohos, clang 15）

`cpucycles-info` 两次运行（本机即 OHOS aarch64 PC）：

```
cpucycles version 20260625
cpucycles tracesetup 0 arm64-perfpmc precision 0 scaling 0.000000 only32 0
cpucycles tracesetup 1 arm64-pmc precision 2 scaling 1.000000 only32 0
cpucycles tracesetup 2 arm64-vct precision 1400 scaling 2.500000 only32 0
cpucycles persecond 2399987654
cpucycles implementation arm64-pmc
```

- **选择的后端**: `arm64-pmc`（`MRS PMCCNTR_EL0`，用户态可直接访问）
- **精度**: 1-2 cycles（两次运行 precision 2/1）
- **arm64-perfpmc 失败原因**（真实不适用，非跳过）：`perf_event_open`
  syscall 返回 -1（OHOS 内核未开放用户态 perf events），上游语义返回
  `cpucycles_SKIP` → 后端被正确跳过
- **fallback 链**: default-perfevent 同因 SKIP；default-monotonic 可用
  （precision 1394）但精度低于 arm64-pmc，未被选择
- persecond fallback: `/proc/cpuinfo`、`/sys/.../cpufreq` 均不可读 →
  落到硬编码 2399987654（上游设计的最终 fallback）

## 上游测试调查

上游 libcpucycles **无正式测试套件**：

- 无 `test/`、`tests/` 目录
- 无 `make check` / `make test` 目标（Makefile 仅 all/install/clean）
- 无 CI 配置（无 .github/、.gitlab-ci 等）
- README 无测试运行说明
- `command/cpucycles-info` 是信息工具，不是测试
- `cpucycles/try-*.c` 是 configure 的 compile-only 探测程序（不运行），
  不计入正式测试

因此 upstream test Total = 0，消费者验证由本包 `test_package/` 承担
（API 契约测试，见 `test_package/MANIFEST.yml`）。

## test_package 设计

契约来源：上游 `doc/man/cpucycles.3` + `cpucycles/wrapper.c` 语义。

| # | 断言 | 依据 |
|---|------|------|
| 1 | `version == "20260625"` | wrapper.c 硬编码 |
| 2 | `implementation != NULL && != ""` | man 页：返回计数器名称 |
| 3 | `implementation` 指针稳定 | wrapper.c: static const char *implementation |
|  INFO | 首次 `cpucycles()` 宥忍任何值 | man 页：懒初始化，无错误路径 |
| 4 | implementation 属于 8 个已知后端 | options.inc (aarch64) |
| 5 | `persecond > 0` | osfreq() 永远 > 0（最终 fallback 2399987654.0） |
| 5/6 | 1000 次读取至少一次严格递增 | 上游选择循环自身接受标准 t[0]!=t[CALLS] |
| 6 | 1000 次连续读取非递减 | 上游选择循环自身标准 t[i]<=t[i+1] |
| 7 | `persecond()` init 后返回缓存值不变 | wrapper.c: persecond 在 init 中一次计算存 static |
| 8 | persecond 在频率量级 [1e6, 1e12] | man 页："cycles per second 的估计值" |
| 9 | tracesetup() 后 impl/persecond/紧循环读数不变 | wrapper.c: 只置静态标志，init 后无副作用 |

共 **10 个 CHECK 断言**（外加 1 个 INFO 行）。

设计上**不**断言：后端选择结果（环境决定）、精确周期差值（机器性能）、
persecond 为真实频率（上游只保证 estimate）、**跨 sleep/调度点的单调性**
（arm64-pmc 读 per-core PMCCNTR_EL0，线程迁核后计数器起点不同；上游
wrapper.c 注释明确承认 "core swap" 会导致跳变——所有 read-to-read 断言
限定在连续紧循环内，与上游选择循环自身的接受标准一致）。

## 验证状态

- [x] `conan create` 编译成功（OHOS aarch64, clang 15）
- [x] ELF64 / AArch64 / PIE / interpreter `/lib/ld-musl-aarch64.so.1`
- [x] 动态库 NEEDED 仅 `libc.so`
- [x] test_package 真实运行（L1e 破坏性测试见证依赖）
- [x] Runtime backend selection: arm64-pmc 被真实执行
- [x] Scoped CI 全门禁通过（G0/G0e/KC/JC/L0/L1/L4/L5 pass，L2 skip 预期：纯库无 bin/）
- [x] `git diff --check` 无问题

## 使用

```bash
conan create . --build=missing -pr:h=ohos-aarch64-local
```

更多适配细节见 `notes.md`。
