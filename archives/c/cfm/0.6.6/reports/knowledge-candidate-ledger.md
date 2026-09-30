# cfm 0.6.6 — 知识候选台账与七轴查重

> 任务类型：知识库扩展（Path B）；knowledge_candidate_observation: required
> 本轮为 cfm 0.6.6 适配产生的候选观察：**无 --version/--help 的纯 termios TUI 程序的消费者验证方法**。

## 候选 1：GNU install 缺失 → package() 绕开 make install

- 问题：cfm `make install` 报 `install: No such file or directory`（HarmonyOS 无 GNU install）。
- 根因：环境缺 GNU install（toybox 兼容性问题）。
- 方案：conan 配方 package() 用 copy() 直接拷贝 cfm/cfm.1，不调用 make install。
- 验证：conan create 全流程通过（本任务 W3 日志）。
- 查重：**exact_duplicate / trigger_overlap 命中既有条目** —— E108（install: No such file or directory → patch-makefile-in-ginstall）、E182（toybox install 兼容 → 手动 cp 替代）。
- 决定：`reuse_existing`（E108/E182 已覆盖，不建草稿）。

## 候选 2：无 --version/--help 的 termios TUI 程序消费者验证（pty 驱动渲染断言）

- 问题：cfm 为纯 termios TUI（无 ncurses、无 FILE=-、无 /dev/tty freopen）。`--version/--help` 按目录参数解析失败退出 1；L2 冒烟为 warn 非阻塞；普通非 TTY 运行（stdin 关闭）**快速退出 0**（只证明加载/目录扫描，不证明 TUI 渲染）。
- 根因：TUI 渲染需要控制终端；上游无版本/帮助参数；测试需要真实终端通道。
- 方案：消费者用例用 `pty.fork()` 启动 cfm，断言输出含 `\x1b[` 转义序列（备屏渲染），发送 `q` 键干净退出（exit 0）。
- 验证：test_package 内 pty 用例实测通过（226 bytes 渲染，q 退出 rc=0）；C 消费者 fork+execvp 冒烟 rc=0。
- 适用边界：纯 termios 直控 TUI、无 FILE=-/无 /dev/tty freopen 的程序；ncurses TUI 与 FILE=- 双通道场景见 DRAFT-E569。
- 反例：mdp 类 freopen("/dev/tty") 程序（DRAFT-E569），管道单通道必失败；jshn 类 getopt CLI（E503）应补 --version/--help 而非 pty。

### 七轴查重

| 轴 | 判定 | 说明 |
|----|------|------|
| exact_duplicate | 否 | 无完全同题条目（E503 是 getopt CLI 的 --version/--help 补丁；DRAFT-E569 是 FILE=-/dev/tty 双通道，均非"纯 termios TUI + pty 渲染断言"） |
| causal_duplicate | 否 | E503 根因=getopt 短选项；DRAFT-E569 根因=/dev/tty freopen；本候选根因=无控制终端时 TUI 渲染不可验证 |
| trigger_overlap | 部分 | 三者都在 conan-verify/L2 冒烟与 test_package 场景触发 |
| solution_overlap | 部分 | 与 DRAFT-E569 同用 python pty.fork()；但本候选是"渲染断言+退出键"而非"双通道喂 stdin+tr -d \r" |
| combination_novelty | 是 | "纯 termios TUI（无 ncurses/FILE=-）+ pty 渲染断言 + 非 TTY 快速退出 0 作为冒烟"组合无既有条目 |
| boundary_novelty | 是 | 明确适用边界（无 freopen 的 TUI）与反例（mdp/jshn），边界划分与 E569/E503 互补 |
| test_migration_novelty | 是 | 可跨库复用：任何无 --version/--help 的 termios TUI（如 vim 类/自定义 TUI 工具）的消费者测试 |

### 关系字段

- similar_to: DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel（同 pty.fork 技术，异根因/异边界）
- similar_to: E503（同 L2 --version/--help 场景，异方案：E503 改程序，本候选改测试通道）
- caused_by: 上游 cfm 无 --version/--help 且 TUI 渲染依赖控制终端
- prerequisite_of: 无
- conflicts_with: 无

## 决定

- 候选 1 → `reuse_existing`（E108/E182）
- 候选 2 → `new_draft`（有新增差异、已由本轮真实 pty 日志验证、可跨库复用）
