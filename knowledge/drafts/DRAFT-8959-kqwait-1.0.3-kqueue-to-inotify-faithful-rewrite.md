# DRAFT-8959: BSD kqueue 原生工具在 OHOS 上以 inotify 忠实重写的适配模式

> 状态: DRAFT — 待 review 晋升为 E 条目
> 发现于: kqwait 1.0.3 OHOS 适配（feat/kqwait-1.0.3 分支，2026-09-15）
> 路径: Path B（可解决的适配模式，非平台能力边界）

## 问题

BSD 系工具（kqwait、各类 watcher）以 `kqueue(2)`/`kevent(2)` + `EVFILT_VNODE` 为核心，等待文件/目录变化事件。移植 OHOS 时直接失败：

```
fatal error: 'sys/event.h' file not found
```

## 平台能力判断（W0）

| 检查项 | 结果 |
|--------|------|
| sysroot `sys/event.h` | **不存在**（`/usr/local/sysroot/usr/include/`） |
| libc.so 动态符号（1595 个） | **无** `kqueue`/`kevent` |
| 内核 syscall | HongMeng 内核**不提供**（BSD 私有事件机制） |
| inotify | **完整可用**：探针 S1–S9 九类边沿事件实测全过 |

**结论**：平台 API 家族缺失（非构建检测问题，非可 shim 的用户态缺口）。但 EVFILT_VNODE 子语义与 inotify 能力正交重叠 → 存在忠实重写路径。

## 两条已被证伪的替代路线（勿重复踩坑）

1. **libkqueue 2.6.1**：OHOS 上目录监听行为失败（见 `archives/l/libkqueue/2.6.1/notes.md`）
2. **epoll-shim**：E399 记录 32/166 CTest 失败，kqueue 模拟语义与原生 epoll 不符（signalfd 阻塞读挂起）

## 解决模式：inotify 忠实重写

### 语义映射表

| kqueue | inotify | 去向 |
|--------|---------|------|
| `NOTE_WRITE` | `IN_MODIFY\|IN_CREATE\|IN_DELETE\|IN_MOVED_FROM\|IN_MOVED_TO` | 文件→打印路径；目录→dirinfo diff |
| `NOTE_DELETE` | **`IN_DELETE_SELF`** | 短路输出 `- path` |
| `NOTE_RENAME` | `IN_MOVE_SELF\|IN_MOVED_FROM\|IN_MOVED_TO` | 同 NOTE_WRITE |

### 三大陷阱（实测踩过）

1. **`IN_DELETE` ≠ kqueue `NOTE_DELETE`**：inotify 的 `IN_DELETE` 是目录内**子项**被删（kqueue 下表现为目录的 `NOTE_WRITE`，走 dirinfo-diff 分支）；`IN_DELETE_SELF` 才是 watch 路径**自身**被删。混淆会把"目录内删文件"错误短路成输出 `- dir/`。
2. **`getopt()` 返回值存 `char`**：aarch64 char 默认 unsigned，`(char)-1 == 255 != -1` → 参数解析死循环（kqwait 上游真实 bug，signed-char 的 BSD 平台未暴露）。修：`int ch`。
3. **测试隔离**：`touch` 已存在文件只发 `IN_ATTRIB`（kqueue `NOTE_WRITE` 同样不含 utimens），场景间不清理残留文件会让复跑假超时——误判为平台行为差异。

### 流程

```
W0 平台能力判断（sysroot grep + libc 符号 + inotify 探针 S1–S9）
→ 证伪 libkqueue / epoll-shim 路线（查知识库 E399 等）
→ 生成移植补丁（只替换事件源；CLI/输出/退出码逐字节一致）
→ 上游断言 1:1 移植执行（IPC::Run 类依赖缺失 → SPEC 3.3 豁免 + 移植）
→ conan create ohos-aarch64 全绿
```

## 适用条件

- ✅ 工具只消费 EVFILT_VNODE 文件系统边沿事件子集（单点等待器）
- ✅ CLI 行为可作黄金基准（输出可逐字节比对）
- ❌ 依赖 EVFILT_READ/WRITE/SIGNAL/PROC/TIMER/USER 等非 VNODE 滤器
- ❌ 多路复用/水平触发语义
- ❌ 需要 kqueue 可移植层的大库（走 libkqueue/epoll-shim 失败记录）

## 安全边界 / fail-closed

1. W0 先证伪再动手：sysroot + libc 符号双确认后才下"平台缺失"结论
2. inotify 探针任一事件失败 → 停止移植，记录平台能力边界（**不**硬凑映射）
3. 禁止空实现/stub（始终返回成功/失败的假 kqueue 违反 SPEC）
4. 移植后上游断言必须 1:1 执行，失败即 fail（不许 ignore_errors 放行核心语义）
5. 依赖 VNODE 之外的 kqueue 滤器 → 直接给平台阻塞结论 + 源码/API 证据，不做假适配

## 复用价值

任何"BSD kqueue 单点等待"型第三方工具（文件监听器、构建触发器、日志 tail 类）移植 OHOS 都可直接套用本模式：映射表 + 三陷阱清单 + W0 探针流程。E399 记录了"模拟层"路线的失败边界，本条目补全"忠实重写"路线的成功边界，两者合成 kqueue→OHOS 的完整决策树。

## 证据

- `archives/k/kqwait/1.0.3/`：完整适配（补丁、15/15 上游断言、notes.md）
- `probes/inotify_semantics_probe.c`：S1–S9 边沿事件探针
- 失败对照：`archives/l/libkqueue/2.6.1/notes.md`、`knowledge/doc/E399.md`
