# DRAFT: 交互式 REPL 行编辑器可用 stdin 管道无头驱动（ired 排除法的互补"驱动法"）

> 草稿条目 `DRAFT-edlin-2.24-interactive-repl-pipe-driven-test`（.kv 配对见同目录同名 .kv）

## 问题

CLI 包中常见的交互式 REPL 工具（行编辑器、shell、解释器循环）在无头 CI 下如何做
test_package / L1 消费者测试？既有条目给出的是**排除法**（ired 0.6：交互终端脚本
从包中排除，L2 非阻塞跳过）与**阻塞法**（DRAFT-8960：CLI 读 stdin 到 EOF 需主动
喂 EOF）。但三类工具性质不同：

| 工具类型 | 判别特征 | 正解 |
|---|---|---|
| 终端 raw 模式脚本（ired/vired） | `stty -echo -icanon`、`dd if=/dev/tty` | **排除**，无头不可驱动 |
| 读 stdin 到 EOF 的一次性 CLI（kea-shell） | `for line in sys.stdin` | **喂 EOF**（`echo |` 或显式关闭） |
| 逐行提示的纯 stdin REPL（edlin、ed、bc 类） | `fputs(prompt)` + `getchar()` 循环，**不碰 tty** | **可以管道完整驱动**，覆盖核心功能 |

第三类常被误判为前两类而只做 `--version` 冒烟甚至排除——白白丢掉功能级断言。

## 方案（edlin 2.24 实证）

REPL 只要满足「逐行读 stdin、无 tty 依赖」，即可用 printf 管道喂完整命令序列：

```sh
# 插入两行、保存退出（e=保存退出，Y=quit 确认，见姊妹条目）
printf '1I\nhello from edlin\nsecond line\n.\ne\nY\n' | edlin "$f"
# 退出码断言 + 文件内容断言 + stdout 缓冲区列表断言
printf 'L\nQ\nY\n' | edlin "$f" | grep -q "hello from edlin"
```

设计要点：

1. **退出路径必须显式走完**：REPL 的退出命令常有确认提示（edlin: `Really quit (Y/n)?`），
   管道里不补确认行就吃掉下一行命令或耗尽 stdin；
2. **exit code 是一等断言**：功能断言（文件内容）全过但退出码非 0 的组合，往往指向
   上游退出路径 bug（见 edlin 大写 E 条目），不能只 grep 内容；
3. **stdout 提示符噪音**：REPL 会把 prompt 打进 stdout，断言用 `grep -q` 定向匹配，
   不做全量输出比较；
4. **L2 skip 归因**：CI 的 L2 探测 `--version/--help` 对交互式工具天然失败（未知参数
   进入编辑循环），属 non-blocking skip，在 notes/manifest 写明"交互式 REPL 无版本
   开关"即可，不要为此伪造 version 选项。

## 验证（edlin 2.24，真机 shadow CI）

- test_package/test.sh 3 组用例 8 断言全过（插入保存/无操作保存/列表输出），exit 0；
- L1 pass；L2 skip（version/help failed, non-blocking）已归因；Build Summary 100%。

## 适用边界

- 工具内部 `open("/dev/tty")`、`isatty()` 分支进入 raw 模式 → 退化成 ired 类，只能排除；
- REPL 有行缓冲/多字节编辑键处理（依赖 termios）→ 同上；
- 上游退出路径在 EOF 下 abort()（edlin 大写 E）→ 先修调用序列（小写命令+Y），
  仍不行才考虑补丁。
