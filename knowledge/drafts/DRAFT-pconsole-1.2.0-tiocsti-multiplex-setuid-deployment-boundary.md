# DRAFT-pconsole-1.2.0 — 靠 TIOCSTI 往别的 tty 注入按键的工具，在鸿蒙上的可交付边界

> 草稿（draft: true），待主编审核后 `graph promote` 为正式 E 条目。
> 来源任务：pconsole 1.2.0 适配 HarmonyOS PC（分支 `feat/pconsole-1.2.0`，2026-09-30）。
> 同行：`knowledge/drafts/DRAFT-pconsole-1.2.0-tiocsti-multiplex-setuid-deployment-boundary.kv`

## 知识缺口（查重结论）

| 已有条目 | 覆盖了什么 | 与本条的关系 |
|---|---|---|
| `DRAFT-secpwgen-1.3-e051-*` | 特权 id syscall（seteuid 等）在鸿蒙被 SIGSYS 打死，PF5 兼容修法是 POSIX 空操作守卫 | pconsole **直接使用**该方案（唯一补丁即此），不重复申报 |
| `DRAFT-E5xx-tui-app-pty-test-harness` | TUI 程序非 tty 即 abort，测试要 pty 驱动 | pconsole **直接使用**该方法论，不重复申报 |
| `DRAFT-8960-*` | 被测 CLI 读 stdin 到 EOF，CI 的永不关闭管道挂死 | 同一族陷阱的另一种形态；本条补的是"驱动脚本轮询不收敛"（见禁止做法 1） |
| `DRAFT-10861-splitvt-*` | `TIOCSCTTY` 需要会话首进程 | 同一个 pty 家族，但讲的是**控制终端绑定**，不是**输入注入** |
| `grep -rl TIOCSTI knowledge/drafts/` | **命中 0** | 本仓 drafts 里没有任何条目讨论过 `TIOCSTI` |

本条目补的正是这一格：**按 E051 的方案让程序活下来之后，这个工具到底还能不能工作。**

## 错误特征

```
ioctl() : Invalid argument          # 或 Operation not permitted / Not a typewriter / EPERM
You must be root to run this program or this program should be setuid root.
cannot create a pconsole loop
already attached
exit code 159 | Bad system call     # E051 面：特权 id syscall 被 SIGSYS 打死
```

## 触发条件

- 构建系统: 任意（问题在运行期，不在编译期）
- 阶段: 运行时 / test_package
- 前置条件: 程序**必须能往别的 tty 的输入队列里写字节**——`ioctl(fd, TIOCSTI, &c)`
- 平台: 任何对 legacy tty ioctl 有开关或权限限制的内核（Linux 6.2+ 的
  `dev.tty.legacy_tiocsti` 默认 0；鸿蒙沙箱另有白名单 seccomp）

## 根因分析

### 1) TIOCSTI 的可用性不是编译期属性，是内核运行期开关

`TIOCSTI` 从未进入 POSIX，只是被各 UNIX 一直实现着。因为它等价于「绕过终端输入检查
直接往别人的 tty 塞字符」，内核后来加了 `dev.tty.legacy_tiocsti` 开关，并在 Linux 6.2
起**默认关闭**；关闭时 ioctl 返回 `EINVAL` 而不是成功，调用方还得对目标 tty 有权限。

于是同一个二进制在两台机器上表现不同：一台能把按键注入出去，另一台只能报
`ioctl() : Invalid argument`。

> 特别提醒：源码里 `#ifndef TIOCSTI / #define TIOCSTI 0x5412` 这类自备兜底定义
> （pconsole.c 里就有）**只保证能编译，不保证能用**。用它推出"功能可用"是错的。

### 2) root 门控 + 特权 id syscall 的组合把可交付面锁死

这类工具 `main()` 开头几乎都是同一个模式（pconsole.c:220-232）：

```c
if (geteuid()) {
    fprintf(stderr, "You must be root to run this program or this program should be setuid root.\n");
    return -1;
}
if (seteuid(getuid())) {        /* 无条件"保险式"丢权 */
    fprintf(stderr, "failed to drop root privileges\n");
    exit(-1);
}
```

鸿蒙的应用沙箱**不给应用进程 root**，setuid 位也绕不过白名单式 seccomp。所以：

- 门控本身在鸿蒙上永远过不去（沙箱不是 root）；
- 绕过门控的路径又被 seccomp 封死（`seteuid` → 不可捕获 SIGSYS，exit 159）。

叠加结果：**这不是靠打补丁能"修好"的东西，它是平台能力边界。**
适配方能做的是两件事，各做各的：

1. 把补丁做成**语义等价的空操作消除**（`geteuid() != getuid() && seteuid(...)`），
   让"以 root 身份运行"这条路在鸿蒙上走得通；
2. 把测试断言钉在**真实可达的那部分面**上，并对不可达的部分**如实说明**，
   而不是把功能砍掉冒充通过。

## 解决方案

### 推荐方案：先探测 TIOCSTI 能力，再按能力选断言形态

绝不要假设可用，也不要假设不可用。harness 里用**一次性探针 pty** 测能力：

```python
import ctypes, os, pty
TIOCSTI = 0x5412

m, s = pty.openpty()                      # 一次性探针，不复用被测的 pty
try:
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    buf = ctypes.c_char(b"\x01")          # 探针字节，与送达判据的字节区分开
    ctypes.set_errno(0)
    tiocsti_ok = libc.ioctl(s, TIOCSTI, ctypes.byref(buf)) == 0
finally:
    os.close(m); os.close(s)
```

再按能力分两条**都非恒真**的断言：

| 能力 | 断言 | 为什么非恒真 |
|---|---|---|
| 可用 | 注入的字节真的出现在目标终端（从 pty **master** 侧读回） | 假壳/未 attach/未进入注入态都会 FAIL |
| 不可用 | 程序报出 `ioctl() : ...` 并干净 detach，rc=0 | 崩溃或静默吞掉错误都会 FAIL |

euid 分支也要显式写出来：`euid != 0` 时断言程序**自己的**门控消息 + 非 0 退出
（即 E051 那条门），`euid == 0` 时才跑完整功能面。这样两种宿主环境下断言都非空。

### 三个实现坑（本包全部踩过）

1. **探针必须用另一个 pty**。往被测 pty 注入探针字节，会污染"字节有没有送达"的判据。
2. **送达判据要用可打印字符**。canonical 行规程对控制字符做 `ECHOCTL` 展开，
   注入 `\x18`（Ctrl-X）后 master 侧读到的是 `^X`（两个字符），
   `b"\x18" in delivered` 会**假失败**。本包最初就栽在这里。
3. **命令模式里敲的字符不会被注入**。Ctrl-A 是"进命令模式"，命令模式里输入被
   `fgets` 吃掉并当命令解析；只有 `connect`/`exit` 才回到注入循环。
   想测注入必须在**注入态**下敲——`pconsole <tty>` 启动后（attach 成功）默认就在注入态，
   输出是 `Press <Ctlr-A> for command mode` 而不是 `>>> `。

### 送达是从 master 侧读的

`TIOCSTI` 把字符塞进 **slave** 的输入队列，行规程回显（`ECHO`）后，字节才从
**master** 读出来。只从 slave 读是读不到的。

## 禁止做法

1. ❌ **在自动化测试里带参数调用驱动脚本**。pconsole.sh 这类脚本靠
   `while [ -z "$TTY" ]; do TTY=$(get_tty)` 找目标 tty；无控制终端时 `tty` 失败 →
   判定条件恒假 → 子 shell 无限自旋。CI 表现是"构建超时/疑似交互式测试卡住"，
   排查成本极高且与真实缺陷无关。**只测无参数路径**（打印 usage 后 `exit 1`）。
2. ❌ **把源码自带的 `TIOCSTI` 兜底定义当成能力证据**。它只保证编译通过。
3. ❌ **把注入失败静默吞掉**（`if (ioctl(...)) ;` 空实现）。那是把核心功能砍掉冒充通过。
4. ❌ **在配方 install 阶段替用户 `chmod 4110` / `chown root`**。README 的 setuid 建议
   是部署动作，不是包管理职责；改制品安全属性会被审计判高危。

## 验证方式

```bash
# 1) 能力探测（任何 Linux 宿主，5 秒）
python3 -c 'import ctypes,os,pty; m,s=pty.openpty(); \
  l=ctypes.CDLL("libc.so.6",use_errno=True); b=ctypes.c_char(b"\x01"); \
  print("rc=%d errno=%s" % (l.ioctl(s,0x5412,ctypes.byref(b)), os.strerror(ctypes.get_errno())))'
#   rc=0  → 该内核允许注入
#   rc<0  → 被 legacy_tiocsti 关掉(EINVAL) 或调用方无权限(EPERM)
#   两种结果都**不**代表配方有问题

# 2) 补丁 A/B（不依赖真机 seccomp，本包实证）
#    同一份源码、同一套工具链各构建一次，数特权 id syscall 次数：
strace -f -qq -e trace=setuid,setresuid,setreuid,getuid,geteuid -o /tmp/s.txt \
  <被测程序> </dev/null
grep -cE 'set(res|re)?uid' /tmp/s.txt
#   未打补丁: 1  → setresuid(-1, 0, -1) = 0
#   已打补丁: 0  → 只剩 geteuid/getuid 判定，syscall 根本没发出
# 注意：**不要**用符号表做判据——守卫是运行期判定，seteuid 符号两个构建里都在。

# 3) 反证（CI L1e 口径）：产物换成空目录或 `echo stub` 假壳，测试必须 FAIL
#    本包实测：假壳 → pty harness 14/16 FAIL rc=1

# 4) 设备侧终态证据：真实 HarmonyOS PC worker 上跑 conan create 的 test_package，
#    确认启动路径退出码 ≠ 159（E051 边界），且 root 门控行为符合预期
```

## 证据

- 配方：`archives/p/pconsole/1.2.0/`
  - `patches/0001-pconsole.c-seteuid-noop-guard.patch`（+2/-2，2 hunk，无平台宏）
  - `test_package/pconsole_pty_test.py`（M1/M1b/H3/H4 按能力与 euid 分支断言）
  - `test_package/test.sh`（注释写明"带参数调用驱动脚本会自旋，不要这样测"）
- 本机验证：`conan create` rc=0；test_package 29/29 通过；
  strace A/B = 未打补丁 1 次 / 打补丁 0 次；反向验证假壳 14/16 FAIL。
- 宿主环境差异如实记录：本机 WSL 的内核**允许** TIOCSTI（rc=0），因此本机走的是
  「注入送达」这条真分支；鸿蒙 worker 若禁用该 ioctl，harness 会自动切到
  「ioctl 错误 + 干净 detach」分支，两条都不是恒真断言。

## 元信息

- authors: pconsole-1.2.0 适配任务
- source_event: pconsole 1.2.0 OHOS aarch64 conan create（2026-09-30）
- draft: true — 待主编审核后 promote 为正式 E 条目
