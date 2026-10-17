# Draft knowledge — 日志括号数字 ≠ errno：Florist `Failed_Creation_Exit := 41`

- **id**: `DRAFT-libflorist-2025.1.0-failed-creation-exit-41`
- **层级**: L1 平台真理 / 判定方法
- **来源**: libflorist 2025.1.0 复审轮（2026-09-29），PR #13295
- **状态**: DRAFT（待主编审核编号）

## 一句话结论

上游测试日志里的 `failed process creation (41)` 中的 **41 不是 errno**，
而是被测库 Florist 的自定义哨兵退出码 `Failed_Creation_Exit := 41`；
据此判定"平台限制"是误判，**fork+exec 在 OHOS 上可用**。

## 证据链

| 类型 | 位置 | 内容 |
|---|---|---|
| 源码（常量定义） | `libsrc/threads/posix-process_primitives.ads:135` | `Failed_Creation_Exit : constant Exit_Status := 41;` |
| 源码（消息拼接） | `tests/posix_report.adb:833-834` | `if E = Failed_Creation_Exit then Assert (False, Message & ": failed process creation (41)")` |
| 源码（抛出点） | `libsrc/threads/posix-process_primitives.adb:494,537,574,621,651,661` | 各处 `Exit_Process (Failed_Creation_Exit)`（子进程 exec 前哨兵路径失败） |
| 探针（本机实测） | `clang -O0` 自写 C 程序 | `setuid/setgid/close/open/dup2/pthread_sigmask/execv` **全部返回 0**，子进程正常退出 |
| 旁证 | 本机 musl | `strerror(41)` = "No error information"（**与 errno 无关**，是巧合性误导） |

## 陷阱与判据

- **陷阱**：日志的 `(41)` 与 musl `strerror(41)` 无字符串**互相印证**，极易得出
  "errno 41 ⇒ 平台禁止 exec"的错误结论。本轮首轮即栽在这里。
- **判据**：凡日志出现 `<message> (<number>)`，先回查该数字是否为
  **被测库 / 测试框架的自定义常量或退出码**，再考虑 errno 解释。
- **证伪手法**：写最小探针直接调用可疑 syscall，用返回码代替推理。

## 适用范围

任何"读上游测试日志判定平台限制"的任务；尤其 Ada/POSIX、以及自带
`exit status` 语义的测试框架（FLORIST、ACVS 等）。

## 关联

- `DRAFT-libflorist-2025.1.0-upstream-runner-layout`：本条的真实致因（驱动未复现
  上游 `test.dir` 软链布局 ⇒ `execvp` 找不到子程序 ⇒ 走哨兵分支）。
- 修复后 `p030100 p030101 p030102 p120502` 由 FAIL 转 PASS：
  PASS 14→17、ASSERT_FAIL 33→19。
