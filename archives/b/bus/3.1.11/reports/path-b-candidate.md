# 知识候选台账 — bus 3.1.11（Path B 候选评估）

任务类型: 知识库扩展（Path B）
日期: 2026-09-19
关联任务: bus-3.1.11-r01-pc2-21-20260919T144437Z

## 候选观测（非噪声项筛选）

适配全程收集到的真实失败/限制共 9 项，逐项归类：噪声（一次性、仅本包）或知识候选（可跨库复用）。

| # | 观测 | 是否候选 | 判定理由 |
|---|------|---------|---------|
| C1 | **OHOS 应用沙箱对 System V IPC（semget/shmget）返回 SIGSYS（Signal 31）**，bus CLI/示例/探针程序全部 core dump | ✅ 候选 | 跨库复用：任何依赖 SysV 信号量/共享内存/消息队列的 C 库都会命中 |
| C1a | C1 的 SIGSYS **可被 sigaction 捕获**（seccomp TRAP 语义），而 E051 记载的 setreuid 类 SIGSYS 不可捕获 | ✅ 候选（C1 扩展） | 模糊了 E051 的"不可捕获"结论：SysV IPC 命中的是 seccomp TRAP 而非未实现 syscall |
| C1b | POSIX `sem_open` 不受阻（返回 ENOENT 而非 SIGSYS），POSIX shm_open/mmap 可用 | ✅ 候选（C1 扩展） | 恢复路径：可迁移到 POSIX 原语（与 DRAFT-E577 buffer 方案同向） |
| C2 | conan-init 对纯 Makefile 工程误生成 autotools 配方 | 候选(轻) | URL 启发式误判；手动改写配方可解；非本包独有 |
| C3 | conan 2.29 `run()` 不接受 `win_bash` 参数 | 噪声 | 一次性 API 使用错误 |
| C4 | test_package 运行 127：VirtualRunEnv 空环境不注入 libdirs/PATH | 候选(轻) | 动态库 test_package 需显式 LD_LIBRARY_PATH + 绝对路径（dbus 有同型经验） |
| C5 | 上游示例硬编码 `/tmp/example-bus`，设备 /tmp 只读 | 噪声 | 平台 TMPDIR 限制，已用 $TMPDIR 规避（知识库已有 E002） |
| C6 | finish G0 clean-verify 对 makefile 工程跑 ./configure 失败 | 候选(轻) | manifest build_system 需如实填 makefile |
| C7 | conan-verify E017 镜像注入残留 conandata.yml.ghfast-bak/.orig | 噪声 | 工具需清理，提交前删除即可（记忆已记录） |

正式知识候选：**C1（含 C1a/C1b）**——以本包完整真实验证进入 Path B。

## C1 详细记录

- 真实命令/首错: `./bus create <path>` → `Signal 31 (core dumped)`（exit 159）
- 最小复现（semprobe）: `semget(IPC_PRIVATE,1,0600|IPC_CREAT)` + `shmget(IPC_PRIVATE,2048,0600|IPC_CREAT)` → SIGSYS
- 可捕获性验证（sigtest）: sigaction(SIGSYS) + siglongjmp → 捕获成功，进程存活；`sem_open` → ENOENT（不受阻）
- 根因: OHOS 沙箱 seccomp 白名单不含 SysV IPC（shmget/semget/msgget），命中即 SIGSYS（E246 同族，E051 反向）
- 修复/适配: 库可编译可链接（零源码补丁）；运行期业务需 SysV IPC 上下文（非沙箱/root/系统服务）或迁移 POSIX
- 验证: conan-verify 全门禁 PASS；test_ohos 运行时如实报告 PLATFORM_LIMITATION；消费者用例/CLI 冒烟通过
- 适用边界: 以 System V IPC 为进程间通信主干、且无 POSIX 等价分支的库/工具
- 恢复条件: 在启用 SysV IPC 的内核/非 seccomp 沙箱环境运行，或将 IPC 层迁至 POSIX shm/sem（DRAFT-E577 路线）

## 四范围查重（正式知识 / 图谱 / 草稿 / index.tsv）

| 范围 | 命中条目 | 覆盖内容 | 差异 |
|---|---|---|---|
| 正式知识 graph | E051 | 未实现 syscall → SIGSYS（setreuid/setregid 不可捕获） | E051 为"内核未实现"，语义与其相反（seccomp TRAP 可捕获）；相互补充 |
| 正式知识 graph | E246 | seccomp 拦截 Linux 私有 syscall（adjtimex）→ SIGSYS | E246 覆盖 syscall 级；C1 是 **IPC 族 syscall 特例** + "可捕获"实测证据 |
| 正式知识 graph | E220 | perl 对 IPC/SysV 能力探测 | 探测思路同向，但无 IPC 的 SIGSYS 实测数据 |
| 正式知识 doc | E022 | POSIX semaphore /dev/shm FileNotFoundError | 互补（POSIX 面），C1 是 SysV 面 |
| 草稿 drafts | **DRAFT-E577（buffer 1.19）** | SysV IPC（shmget/semget/msgget）在 OHOS 沙箱直接 SIGSYS；**方案=改用 POSIX shm_open+sem_t** | 见七轴（部分重叠，存在验证过的新增差异） |
| 草稿 drafts | DRAFT-E580 等 | 无关（编码/构建问题） | — |
| index.tsv | 无 C1 对应整行 | — | 需新条目 |

## 七轴查重（对 DRAFT-E577）

| 轴 | 结论 | 说明 |
|---|---|---|
| exact_duplicate | **否** | E577 针对"双进程共享内存环形缓冲的可改写程序"（buffer/afl），本候选针对"以 SysV IPC 为公开 API 的 C 库"及 SIGSYS 可捕获性实测 |
| causal_duplicate | **部分** | 根因相同（SysV IPC 不在 OHOS seccomp 白名单） |
| trigger_overlap | **高重叠** | 同一触发面（semget/shmget → SIGSYS） |
| solution_overlap | **部分重叠** | E577 提供 POSIX 迁移路线（rec_approach=sysv-ipc-to-posix-shm-sem）；本候选补充"不可迁移时如何如实验证/降级+通告"（捕获 SIGSYS+平台限制标注+恢复条件），且提供 SIGSYS 可捕获的证据链（E577 未含） |
| combination_novelty | **新增** | "SysV IPC 库（无可迁移分支）+ SIGSYS 可捕获实测 + 消费者用例用非触发路径验证 + 鸿蒙专项测试如实报告平台限制"的组合无既有条目 |
| boundary_novelty | **新增** | 边界：可改写程序（buffer）→ 迁移 POSIX；不可改写库（本包 API 即 SysV）→ 编译链接交付 + 运行期平台限制通告；两条路径按"IPC 层是否与源代码耦合"划分 |
| test_migration_novelty | **新增** | 给出 SysV IPC 受限平台上的测试迁移口径：上游示例全量枚举（23/23 编译，运行 SIGSYS 均计未运行）、消费者用 ENOENT 路径、专项测试捕获 SIGSYS 区别"平台限制 vs 真实缺陷" |

## 覆盖/新增差异与关系字段

- 既有条目覆盖部分: E051（SIGSYS 家族）、E246（seccomp 拦截）、DRAFT-E577（SysV IPC→POSIX 迁移路线）
- 本轮新增部分: ①SysV IPC 在 OHOS 沙箱的 SIGSYS **可捕获**（seccomp TRAP）实测证据；②不可改写库（IPC 为公开 API）的适配验证与平台限制通告方案；③macOS/Linux 无涉，仅 OHOS 应用沙箱约束下的验收口径
- 适用边界/反例: 不适用于 mount namespace/FUSE 等非 IPC 场景；若库本身带 POSIX 回退分支（如 E237 acpid 类）则不适用
- relations: similar_to=[E051, E246, E220, DRAFT-E577], caused_by=[], prerequisite_of=[], conflicts_with=[]

## 路径决定

**Path B（new_draft）**：新增差异已由本轮真实日志验证（semprobe/sigtest/test_ohos 全实测），
且可跨库复用（任何以 SysV IPC 为核心的 C 库）。非完全重复，需建立同 stem 的 .md/.kv 草稿
（E584-bus-sysv-ipc-sigsys-catchable）。