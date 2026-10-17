# DRAFT-memlockd-1.3.1-ohos-unprivileged-mlock-capability-plane

**OHOS 用户态锁页能力面**：非 root、无 `CAP_IPC_LOCK` 的普通会话里，`RLIMIT_MEMLOCK` 就是无限，
`mlockall()` 与 `mmap()+mlock()` 全部放行；而"放行"本身不能证明页真被钉住——
判别性证据只能取 `/proc/<pid>/smaps_rollup` 的 `Locked:` **差分**。

- 来源：memlockd 1.3.1 适配 HarmonyOS PC（平台任务 8789，路径 B）
- 实证日期：2026-09-25，HarmonyOS PC 真机（HongMeng Kernel 1.12.0，musl 用户态，clang 15.0.4），非 root 会话 `uid=20020084`
- 严重度：2（不阻断编译，但决定"锁页型包能不能算真适配"与测试证据是否假绿）

## 错误特征

```
RLIMIT_MEMLOCK cur=-1 max=-1 RLIM_INFINITY=-1
mlockall: Permission denied                      # 常见平台的反面形态，本机不出现
Can't lock memory, exiting                       # memlockd 自有失败串（本机不触发）
Cannot allocate memory (ENOMEM)                  # 上限有限时的典型 errno（本机不触发）
"Locked:.*kB" 行缺失 / 恒为 0                     # 判据本身不可用
```

`trigger_tool`：`clang|make|conan|python3`；`phase`：`test|runtime`。
`prescan_pattern`：`mlock\(|mlockall\(|RLIMIT_MEMLOCK|CAP_IPC_LOCK|sodium_mlock|munlockall`。

## 触发条件

- 平台：OHOS / HarmonyOS PC（本条全部读数出自该真机，非容器、非 CI worker）
- 主体：任何以 `mlock`/`mlockall` 为功能核心的包——锁页守护进程（memlockd、`memcached -k`、
  `gpg-agent`/`keepassxc` 的密钥清零路径）、`libsodium` 的 `sodium_mlock()`、以及"把关键文件常驻内存"类工具
- 阶段：配方 `build()` 之后的真实运行期与消费者测试期；也包括写"能力探测"时的 configure 阶段
- 前置：调用方以普通用户身份运行，未持有 `CAP_IPC_LOCK`，也没有 systemd `LimitMEMLOCK=` 这一层

## 根因分析

1. **上限形态与 Linux 桌面惯例不同**。同一进程内 `getrlimit(RLIMIT_MEMLOCK)` 的 `cur` 与 `max`
   都返回 -1（即 `RLIM_INFINITY`）。因此"非 root 最多只能锁 64KB（或 systemd 给的 8MB）"
   这一先验在 OHOS 上不成立：超过任何常见上限的 8 MiB 文件整体锁页照样成功。
2. **三类调用全部放行**：`mlockall(MCL_CURRENT|MCL_FUTURE)` 返回 0（memlockd 把这一步当作致命门，
   失败即 `exit(1)`）、`mmap(PROT_READ, MAP_SHARED)`＋`mlock(整个文件)` 返回 0、
   经 `SIGHUP` 重解析配置后追加映射一个 8 MiB 文件仍成功。
3. **陷阱在证明方向**。返回 0 只证伪"被拒绝"，不证实"页被钉住"。若把判据写成
   "`mlock` 返回 0 即通过"，那么一个静默忽略 `mlock` 语义的环境（返回 0 但不钉页）同样报绿。
   这与 `E584`（configure 报 yes、运行期被 seccomp 以 `SIGSYS` 终止）同属假绿家族，
   但更隐蔽：这里连 syscall 都完全规矩，没有任何信号或 errno 可以顺手捕获。
4. **可证伪的载体是 procfs 的 `Locked:` 差分**。本机同一进程先读基线 `31768 kB`，
   通过上游自身的重配置入口（`SIGHUP` → `parse_config()`）追加一个 8 MiB 文件的锁页映射后
   读到 `39960 kB`，**增量恰为 8192 kB**。必须用差分而不是绝对值：`mlockall` 一开始就把整个地址空间
   钉住了，绝对值恒大于 0，无法归因到被测对象。
5. **归因还要排除进程自身段**。被测的可执行文件本身在 `maps` 里有 `r--p` 与 `r-xp` 段，
   与 `memlockd` 自己建立的 `PROT_READ|MAP_SHARED` 映射同一路径；只有权限串 `r--s` 那一条才是被测映射。
   开发期一次"按路径存在即通过"的断言正因如此无条件成立（假绿），已在本包 notes.md 记录并更正为
   权限串＋尾段双重匹配。

## 最小复现

```sh
# 1) 平台形态（只记录，不作判据）
python3 -c 'import resource;print(resource.getrlimit(resource.RLIMIT_MEMLOCK))'   # (-1, -1)

# 2) 被测进程：非 root 起锁页守护进程，读基线
memlockd -d -c /abs/path/cfg1.cfg &                       # cfg1 里先只列 2 个小文件
PID=$!; awk '/^Locked:/{print "base", $2}' /proc/$PID/smaps_rollup

# 3) 经上游自身的重配置入口追加一块已知大小的映射
printf '%s\n' /abs/path/one.cfg /abs/path/huge8m.bin > /abs/path/cfg1.cfg
kill -HUP $PID; sleep 1; awk '/^Locked:/{print "after", $2}' /proc/$PID/smaps_rollup
# 期望 after - base >= 8192 (kB)，且 huge8m.bin 在 maps 里恰有一条 r--s
```

## 推荐方案（优先级 1）

**方法**：`verify-page-lock-via-smaps_rollup-delta`

1. 在同一进程内读 `getrlimit(RLIMIT_MEMLOCK)` 与一次最小 `mlock` 的 `errno`，**只用于记录平台形态**，
   不作为通过判据；
2. 以 `/proc/<pid>/smaps_rollup` 的 `Locked:` 做**差分**：起被测进程读基线 →
   用上游自身的重配置入口（本包是 `SIGHUP` 重解析配置文件）追加一块已知大小（建议 ≥ 8 MiB，
   显著大于任何默认上限）的锁页映射 → 重读并断言增量落在该大小；
3. 用 `/proc/<pid>/maps` 的权限串 `r--s` 把被测映射与进程自身段区分；路径匹配按**尾段**而非全串
   （HMDFS 在 procfs 侧打印 `/data/service/el2/<uid>/hmdfs/...` 规范路径，且两侧 inode 不一致，
   该通用机制已转成 `经验文档/B草稿库/DRAFT-PKG-VER-proc-maps-hmdfs-canonical-path.*`）。

`rec_command`：`python3 test_memlockd.py <package_folder> <work_folder>`
（逐字读数见 `~/tmp/uc2/hw-3/memlockd/create-6.log:152-173`）

## 回退方案（优先级 2）

**方法**：`absolute-locked-threshold-when-no-reconfig-entry`

上游没有"重读配置/增量锁页"入口时无法做差分，退一步用绝对阈值：在被测进程锁完一个 ≥ 8 MiB 的已知文件后
断言 `Locked >=` 该文件字节数，并在报告里写明该形态排除不了"环境把全地址空间钉住"的贡献（弱一等证据）。
再退一步才允许写"仅证伪不证实"并标注未覆盖——不允许把 `rc=0` 直接当"锁页成功"申报。
`fallback_command`：`awk '/^Locked:/{print $2}' /proc/$PID/smaps_rollup`

## 实测证据（与 PR 同源）

| 读数 | 值 | 出处 |
|---|---|---|
| `RLIMIT_MEMLOCK cur/max` | `-1 / -1`（RLIM_INFINITY） | `create-6.log:152` |
| `mlockall(MCL_CURRENT\|MCL_FUTURE)` | rc=0（非 root、无 CAP_IPC_LOCK） | 同上 `:158`（L2a PASS） |
| `Locked:` 基线 → 追加 8 MiB 后 | `31768 kB → 39960 kB`（+8192 kB） | 同上 `:163` |
| 被测映射权限串 | 恰一条 `r--s` | 同上 `:164`（L2e PASS） |
| 消费者断言 | `PASS=17 FAIL=0`（其中 5 条打在锁页面） | 同上 `:153-173` |
| 进程内存峰值 | `MEMCAP[run] peak=97MB budget=2500MB rc=0` | 同上 `:175` |

## 适用范围与反例

- **适用**：OHOS/HarmonyOS PC 上以 `mlock`/`mlockall` 为功能核心的包，以及任何想申报
  "非特权下内存常驻能力可用"的测试证据。
- **不适用 / 反例**：
  - `RLIMIT_MEMLOCK` 被策略下调为有限值的形态本机未观测到（本机 `max` 亦为无限），
    不能拿本条断言"任何 OHOS 部署都无限"；换环境必须重测差分。
  - seccomp 直接以 `SIGSYS` 终止 `mlock` 族的平台属 `E584` 家族，签名与处置都不同（那里有信号，这里有正常返回）。
  - `madvise(MADV_MEMLOCK)`、THP、memcg 锁页记账不在本条范围。
  - 若 CI worker 以 root 或带 `CAP_IPC_LOCK` 运行，"无限上限"读数不能外推到它。
  - 本条不覆盖 `munlock`/`munlockall` 的对称行为，也不覆盖锁页后的换出拒绝验证（需要更大内存压力，
    本机共享设备上不做）。

## 查重结论与新增价值

- 检索范围：`knowledge/graph/index.tsv` 全量按 `mlock`/`RLIMIT`/`Locked`/`CAP_IPC_LOCK` 关键词，
  `knowledge/*.md`（含 `error-patterns.md`、`musl-compat.md`、两份 musl/glibc 对照表），
  以及工作区通用草稿池 `经验文档/B草稿库/`（22 条）全量。
- 结论：既有条目里 `mlock`/`mlockall`/`RLIMIT_MEMLOCK` **只作为"musl 是否提供该符号"的勾叉表行出现**
  （`musl-glibc-full-comparison-gnu-linux.md:424/426`、`musl-glibc-full-comparison-iso-posix.md:1400/1887/1889`），
  没有任何条目给出**本机运行期上限取值、非特权是否放行、以及如何证明页真被钉住**；草稿池零命中。
  按 §6.2「家族命中四条件」：条件 1（症状一致）不成立（既有条目根本没有症状，只有能力表行），
  条件 2（解法已被覆盖）也不成立 ⇒ **判 create，不是 hit**。
- 新增价值：①一个与 Linux 惯例相反的**具体平台取值**（无限上限，直接决定"锁页型包是否需要特权预处理"这一
  配方决策）；②一条**反假绿的测试方法**（差分 `Locked:`，附可执行的三步与回退档），
  可被 `memcached -k`、`gpg-agent`、`libsodium` 消费者、任何"内存常驻/密钥清零"类包直接复用；
  ③maps 权限串归因（`r--s` vs `r--p`）这一配套细节，是本包开发期真撞出来的假绿修正，
  单靠"知道要看 maps"得不到。
