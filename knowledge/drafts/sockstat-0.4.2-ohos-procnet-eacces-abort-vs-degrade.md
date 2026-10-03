# DRAFT-sockstat-0.4.2-ohos-procnet-eacces-abort-vs-degrade

**错误模式**：OHOS 沙箱下 `/proc/net` 文件内容 EACCES，上游「读不到就 `abort()`」
导致工具在真机上以 `rc=134(SIGABRT)` 结束，Linux 开发机上却完全正常。
按 Linux 行为写的断言在真机必红；把一切非零 rc 都当「平台受限」又会把真 bug 放过去。

- 来源：sockstat 0.4.2 适配（2026-10-02）
- 严重度：🟡 medium（不阻塞适配，但决定测试在真机是否可绿）

## 根因

OHOS 沙箱把 `/proc/net` 的**目录列举**与**文件内容**权限拆开：普通 uid 下
`ls /proc/net/` 可见 70+ 条目，但逐个读内容是 12/12 全拒（华为 PC 真机实测，
证据见 `archives/n/net-tools/2.1/reports/manual-runtime-evidence.md`）。
Linux 上这些文件世界可读 —— 同一份源码在 Linux 跑得通、在 OHOS 真机必然失败。

关键在于上游对「读不到表」有两类反应，必须分开对待：

| 类型 | 上游行为 | 真机表现 | 例子 |
|---|---|---|---|
| (A) 降级继续 | 少打印几行，仍 rc=0 | `rc=0` + 可解释的 `Limited output` | net-tools 的 netstat/route/ifconfig |
| (B) 缺失即 abort | `fprintf` + `abort()` | `rc=134` + `can not open file /proc/net/tcp, program will be aborted` | sockstat 0.4.2 |

## 推荐做法

按「**能否继续执行**」而非「是否报错」分流断言，平台受限单列一档：

1. **先读源码**确认是 (A) 还是 (B)，别靠猜：
   ```bash
   grep -n "handle_missing_file\|abort()" <src>/sockstat.c
   ```
2. 测试脚本设 `PASS` / `RESTRICTED` / `SKIP` 三态计数。`RESTRICTED` 的判据
   必须是**可 falsify 的特征串**（`can not open file /proc/net/` 或
   `Permission denied`），仅该串命中才计受限，**其余任何非零 rc 一律硬 FAIL**
   —— 受限档绝不能变成垃圾桶。
3. 为 (B) 型工具额外加两条断言：
   - 受限态必须给出明确诊断、**不得静默输出空表**（防上游某天改成静默退化）；
   - 受限态退出码语义为 `134`。
4. 参数解析路径（`-h` / 非法选项 / 非法端口）在 (B) 型工具里**先于读表返回**，
   是真机上稳定可绿的真实断言，应优先铺满，保证 CI 有实质通过项。

## 验证（本条已实测，sockstat 0.4.2）

| 环境 | 读表 | T3（11 条） | T4 鸿蒙特有（4 条） |
|---|---|---|---|
| x86_64 + qemu-aarch64 | 可用 | PASS（出真实 socket 行） | PASS |
| 等价 stub 复现受限分支 | EACCES | 全 11 条 RESTRICTED | 「受限态 rc=134」「必须点名 /proc/net 文件」PASS |

断言计数在两种环境下恒为 31（受限与可用各分支逐条独立记账，不合并）。

## 本地无法模拟时的替代取证

`unshare -rm` 挂 tmpfs / bind-mount 遮蔽 `/proc/net` **不可用**——`/proc/net`
是指向 `self/net` 的符号链接，用户命名空间内覆盖不生效（实测 bind-mount 后
`head /proc/net/tcp` 仍读到原内容）。改用等价 stub 复现上游受限分支来验证
分类逻辑，是可行且更可控的做法。

## 适用范围

- 读 `/proc/net/*` 的网络诊断类 C 工具（sockstat / netstat / ss 类）
- 对缺失输入文件选择 `abort()` 而非降级的上游程序
- 任何需要在 OHOS 真机与 x86 开发机之间迁移测试结论的适配任务
