# 草稿 — OHOS C 库连 POSIX 标准函数 `sockatmark(3)` 都不声明也不导出：按特性改发其规范自身定义的 `ioctl(fd, SIOCATMARK, &val)`

> 触发实例：qperf 0.4.11 `src/support.c:466`（`mark_remote_failure()`）。
> 取证环境：HarmonyOS PC B 机（aarch64，HongMeng Kernel 1.12.0），
> OHOS SDK `ohos-sdk_26.0.0.18/ohos/native`，clang 15，conan profile `ohos-aarch64`。
> 取证日期：2026-09-24 ~ 2026-09-25（补丁 0001 由前窗产出，**根因与修法由本包全部复算取证**）。

## 可复现症状与稳定错误签名

编译期（非致命告警）+ 链接期（致命）成对出现：

```
support.c:466:17: warning: call to undeclared function 'sockatmark';
    ISO C99 and later do not support implicit function declarations
    [-Wimplicit-function-declaration]
ld.lld: error: undefined symbol: sockatmark
>>> referenced by support.c
>>>               support.o:(urgent)
clang-15: error: linker command failed with exit code 1
```

稳定签名：`call to undeclared function 'sockatmark'` + `undefined symbol: sockatmark`。
本包真机复现记录：`archives/q/qperf/0.4.11/reports/conan-create.log`（2026-09-24 17:01 那轮，
`conan-verify-report.md` 的 `G2: ❌ FAIL`）。

## 根因与最小复现（本包自行复算，未沿用他窗结论）

**根因**：`sockatmark(3)` 是 **ISO POSIX.1-2001 标准化函数**（glibc、macOS 均在
`<sys/socket.h>` 声明），上游 C 代码因此普遍"拿 POSIX 就当有"。OHOS 工具链的 C 库
**既不声明、也不导出**它：

| 探测面 | 命令 | 实测 |
|---|---|---|
| 声明 | `grep -rl sockatmark <sysroot>/usr/include` | **命中 0 个文件**（整个 sysroot 头树无任何原型） |
| 导出 | `llvm-nm -D --defined-only <sysroot>/usr/lib/<triple>/libc.so \| grep -c sockatmark` | aarch64-linux-ohos / arm / x86_64 **均为 0** |
| 底层特性 | `grep -rn 'define SIOCATMARK' <sysroot>/usr/include` | **命中 5 处**，含 `aarch64-linux-ohos/bits/ioctl.h:106: #define SIOCATMARK 0x8905` |

**关键的二分实验**（用来排除"只是头文件漏声明，补个原型即可"这一常见误判）：

| 实验 | 结果 |
|---|---|
| A. 自带原型 `int sockatmark(int);` 后调用并链接 | `rc=1`、`ld.lld: error: undefined symbol: sockatmark`、**无产物** ⇒ 缺的是**符号本身** |
| B. 改用 `ioctl(0, SIOCATMARK, &a)` 编译链接 | `rc=0`、**产物已生成**、无诊断 ⇒ 补丁路径可用 |

⇒ 结论：**不是"少个头文件"，是 libc 没有这个函数**；而它规范自身定义的底层 ioctl 是有的。

最小复现脚本：`~/tmp/uc2/z26-qperf/probe_link_paths.py`（实验 A/B）、
`~/tmp/uc2/z26-qperf/step_probe2.log`（声明/导出/特性三面盘点）。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 上游原样调用 `sockatmark()` | 链接失败 `undefined symbol`，G2 FAIL（实测，见上） |
| 只补函数原型 / 加 `-D_GNU_SOURCE` 等特征宏 | **无效**：实验 A 已证符号根本不存在，补声明只是把告警换成同一个链接错误 |
| 用 `__OHOS__` 平台宏把调用整段 `#if` 掉、或 `return 0` 占位 | **不采纳**：①违反 R8 / preflight PF5（补丁新增行禁平台宏）；②把链接错误换成**静默的错误结论**——`sockatmark` 用于判定"是否已到达带外数据标记"，返回 0 会让 `mark_remote_failure()` 的等待逻辑得出"没有带外数据"的假结论，比编译失败更坏 |
| 链接期塞一个 weak 符号兼容层（E534 家族做法） | 可绕过链接，但必须给**真值**；在已有底层 ioctl 可用时属于"绕远路 + 改变所有调用点语义"，退居 fallback |
| **按特性改发 `ioctl(fd, SIOCATMARK, &val)`（采纳）** | 与 POSIX 规范及 musl 自身实现同构；G2 转绿，真机 25 条断言全过 |

## 最终方案、输入输出与真实验证

补丁：`archives/q/qperf/0.4.11/patches/0001-support-sockatmark-via-siocatmark.patch`
（`patch_type: portability`，已在 `conandata.yml` 的 `patches:` 段登记）。

- 新增 `static int socket_atmark(int fd)`：`#ifdef SIOCATMARK` 分支
  `int atmark = 0; if (ioctl(fd, SIOCATMARK, &atmark) < 0) return -1; return atmark;`；
  `#else` 分支保留 `return sockatmark(fd);`。补 `#include <sys/ioctl.h>`。
- 调用点 `sockatmark(RemoteFD)` → `socket_atmark(RemoteFD)`。
- **开关按特性（有无该 ioctl）分流，不按平台分流**，补丁文件中不含任何平台宏：
  对 glibc/macOS 等具备 `sockatmark` 而无 `SIOCATMARK` 宏的平台走 `#else`，行为逐字不变。
- 错误语义与 POSIX 一致：失败返回 -1 并保留 errno 交给调用方，不伪造成功值。

真实验证（鸿蒙 PC B 机真机）：

- `python3 scripts/ohc-run.py conan-verify qperf 0.4.11` → `VERIFY_RC=0`，
  G0/G1/**G2**/G3/G4/L2/L4/L5 全 `✅ PASS`（`reports/conan-verify-report.md`，2026-09-25 00:12）。
- 消费者测试真机 **25 条断言全过、0 失败**，其中包含真实 TCP/UDP 自环测量：
  `tcp_bw = 4.51 GB/sec`、`tcp_lat = 19.6 us`、`udp_lat = 20.9 us`、
  `udp_bw: send_bw = 4.66 GB/sec / recv_bw = 531 MB/sec`。
- 补丁自身：`git apply --check` 与 `git apply --reverse --check` 均 `rc=0`。

## 适用范围、反例、解除条件与风险

**适用**：缺失函数是"某个平台已提供的底层接口（ioctl / syscall）的薄包装"——此时按特性改写
与 libc 的参考实现等价，不是伪造。已实证：`sockatmark` → `ioctl(SIOCATMARK)`
（POSIX 正文明确二者等价，musl 的实现也是这条 ioctl）。

**反例 1（不适用）**：缺失函数承载平台**确实没有**的能力（真正的 OOB 队列语义、RDMA verbs、
`perf_event_open` 权限等）。此时换成底层接口只是把编译错误替换成错误的运行期结论，
应按"能力缺失"如实申报，不要补包装蒙过链接。

**反例 2（勿与本条混用）**：**GNU/BSD 扩展函数**缺失（`gethostid` / `strverscmp` /
`sigisemptyset` / `getusershell` / `secure_getenv`）属既有条目 **E534 / E081** 家族。
E534 的根因解释是"musl 有意不实现**非 POSIX** 扩展"，该解释对**本条不成立**
（`sockatmark` 恰恰是 POSIX 标准函数，musl 上游也提供）。两族的根因层与解法都不同，
不能互相替代。

**解除条件**：若 OHOS 的 C 库未来在 `<sys/socket.h>` 声明并导出 `sockatmark`，
`#ifdef SIOCATMARK` 仍会优先走 ioctl（因宏仍在），行为不变；若要回到 POSIX 调用，
删除该包装函数即可，调用点无残留。

**风险**：`#else` 分支在未定义 `SIOCATMARK` 的平台上会重新引入隐式声明告警，
因此该分支必须保证 `<sys/socket.h>` 原型可见（补丁保留了原有包含顺序）。

## 知识库查重与新增价值

**四范围查重（命令与命中数）**：

| 范围 | 命令 | 结果 |
|---|---|---|
| 正式条目签名 | `grep -in "sockatmark\|SIOCATMARK\|out-of-band\|urgent" knowledge/graph/*.kv knowledge/graph/index.tsv` | **0 命中** |
| 草稿池 | `grep -in "sockatmark\|SIOCATMARK" knowledge/drafts/*.kv` | **0 命中**（草稿 1396 条） |
| 同机制先例 | `grep -ln "ioctl\|SIOC" knowledge/graph/*.kv` | **0 命中**——540 条正式条目无一涉及"改用 ioctl 实现" |
| "libc 缺符号但底层有"一族 | `grep -lE "未导出\|不伪造\|shim" knowledge/graph/*.kv` | 命中 19 条，其中**最近邻为 E245**（见下） |
| 归档先例 | 本包 `recipe-search qperf` → `⚠️ 无相似配方（语料 6173 条）` | 无同族配方可参考 |

`draft-review` 相似度 TOP3：**E093 0.43 / E245 0.29 / E085 0.23**，预审建议 `review-similar → E093`（灰区，人工裁决）。

**与最近邻条目的四条件比对（判 `create` 的依据）**：

- **E245**《OHOS libc 未导出 vhangup（声明缺失+符号缺失），但内核 syscall 存在》——**这是全库最近的一条，必须正面比对**
  1. *症状一致*：**部分成立**。E245 的三层诊断（无声明 → 无导出符号 → 底层内核接口仍在）与本例形状相同，
     且其 `affected_scope` 已自我泛化到"或类似'libc 未导出但内核 syscall 存在'接口"。
  2. *解法已被覆盖*：**不成立——这是判 `create` 的落点**。E245 的方案是 `ohos-syscall-shim`：查
     `__NR_vhangup` 后用 `syscall(SYS_vhangup)` **直调裸系统调用**，并且明确"**仅 OHOS 条件启用、
     非 OHOS 平台不启用 shim**"，即**依赖平台宏**。本例三点都不同：
     ①底层接口是 **libc 自己已导出的同层 `ioctl()`**，不涉及 syscall 编号；
     ②分流键是**特性**（`#ifdef SIOCATMARK`）而非平台，补丁新增行**零平台宏**，
     因此**通过 preflight PF5 / R8**——E245 那种 `__OHOS__` 写法若放进 patches/ 今天会被 PF5 拦；
     ③等价性有**规范背书**：POSIX `sockatmark(3)` 正文即定义其等价于 `ioctl(fd, SIOCATMARK, &atmark)`，
     musl 的实现也是这条 ioctl，故本补丁与该函数的参考实现同构。
     按四条件第 2 条原文："症状相同、但你用的是**既有条目没写的另一条解法**时**不算 hit，按 `create` 报**"。
  ⇒ 两族关系定为"**同族第二条解法路线**"：E245 = 裸 syscall shim（平台门控），本条 = 同层 ioctl（特性门控）。
     选路判据也一并沉淀：**先查有没有已导出的同层接口可用，没有才下沉到 syscall 编号**。
- **E534**《OHOS musl 缺失 GNU/BSD 扩展函数的 BusyBox 兼容层与配置规避》
  1. *症状一致*：**不满足**。E534 的 `error_signature` / `match_keywords` / `affected_scope`
     逐项只列举 `gethostid`/`strverscmp`/`sigisemptyset`/`getusershell` 这类 **GNU/BSD 扩展**，
     `root_cause` 明确写"musl 项目明确选择不实现**非 POSIX** 扩展"。本例缺失的
     `sockatmark(3)` 是 **ISO POSIX 标准函数**，属 E534 解释覆盖不到的新偏差
     （条件 1 自身口径："出现已知条目外的新行为偏差即升 B"）。
  2. *解法已被覆盖*：**不满足**。E534 的方案是 `compat-patch-in-missing-syscalls` +
     `__attribute__((weak))` 弱符号集中在兼容文件里；本例是**在调用点按特性开关
     （`#ifdef SIOCATMARK`）改发底层 ioctl**，不用弱符号、不加平台宏、不改 libc 侧语义。
- **E093**（`getpass` GNU 扩展缺失，draft-review 给出 0.43 最高分）：分数由 `cat=0.75` 的
  类目重合与 `sig=0.57` 的"undeclared function"表象推高，`kw` 仅 **0.05**（关键词几乎零重合）。
  `getpass` 是 **POSIX 已标记废弃的 GNU 扩展**、且 E093 的解法是"自己写一个 tty 读实现或
  `--disable-feature`"，与本条"改发平台已提供的等价 ioctl"既不同根因也不同解法 ⇒ 不构成覆盖。
- **E081**（musl 缺 `secure_getenv` → undeclared/implicit declaration）：同为"缺声明"表象，
  但函数类别（GNU 扩展）与解法（补声明/gnulib 替换）均不同，签名不重合。
- **E086**（`struct ucred`/`SO_PEERCRED` 缺失 → `ohos-guard-ucred`，用 `__OHOS__` 平台宏门控）：
  机制层面相邻（都是 socket 接口在 OHOS 缺）但**解法路线相反**——本条刻意不用平台宏
  （R8/PF5），且 E086 是"编译期类型缺失"、本条是"链接期符号缺失 + 存在等价底层接口"。

**结论：`B判定=create`**，新增草稿 `DRAFT-qperf-0.4.11-posix-sockatmark-absent-use-siocatmark-ioctl.{kv,md}`。

**新增价值**（相对 E245/E534 的净增量，不声称"首见 libc 缺函数"）：
①把 OHOS "libc 缺函数"族的**根因边界从"GNU/BSD 扩展"外扩到 ISO POSIX 标准函数**，
E534 的"musl 有意不实现非 POSIX 扩展"解释在此失效；
②给出**第二条解法路线**（同层已导出 ioctl + 特性门控，零平台宏、PF5 友好）及其与 E245
裸 syscall shim 的**选路判据**；
③给出可机械执行的**二分探针**（自带原型仍链接失败 ⇒ 缺符号而非缺声明），
避免下一包误走"补个原型/加特征宏"这条死路；
④用反例把边界钉死：无等价底层接口时不得补包装伪造成功（与 E245 的 `forbid_1` 同向）。
