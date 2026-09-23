# notes — libcpucycles 20260625 OHOS aarch64 适配

本文记录适配过程的关键决策与证据，供后续审计与复用。

## 1. 上游核验（官方事实，非第三方）

| 项 | 值 |
|---|---|
| 官方主页 | https://cpucycles.cr.yp.to |
| 源码仓库 | git.cr.yp.to/cpucycles |
| 版本 | 20260625（wrapper.c `cpucycles_version()` 返回值） |
| tarball URL | https://cpucycles.cr.yp.to/libcpucycles-20260625.tar.gz |
| SHA256 | 74a815bfb5ab645e5d07617125824c946ce5039db139e5233467d1ff33f69afa |
| License | Unlicense（公共领域；源文件头 "public domain"） |
| 构建系统 | ./configure (python3) + scripts-build/ + Makefile |

版本一致性：tarball 内各文件头日期为最后修改日期（wrapper.c 20260625、
options.inc 20251226、cpucycles.h 20230115、arm64-*.c 20251226），以
`cpucycles_version()` 硬编码 "20260625" 为准。

## 2. 上游测试调查（upstream test Total = 0）

| 搜索位置 | 结果 |
|---|---|
| test/ tests/ | 不存在 |
| Makefile 目标 | 仅 all / install / clean |
| configure | python3 脚本，无 test 目标，无 try-run |
| cpucycles/try-*.c | configure 的 compile-only 探测，不运行 |
| CI 配置 (.github/ 等) | 不存在 |
| README / doc | 无测试运行说明 |
| command/cpucycles-info | 信息工具，不是测试 |
| command/cpucycles-open | 工具，非测试 |

结论：上游无正式测试套件，无 make check/test。消费者验证由本包
test_package 承担（API 契约测试，10 断言，见 test_package/MANIFEST.yml）。

### 2.1 test_package 断言设计原则（重要修正记录）

初版 test.c 有两个断言违反 API 契约，真实运行失败后删除：

- ~~persecond-consistency~~：50ms nanosleep 前后 dc 与 persecond*0.05
  交叉验证。失败原因：arm64-pmc 读 per-core PMCCNTR_EL0，sleep 期间
  线程迁核，新核计数器起点不同（实测 7.4e13 < 睡前 1.4e14）。上游
  wrapper.c 选择循环注释明确承认 "!ok can be caused by overflow or
  by core swap"。跨 sleep 的单调性不在 API 保证内（man page："an
  estimate ... since an unspecified time in the past"）。
- ~~after >= maxv~~（tracesetup 检查的旧形式）：同样跨 sleep 断言。

修正后原则：所有 read-to-read 断言限定在连续紧循环内——与上游选择
循环自身的后端接受标准一致（CALLS 次读取非递减）。替换为
persecond-stable（init 后缓存值不变）、persecond-plausible（频率
量级 [1e6,1e12]）、tracesetup 后 impl/persecond/紧循环读数不变。

## 3. CPU/OS 能力探测机制分析（本库核心）

### 3.1 configure 阶段（构建期）— compile-only，交叉安全

上游 configure 的探测方式：对每个 try-*.c（编译器探测、头文件探测等）
只执行编译判断可用性，从不运行 target 二进制。configure 输出可直接
观察："skipping default compiler gcc" → "using compiler clang"。

- arm64-pmc / arm64-vct：纯 asm（MRS 指令），无条件编译进库
- arm64-perfpmc / default-perfevent：依赖 `linux/perf_event.h`，OHOS
  sysroot 中存在（musl 提供），可编译
- default-mach：仅 macOS；default-monotonic / default-gettimeofday：POSIX

对 OHOS 的含义：
- 无需 --host 参数（上游无此概念），工具链仅靠 CC/CFLAGS/AR/RANLIB 注入
- 无需把 OHOS 特殊对待为 Linux GNU；musl sysroot 的 perf_event.h 足以编译
- configure 从 `clang -dumpmachine` 得 aarch64-unknown-linux-ohos → arch=arm64
  （build 树目录名 build/arm64/ 为证）

### 3.2 运行时 — backend selection 100% 目标机上执行

`cpucycles_init()`（wrapper.c）流程：
1. `persecond = osfreq()`：按序尝试 /etc/cpucyclespersecond →
   /sys/.../cpufreq → /proc/cpuinfo → sysctl → env cpucyclespersecond →
   硬编码 2399987654.0（最终 fallback，永远为正）
2. 逐个后端 `ticks_setup()`（SIGILL/SIGFPE/SIGBUS/SIGSEGV/SIGABRT 由
   sigsetjmp 捕获，abort 即判不可用）
3. 每个可用后端实测 1000 次读取算 precision（最小正增量），选最优
4. 保底 default-zero（恒 0，仅当全部失败才可能被选）

OHOS 实测（cpucycles-info，本机即 OHOS aarch64 PC，两次独立运行，完整
原始输出留存于适配工作目录）：

```
cpucycles version 20260625
cpucycles tracesetup 0 arm64-perfpmc precision 0 scaling 0.000000 only32 0
cpucycles tracesetup 1 arm64-pmc precision 2 scaling 1.000000 only32 0
cpucycles tracesetup 2 arm64-vct precision 1400 scaling 2.500000 only32 0
cpucycles tracesetup 3 default-perfevent precision 0 scaling 0.000000 only32 0
cpucycles tracesetup 4 default-mach precision 0 scaling 0.000000 only32 0
cpucycles tracesetup 5 default-monotonic precision 1394 scaling 2.399988 only32 0
cpucycles tracesetup 6 default-gettimeofday precision 3429 scaling 2399.987654 only32 0
cpucycles tracesetup 7 default-zero precision 0 scaling 0.000000 only32 0
cpucycles persecond 2399987654
cpucycles implementation arm64-pmc
```

结论：
- 选择 **arm64-pmc**（MRS PMCCNTR_EL0，用户态可访问，精度 1-2 cycles）
- arm64-perfpmc / default-perfevent 失败是**真实不适用**：OHOS 内核
  未开放用户态 perf_event_open（syscall 返回 -1），上游语义返回 SKIP
- default-mach SKIP 是设计行为（非 macOS）
- fallback（default-monotonic）真实执行：precision 1394 是它被真实运行
  并测量的证据；未被选择仅因 arm64-pmc 精度更高
- persecond 落到硬编码 2399987654（/proc/cpuinfo 等不可读，上游设计
  的最终 fallback）

## 4. 交叉编译关键问题清单

| 问题 | 答案 |
|---|---|
| configure 是否运行 target 程序 | 否（compile-only） |
| compiler 是否正确选择 OHOS clang | 是（configure 输出 + ELF interpreter musl） |
| --host/target arch 是否正确识别 | arch=arm64（-dumpmachine → aarch64-unknown-linux-ohos） |
| 是否把 OHOS 错当 Linux GNU | 否（无 glibc 特有依赖；musl sysroot） |
| Linux 私有 API 是否造成问题 | perf_event_open 运行时不可用 → 上游自带 SKIP，无影响 |
| ARM cycle counter OHOS 用户态可否访问 | 可以（PMCCNTR_EL0，实测选中） |
| 失败后端有无安全 fallback | 有（上游设计：单调时钟/ gettimeofday / zero 链） |
| fallback 是否真实工作（非仅编译通过） | 是（default-monotonic precision 1394 实测） |

## 5. install 失败分析与绕过

上游 scripts-build/install 流程：
1. mkdtemp 在目标目录内创建临时目录
2. shutil.copy2 拷贝产物 → rename

OHOS hmfs 行为（实测）：
- mktemp 本身不失败（TMPDIR 指向可写目录可绕过 /tmp 只读）
- 失败点：临时目录 mode 0700（umask 077）+ setgid 目标目录（02751）→
  copy2 抛 PermissionError [Errno 13]

绕过方式（recipe 已采用）：跳过上游 install，直接收集
build/arm64/package/。上游 install 无编译动作（纯 copy+rename），
语义等价。

## 6. ELF / triple 验证

- ELF64 / AArch64 / PIE（Type: DYN）— cpucycles-info 与 libcpucycles.so.1
- interpreter: `/lib/ld-musl-aarch64.so.1`（OHOS musl 运行时）
- libcpucycles.so.1 NEEDED 仅 libc.so；SONAME libcpucycles.so.1
- cpucycles-info NEEDED: libcpucycles.so.1 + libc.so
- compiler target: aarch64-unknown-linux-ohos（clang -dumpmachine）

## 7. 路径 B 知识库查重（已完成，结论：不创建 draft）

已用关键词搜索整个 knowledge/（graph + doc + drafts + operations，1197 文件）：
cross compile probe / try_run / configure run target / CPU feature /
runtime detection / runtime dispatch / runtime fallback / backend
selection / aarch64 / arm64 / perf_event / cycle counter / hardware
capability / Linux API fallback / target probe / feature detection /
clock_gettime / gettimeofday / monotonic / sysctl / mkdtemp / setgid。

最接近的既有知识：

| 既有条目 | 覆盖内容 | 与候选方向的差异 |
|---|---|---|
| E159 / E459 | CMake TRY_RUN 交叉编译不能运行 target 二进制 | 解法是构建期预填 cache，不是延迟到运行时 |
| E007 / E064 / E082 / E122 / E197 / E293 | autotools --host 误判交叉编译 → AC_RUN_IFELSE 跳过 | 平台识别问题，非能力探测框架 |
| E320 | fmemopen 链接期存在运行期失效，configure 真跑探测 | 单点修复，方向相反（主张 configure 期运行探测） |
| E100 | libjpeg-turbo SIMD 平台未识别 → 禁用 | 构建期静态禁用，无运行时选择 |
| E270 | CLOCK_SGI_CYCLE 声明存在运行期 EINVAL → 回退 CLOCK_MONOTONIC | 单点时钟补丁，非可推广的 backend 链方法论 |
| E412 | 可选加速后端须在 recipe 显式声明 | 依赖图卫生问题，非 CPU/OS 能力探测 |
| E011 / E112 / E114 / E118 / E129 / E206 / E533 | HMDFS setgid/umask 临时目录 Permission denied | **本次唯一实际问题的根因类，已覆盖** |

不创建 draft 的理由：

1. 候选方向门控条件"实际问题出现并解决"未满足：上游 libcpucycles
   本就是 compile-only 探测 + 运行时 backend selection，本次适配没有
   出现"构建期执行 target probe"问题需要解决，无 problem→repair 可记。
2. 实际发生的唯一问题（HMDFS 上游 install PermissionError）属于既有
   HMDFS setgid/umask 知识类（上表第 7 行），新建条目等于复制现有
   知识改标题（规则明令禁止）。
3. perf_event_open 用户态不可用（syscall -1）未造成任何失败（上游
   SKIP 语义按设计工作）；OHOS perf 不可用事实已记录在
   operations/ptrace-alternatives.md。

路径 B 不强行申报。

### 7.1 后续实际出现的新问题（2026-09-03 补充）

上表查重完成后，在 20260902 归档的 test_package 长跑中实际出现并解决了
一个新问题：每核硬件周期计数器（PMCCNTR_EL0）在 OHOS PC 跨核调度下
读数回退（cpucycles persecond 出现 0.94x/0.97x 抖动）。该问题发生时已
离开构建期探测主题，属运行时正确性验证方法论：

- 门控条件"实际问题出现并解决"已满足（问题、定位、修复、验证全链路）；
- 按查重流程比对 graph + doc + drafts + operations：E138/E152 为编译期
  时钟常量探测，E270 为单点时钟回退补丁，均非"每核计数器跨核单调性
  验证方法"，存在真实知识缺口；
- 已按仓库草稿流程以官方工具重新提交候选草稿
  knowledge/drafts/E558-draft-7899.kv（draft: true，contributor_id: 7899），
  等待 draft-review 与主编转正，不直接写正式 graph/doc/index。
  原候选编号 E479 已被 upstream 草稿占用，E549/E557 亦已被其他分支
  占用，E558 经全库查证无占用，由 graph add --draft 官方流程重建。

原 §7 中"路径 B 不强行申报"的结论仅适用于构建期探测类候选，维持不变。

## 8. 使用说明（交叉环境运行）

本机为 OHOS PC（编译即目标机），无需传输执行。若在其它主机交叉编译
后部署：同步 package 目录，export LD_LIBRARY_PATH 或安装到系统路径。

## 9. Scoped CI 最终结果（2026-09-02）

命令：`CI_PACKAGES="archives/l/libcpucycles/20260625" CONAN_PROFILE="ohos-aarch64-local" zsh ci/conan/build_and_test.sh`

| 门禁 | 结果 | 说明 |
|---|---|---|
| G0 | pass | 知识图谱完整性 540 条 |
| G0e | pass | 根目录白名单 |
| KC | pass | 知识库质量（KC1-KC5 全过，0 错误） |
| JC | pass | junk 检查（incremental 模式，9 文件） |
| L0 | pass | L0j 首次发布版本无冲突 / L0k 库无 commands.json / L0m 目录结构 |
| L1 | pass | conan create + test_package 真实执行（L1a/L1b 测试证据，L1e 破坏性验证 lib/ include/ 真依赖） |
| L2 | skip | 无 bin/（纯库，无 CLI 产物打包，预期） |
| L4 | pass | 无 patch |
| L5 | pass | lib/ 有产物 |

test_package 输出（.tmplogs/ci-scoped-final.log 275-287 行）：
10/10 断言 PASS，backend=arm64-pmc（PMCCNTR_EL0 真实硬件计数器），
persecond=2399987654（上游硬编码 fallback，/proc/cpuinfo 与 /sys
cpufreq 在 OHOS 上不可读），exit=0。conandata.yml CI 后已还原官方
HTTPS URL。
