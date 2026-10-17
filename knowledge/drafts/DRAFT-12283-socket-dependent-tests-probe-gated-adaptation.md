# DRAFT-12283 — socket 依赖型消费者测试在 OHOS 的诚实适配范式

> **引用既有平台事实**：`E461`（writable FS 拒绝 AF_UNIX file-socket bind；
> abstract 命名空间可用）、`E024`（AF_UNIX bind 受限 → use-tcp-socket）、
> `E002/E052`（/tmp 只读）。本条不重复论证平台事实，给出的是**测试设计范式**：
> 当消费者测试需要先 bind 本地 socket 时，如何在不伪造、不静默跳过的前提下
> 保持测试可审计。定位为可并入 E461 的增量段落（`draft-review` 预审：
> review-similar → E461，最高相似度 0.46）。

## 错误特征

```text
# 测试内对端 bind（受限域）
bind: Operation not permitted                      # EPERM=1（dgram/stream 同）
# 默认路径
touch: '/tmp/.probe': Read-only file system         # EROFS
# 客户端（负路径，稳定可断言）
$ YDOTOOL_SOCKET=/tmp/.ydotool_socket ydotool key 1:1
failed to connect socket `/tmp/.ydotool_socket': No such file or directory
Please check if ydotoold is running.               # exit 2
```

若把 bind 失败直接当作测试 FAIL，则该组协议断言在受限平台永远红；若静默
跳过，则测试失去审计价值（无法区分“平台不允许”与“实现坏了”）。

## 触发条件

- 阶段: testing（消费者测试/上游测试需要本地 socket）
- 场景: daemon/client 类包——测试先 bind 一个本地 AF_UNIX socket，再驱动
  客户端断言 `input_event`/协议字节流
- 环境: HarmonyOS PC（受限执行域，`bind` EPERM、`/tmp` EROFS）

## 适配范式（本条增量）

1. **能力探针先行**：测试第一步运行“用户态对端 bind 能力探针”，输出可审计
   标记：成功 → `LISTENING`；被策略拒绝 → `BIND-FAILED errno=1 Operation not
   permitted`。探针是断言的一部分（A8），不是旁路。
2. **条件执行 + 显式计数**：探针成功 → 执行全部线协议逐字节断言；探针 EPERM →
   该组断言登记 **skipped**（打印明确计数与平台原因），进程退出码保持成功；
   **非 EPERM（如 EADDRINUSE/ENAMETOOLONG 等）一律 FAIL**，绝不掩盖真实缺陷。
3. **不受影响的断言必须真实执行**：CLI 契约（`--version`/`--help`/未知命令）、
   产物完整性（ELF）、负路径（缺失 socket / 非 socket 路径的 rc 与提示文本）、
   平台边界（真实 daemon 的 uinput 分支）——它们不依赖 bind，永远是硬断言。
4. **运行时路径**：默认 `/tmp/...` 在 OHOS 不可用；用 `-p "$TMPDIR/..."` 或
   `XDG_RUNTIME_DIR`（客户端/服务端同源回退）。
5. **禁止**：伪造 AF_UNIX 接收端、把跳过计入 pass 数、为让测试变绿改产品
   代码或注入 `__OHOS__` 空壳。

## 与其他条目的关系（查重差异）

| 条目 | 讲了什么 | 本条的差异 |
|------|----------|-----------|
| E461 | 平台事实：writable FS 拒绝 file-socket bind；abstract 可用 | 本条讲**测试怎么写**（探针门控/跳过计数/硬断言集合） |
| E024 | 替代方案：AF_UNIX → TCP | 若协议允许可用 TCP 替代；若协议固定（如 ydotool 客户端只支持 AF_UNIX pathname）则须按本条适配 |
| raul-2.0.0-af-unix-bind-blocked-meson-skip | 上游 meson 测试 `exit 77` 记 SKIP（只改失败分支，不改断言） | 本条针对**自建消费者测试**：探针+条件执行+显式计数，并保留负路径与平台边界硬断言 |
| DRAFT-pty-driven-interactive-test-traps 等 PTY 类 | 伪终端驱动交互程序（TTY 层） | 本条是 unix 域 socket 绑定（网络命名空间），不同面 |

## 验证

```bash
# 探针分支证据（本包 A8）：LISTENING 或 BIND-FAILED errno=1
# 条件执行结果：test_ydotool: 9/9 executed assertions passed (7 skipped: E024 AF_UNIX bind EPERM)
# 负路径（永远执行）：缺失 socket -> rc=2 + "Please check if ydotoold is running."
```

## 关联条目

- similar_to: E461、E024、E002、E052
- 配套草稿（同任务）：`DRAFT-12283-ohos-uinput-injection-device-permission-boundary`（注入链另一道边界）
