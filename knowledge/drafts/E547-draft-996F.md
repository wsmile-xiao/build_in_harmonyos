# E547 — pty 测试里把 script 的 typescript 指向 /dev/null，会在部分实现上丢光输出

> Draft（待知识库主编审核 promote）｜对应: `knowledge/drafts/E547-draft-996F.kv`
> 来源包：spinner/1.2.4（修 CI 构建 #66242 时定位）

## 错误特征

本地 `conan create` 全绿，远端 CI 却红在 pty 断言上，字节数为 **0**：

```
ok A1 - -L exits 64 (EX_USAGE, upstream usage.c License())
...
ok D7 - refused run leaves no pid file behind (fails before daemonising)
FAIL E1 - daemon run on a pty emits output (bytes=0)
ERROR: spinner/1.2.4 (test package): Error in test() method
```

同时注意：**编译与打包都成功了**（`Packaged 2 files: spinner, COPYING`），
所以这不是构建缺陷，而是**测试 harness 的环境假设不成立**。

## 触发条件

- 构建系统: 任意（与构建无关，是**测试方法**问题）
- 阶段: testing
- 测试手法: `script -qc "..." /dev/null > out`
- 被测对象: 需要真实 tty 的程序（`isatty()` 检查 / `tcdrain()`），
  典型是 fork 出守护进程、周期性向控制终端写 VT100 帧的 CLI

## 根因分析

`script(1)` 各实现对"会话输出写到哪里"**不一致**：

| 实现 | stdout | typescript 文件 |
|------|--------|-----------------|
| util-linux `script` | 写 | 写 |
| 部分实现（实测 HarmonyOS worker 上的 `script`） | **空** | 写 |

于是原写法 `script -qc CMD /dev/null > spin.out`：

- 在**本地 WSL + qemu** 上：util-linux 版两个通道都写，`/dev/null` 吞掉的那份
  从 stdout 仍能取到 → **本地全绿，缺陷被掩盖**；
- 在 **worker** 上：只写 typescript，而它指向 `/dev/null` → 输出全丢 →
  `spin.out` 为 0 字节 → `bytes=0`。

还有第二层风险：合并写法 `-qc` 并非所有实现都接受，严格实现会直接报错退出。
所以"本地通过"在这里完全没有说服力，必须显式覆盖不同 runner 实现。

## 解决方案

### 推荐方案

1. **typescript 指向真实文件**，并在断言前把两个通道**并集**后统计：

```sh
script $style "sh -c '<prog>; sleep 6'" spin.ts > spin.out 2> spin.err
cat spin.ts spin.out > spin.all          # 两种实现都覆盖
frames=$(LC_ALL=C grep -a -o -F "$HEAD" spin.all | wc -l)
```

2. **用与被测程序无关的探针判活**，依次尝试两种调用形式：

```sh
PTY_STYLE=""
for pstyle in "-qc" "-q -c"; do
    : > probe.ts; : > probe.out
    TERM=vt100 timeout 15 script $pstyle "printf PTYPROBE" probe.ts > probe.out 2>probe.err
    grep -q 'PTYPROBE' probe.ts probe.out && { PTY_STYLE="$pstyle"; break; }
done
```

探针成功才跑被测程序；探针失败则该组记 **skipped** 并显式打印，
**绝不把 runner 差异误报成被测程序缺陷**。

### 禁止做法

- ❌ `script -qc CMD /dev/null > out` —— typescript 指向 `/dev/null`
- ❌ 跳过探针直接断言 —— 无法区分"harness 不可用"与"程序不输出"
- ❌ 把守护进程用 `&` 放到后台 —— 会失去控制终端，写入已销毁的 pty 触发 SIGSEGV

### 回退方案

用 Python 的 `pty` 模块自己分配 pty，完全绕开 `script` 的输出通道语义：

```sh
python3 -c "
import os, pty, select
pid, fd = pty.fork()
if pid == 0: os.execvp('sh', ['sh','-c','<prog>; sleep 6'])
buf=b''
while True:
    r,_,_=select.select([fd],[],[],1.0)
    if not r: break
    d=os.read(fd,4096)
    if not d: break
    buf+=d
open('spin.all','wb').write(buf)
"
```

代价：引入 python3 依赖，且要自己处理超时与僵尸回收。

## 验证

四种环境组合都应得到预期结果（缺 pty harness 时显式 skip 而非失败）：

```bash
# harness 可用 → 37/37；把 script 换成"只写 typescript"的实现也应 37/37
script -qc "printf PTYPROBE" /tmp/probe.ts > /tmp/probe.out 2>&1
grep -c PTYPROBE /tmp/probe.ts /tmp/probe.out
```

## 关联条目

- 原则: R34（测试必须实质依赖被测包真实行为，且不能把环境问题伪装成通过/失败）
- 相关: E545（pty 必须挂住，否则守护进程只吐一帧）、E546（门禁对补丁说明的无上下文子串误报）
