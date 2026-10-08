# DRAFT — 无界 `while printf` 管线 fixture 依赖写端进程自身死于 SIGPIPE 才能终止；OHOS /bin/sh（toybox）无 printf 内建导致每轮 fork 外部写端、循环永不终结——应改有限输出生产者（或内建写端 shell）

> B 申报草稿（配额 1/2，PENDING_PAYLOAD）。申报域：musl/libc 与 toybox 差异（shell 能力差异），相邻系统调用限制（open point 部分）。分层：L1 平台/工具链/构建系统语义层。最终编号 Exxx 由知识库主编确认，本稿不自行编号。

## 错误特征

- `go test` 某包挂死直至默认 10 分钟超时：`panic: test timed out after 10m0s`，goroutine 栈消费方停在 `os/exec.(*Cmd).awaitGoroutines [chan receive]` / `cmd.Wait()`；权威 CI 报 `FAIL <pkg> 600.612s`、`conan create failed`。
- 涉事 fixture 形态：`无界生产者 | head -c N`（本例：`while :; do printf ...; done | head -c$(( 2 << 20 ))`）。
- 挂死进程残留两种形态：fork 再生 spin（`sh` 循环不断 fork 外部 printf），或写端阻塞在 `write()`（D 态、TERM/timeout 免疫，活体残留可存活数小时）。

## 触发条件

- 构建系统: 任意（Go `go test`、shell 测试 fixture、CI 包装脚本均可）
- 阶段: testing（管线式测试数据生产）
- 平台: OHOS（/bin/sh = toybox 306288 字节，无 printf 内建；`sh -c 'type printf'` → "printf is an alias for printf"，指向外部 applet）
- 代码形态: 测试 fixture/脚本使用『无界生产者 | head -c N』，其终止依赖"SIGPIPE 杀死写端进程"

## 根因分析

1. **POSIX 终止机制**：`无界生产者 | head -c N` 能终止，是因为主流 /bin/sh（bash/dash/mksh）把 printf/echo 作为**内建**执行——循环进程自己就是写端；head 退出后内建写端死于 SIGPIPE，`while` 循环终结，管线达到 EOF。
2. **OHOS 差异**：toybox sh 无 printf 内建 → 每轮循环 **fork 新的外部写端进程**；单个写端进程死于 SIGPIPE 不终止 `while :` 循环 → 写端无界再生 → 管线永无 EOF → 消费方 `cmd.Wait()` 永久阻塞 → go test 10 分钟超时 panic。
3. **控制实验（Curator/Auditor 独立复现，全部 `timeout -s KILL` 有界）**：同设备简单管线的 EPIPE/SIGPIPE 投递**本身正常**——bash 内建写端循环、登录 shell 建管的外部 seq、toybox sh 建管的 seq 在读端退出后全部同秒终结。微分对照：裸 `echo` 循环（toybox sh 进程内执行）同秒终结；`/bin/echo`、`/bin/printf` 外部循环同样挂死。**决定变量 = 写端在循环进程内（内建）执行还是 fork 外部 applet**，不是内核级 EPIPE 缺失（早前"内核读端关闭不返回 EPIPE"的表述已被控制实验驳回，本稿为修正版机理）。
4. **Open point（如实记录，不得写成内核级结论）**：fork 再生 spin 与写端阻塞 write()（D 态、TERM/timeout 免疫）两种挂死形态的确切切换条件（内核满缓冲写与读端可见性的交互、toybox sh 管线 fd 布线）尚未定性。
5. 侧证：既有草稿（早退 `readelf|grep -q` 场景）记录 LLVM readelf 对早退管线正常收到 EPIPE 并以 74 退出——与"投递正常"一致。

## 解决方案

### 推荐方案：有限输出生产者（已验证，可上游提交）

用 `dd`/`seq` 等有限生产者产出**等量字节**，消除对 SIGPIPE 终止的依赖；不触碰消费方断言（本例 Go 断言仅校验截断后捕获长度 1<<20，与内容无关）；POSIX 与 OHOS 双侧语义保持。

```sh
dd if=/dev/zero bs=$(( 2 << 20 )) count=1
```

### 回退方案（诚实权衡，仅作退路）

fixture 改用带内建写端的 shell（`#!/data/service/hnp/bin/bash -eu`）保留无界形态。权衡：依赖设备上非标准 bash 路径，可移植性差，掩盖兼容性而非修复——优先用推荐方案。

### 禁止做法

- ❌ 为绕过挂死而跳过/禁用上游测试（如跳过 TestHooks）或修改 Go 断言——污染上游判定，平台限制应降级记录而非绕过（P013）。
- ❌ 新增"终止依赖 SIGPIPE 杀死写端且写端为 fork 外部 applet"的无界生产者 fixture。
- ❌ 按 `type` 输出做 printf→echo 互换"假修复"：`type` 对 echo 同样报 alias，但 `/bin/echo` 外部循环同样挂死；裸 echo 能过是因为 toybox sh 将其**内建执行**——判断内外建要看循环形态探针，不要信 `type` 单词面。

## 验证

（设备新 shell 直接可跑，逐条有界 ≤6s；P2-P4 同秒完成为"投递正常"判据，P5 挂满被 KILL 为"机理复现"判据）

```bash
# P1 对照：timeout/KILL 机制正常（耗整 5s 被杀）
timeout -s KILL 5 bash -c 'while :; do :; done'

# P2 内建写端：EPIPE/SIGPIPE 投递正常（同秒完成）
timeout -s KILL 5 bash -c 'while :; do echo xxxxxxxxxx; done' | head -c 10

# P3 登录 shell 建管的外部写端：同秒完成，无残留
timeout -s KILL 5 sh -c 'seq 1 2000000' | head -c 10

# P4 toybox sh 建管的外部写端：同秒完成，无残留
timeout -s KILL 5 sh -c 'seq 1 2000000 | head -c 10'

# P2-P4 事后复核无残留
ps -ef | grep -E 'seq|while :' | grep -v grep

# P5 机理复现（危险！必须 KILL 包裹；timeout 只杀顶层 sh）
# 挂满 5s 被 KILL = 复现。会留下 TERM 免疫的 while 子壳/printf 子进程，
# 事后必须 kill -9 清理全部残留并 ps 复核清零。
timeout -s KILL 5 sh -c 'while :; do printf x; done | head -c 10'
ps -ef | grep -E 'printf x|while :' | grep -v grep   # 如有残留: kill -9 <pid>
```

修复实证：同一 fixture 改 `dd if=/dev/zero bs=$((2<<20)) count=1` 后，hooks 包在该设备权威 CI 中 3.018s ok；消费方断言零改动。

## 关联条目

- 相似/同族: E010（toybox 能力差异族）、E402（toybox applet 语义差异）、E074（管线/FIFO 相邻）
- 原则: P005（补丁可上游提交）、P013（平台限制降级而非绕过）
- 交叉引用草稿: DRAFT-E568 族（CI stdin 开放空管→读侧 fgets 永久阻塞，机理不同）；E569-draft-BCF3（早退管线写端 EPIPE 正常投递——本条机理的侧证，非重复）
- 案例: 某 Go 备份/复制工具 0.7.0 的 hook 测试 fixture（有限生产者 patch 已随其 feat 分支交付）

## 沉淀价值与查重（B 两段审计摘要）

- **价值**：可复用问题类别="管线 fixture 终止依赖写端内建性"的设计约束；适用所有 shell-hook/管线式测试、CI 包装脚本及后续 busybox 系测试迁移；能把"go test 600s panic 无输出"的诊断收敛到首查 fixture 生产者形态；并纠正"该平台内核不投递 EPIPE"的错误认知（防未来误判内核缺陷）。
- **去重**：knowledge/graph（546 文件）与 knowledge/drafts 全量 grep EPIPE/SIGPIPE/broken pipe/管道——图内命中 E008/E009/E074/E076/E106/E161/E167/E458 逐条实读均为不同机理（fstat/lseek EACCES、SELinux 域、jobserver FIFO、GNU cat stdout SIGPIPE、stdin fstat、config.status 临时目录、restinio sendfile 应用层）；drafts 中 E568 族=读侧 stdin 空管阻塞、E569 族=早退管线 EPIPE 正常投递（侧证）、E654/7605 等均不同；经验仓全目录 grep 0 命中。确认无覆盖，新增价值成立。
