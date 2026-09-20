# DRAFT: KDE KGame AI 协程进程 stdin-EOF 不退出——headless 测试须启动握手断言 + 有界兜底 + rc 合法化

> 配套条目：`DRAFT-kfourinline-kgame-proc-stdin-eof-event-loop-bounded-test.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：kfourinline 26.04.0，PR #11104（merged，commit `5a1146acad` / `fd69863645`）

## 1. 错误特征（可机器匹配）

```
kgameprocess.cpp:39:5: warning: ignoring return value of function declared with 'nodiscard' attribute
    d->rFile.open(stdin, QIODevice::ReadOnly | QIODevice::Unbuffered);
...（进程启动后进入事件循环）
stderr: AI process starts up
stderr: Cookie error × N（stdin 喂 EOF 后无限刷，进程不退出）
```

- error_signature：`Cookie error|AI process starts up|kgameprocess\.cpp|stdin-EOF|timeout 15.*rc=124`
- **识别要点**：被测进程是 KDEGames 的 KProcess 子进程（AI/协议引擎）；启动即打 banner；`< /dev/null` 喂 EOF 后 cookie 解析循环刷 "Cookie error" 不退出；TERM 可干净杀掉（rc=143）；上游 main 设计返回码为 1。

## 2. 根因

kfourinline 上游交付两个可执行文件：`kfourinline`（QApplication GUI）+ `kfourinlineproc`（QCoreApplication AI 引擎进程）。游戏主进程通过 **KProcess spawn AI 进程，双方在 stdin/stdout 上交换 KGame 消息协议**（src/kwin4proc.cpp + src/kgameprocess.cpp）：

```cpp
// src/kgameprocess.cpp（上游 26.04.0）
d->rFile.open(stdin,  QIODevice::ReadOnly  | QIODevice::Unbuffered);  // stdin = 协议入站
d->wFile.open(stdout, QIODevice::WriteOnly | QIODevice::Unbuffered);  // stdout = 协议出站
```

- **该进程没有"stdin EOF 退出"路径——上游设计**：消息循环由父进程的消息驱动，父进程发关闭消息才退出（游戏退出时 close 掉 KProcess）；
- headless CI 测试中给 stdin 喂 EOF（`< /dev/null`）时，KMessageFilePipe 的 cookie 解析循环把 EOF 当作半条消息反复尝试解析 → stderr 无限刷 "Cookie error" → 进程永不退出 → 测试脚本挂死/超时；
- 这是 **IO 协议进程的退出语义**问题（上游行为正确），不是平台缺陷——测试侧必须适配，不能改上游。

**与 E464（MyGUI Dummy busy loop）的辨析**——同签名家族（忙循环 + kill 兜底）不同根因：

| 维度 | E464 MyGUI | 本条 KGame |
|---|---|---|
| 循环位置 | DataStream::read() 消费循环（EOF 后 read 仍返回非 0） | KMessageFilePipe cookie 解析循环（EOF 被当半条消息） |
| 根因性质 | **实现缺陷**（Dummy 后端资源注册空实现 + read 契约违背）——需补实现修复 | **上游设计**（协议进程退出由父进程消息控制）——测试侧适配 |
| 修复方向 | patch 源码实现资源注册接口 | 不改上游，改测试断言语义（握手+有界+rc 合法化） |
| 影响范围 | MyGUI 无头渲染测试 | KDEGames 全家（所有 KProcess AI 子进程游戏） |

## 3. 解法（测试侧三件套）

test_package 对协议进程的验证模式 = **启动握手断言 + 有界兜底 + 退出码合法化**：

```sh
# ── 断言 2: kfourinlineproc AI 进程启动握手（定稿形态）──
"$PROC" > "$KFIPROC_OUT" 2>&1 &
PID=$!
# 轮询最多 5 秒等 banner（banner = ELF 加载 + Qt 运行时初始化 +
# KGame 进程对象构造全部成功的证据）
i=0; FOUND=0
while [ $i -lt 25 ]; do
    grep -q "AI process starts up" "$KFIPROC_OUT" 2>/dev/null && { FOUND=1; break; }
    kill -0 $PID 2>/dev/null || break
    sleep 0.2; i=$((i + 1))
done
[ $FOUND -eq 1 ] || { cat "$KFIPROC_OUT"; kill -9 $PID; exit 1; }
kill -TERM $PID; wait $PID; RC=$?
# TERM 后 0/1/143 均合法（上游设计退出码 1；TERM=128+15=143）
case "$RC" in 0|1|143) echo "[test] ✅ rc=$RC";; *) exit 1;; esac
```

演进注记（CI 实测两版）：首版用 `PROC_OUT="$(timeout 15 "$PROC" < /dev/null 2>&1)"` + rc=124 判合法——banner 已验证启动握手成立，事件循环由 harness 有界终止；定稿版改后台 + banner 轮询 + TERM 收尾（不依赖 coreutils timeout 存在）。**两版核心语义等价：不断言进程自然退出，断言"启动握手成立 + 干净可终止"。**

**推广**：KGame IO 协议是 KDEGames 生态通用模式（kfourinline/kgoldrunner/kapman/ksirk/ksquares 等所有带 AI 进程的游戏同构）——后续此类游戏适配的 test_package 直接套用。

## 4. 降级方案

1. 不测 AI 进程，只测 GUI `--version`——覆盖度损失（proc 的 Qt 运行时 + KGame 构造链路漏测）；
2. 上游 patch 给 kwin4proc 加 EOF 退出路径——违背上游设计（协议进程只被父进程消息关闭），KDEGames 共享代码改动面大，拒绝；
3. CI 里放任挂死等 conan 超时——浪费整轮构建，禁止。

## 5. 红线

- ❌ 不要把"进程未自然退出"判为适配失败（上游设计如此）；
- ❌ 不要 kill -9 作为常规收尾（无法验证干净终止语义；-9 仅在 banner 缺失的失败路径兜底）；
- ✅ banner 断言是核心（启动握手 = 加载+初始化+构造全链证据）；
- ✅ rc 白名单要含上游设计返回码（本例 1）与 TERM 语义码（143）。

## 6. 覆盖判断（查重展开）

| 既有条目 | 覆盖内容 | 本条增量 |
|---|---|---|
| E464（MyGUI Dummy busy loop / SIGKILL 137 / headless） | 同 kill-兜底家族：图形资源注册缺失 + DataStream read 契约缺陷 → 忙循环被 SIGKILL | **触发协议完全不同**：KGame stdin/stdout 消息协议的退出语义（上游设计） vs 图形资源注册（实现缺陷）；修法方向相反：本条**不改源码改测试断言语义**，E464 是 patch 源码补实现 |
| DRAFT-8960-conan-test-package-cli-reads-stdin-to-eof（kea-shell） | 镜像问题：CLI 读 stdin 到 EOF（读到 EOF 才继续），测试侧须**显式给 EOF**（DEVNULL/echo \|） | 本条是**给了 EOF 进程也不退出**——cookie 解析器把 EOF 当半条消息自旋；解法从"喂 EOF"变成"握手断言+有界终止" |
| DRAFT-E569（mdp stdin /dev/tty freopen） | TUI 程序按键走 /dev/tty，测试须 pty 双通道 | 本条无 /dev/tty 依赖，是纯 IO 协议进程；坑点在退出语义而非输入通道 |
| E302（open_memstream cookie stream） | cookie 关键词撞名，glibc/musl 行为探针主题 | 无关：本条 "Cookie error" 是 KGame 协议解析器日志，非 libc |

三者合观：**stdin 语义故障族**（读等 EOF / EOF 不退 / TTY 重定向冲突）在知识库中各有一条，本条补齐第三类"协议进程 EOF 不退出"。

## 7. 复现方法（自含）

```sh
# 任一 KGame AI 进程（kfourinlineproc 为例）：
$ kfourinlineproc < /dev/null
# 观测：stderr 打 "AI process starts up" 后进入事件循环；
#       stdin 已 EOF → KMessageFilePipe cookie 解析循环刷 "Cookie error"，永不退出
# 另一终端：
$ kill -TERM <pid>; echo $?   # 143，干净终止
# 上游源码（26.04.0 tarball src/kgameprocess.cpp:39-40）：
#   d->rFile.open(stdin,  QIODevice::ReadOnly  | QIODevice::Unbuffered);
#   d->wFile.open(stdout, QIODevice::WriteOnly | QIODevice::Unbuffered);
```

## 8. 证据链

- PR #11104（kfourinline 26.04.0，calbee21，2026-09-19 merged）：
  - CI #51056/#51058：L0k commands.json 类型门禁红（修前另一问题，同一 PR 的完整时间线）；
  - CI #51100/#51114：absolute-NEEDED 库加载失败（KF6 构建机绝对路径，commit `b957a32c3a` 修复）；
  - **CI #51150：test.sh 含 kfourinlineproc timeout 15s + rc=124 合法化断言——全绿**（本条修法定稿轮）；
  - CI #7835（REL-003 release）：conan-upload + sign-artifacts 全绿，PR merged；
- 定稿代码：archives/k/kfourinline/26.04.0/test_package/test.sh 断言 2（banner 轮询 + TERM 收尾）；notes.md "Verification" 节记录上游设计说明；
- commit 链：`5a1146acad`（首版 timeout 方案）→ `b957a32c3a`（NEEDED 兼容层）→ `fd69863645`（清理 kfiproc.out）。
