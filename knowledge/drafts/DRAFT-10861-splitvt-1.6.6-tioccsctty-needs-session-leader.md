# fork 后想夺取 pty 控制终端的子进程必须先成为会话首进程：`ioctl(TIOCSCTTY)` 在非会话首进程上静默失效

## 基本信息
- **严重度**: 2
- **类别**: platform, portability, pty, process-control
- **来源包**: splitvt 1.6.6（`misc.c:dropctty()`，补丁 0005）
- **触发阶段**: runtime（编译/链接全程无错，构建门禁发现不了）

## 错误特征
没有错误输出，只有行为签名：**用户敲进子窗口的命令被回显、却永远不被执行**，子窗口也不出现 shell 提示符。
观察面（本项目实测）：`输入被回显但命令不执行` / `子窗口无 shell 提示符` / `typed command echoed without execution`。

## 根因分析
POSIX/SVr4 规定 `ioctl(fd, TIOCSCTTY, 0)` **只允许会话首进程**调用。老代码常把 `setsid()` 留在 `_POSIX_SOURCE` 之类的旧编译分支里，其它分支只做 `setpgid()` + `TIOCNOTTY`：

- `setpgid()` 只改进程组，**不创建新会话**；
- 于是 fork 出的子进程既不是会话首进程、也没有控制终端，`TIOCSCTTY` 无法把它绑定到新 pty；
- 子窗口里的 shell 因此认定自己是后台作业，不接管 tty；ldisc 仍然回显输入，但命令不被读走执行。

⇒ 症状是"看起来活着、永远不响应回车"，而不是崩溃或报错，定位成本高（本案在真 pty 上做 A/B 才钉住）。

## 推荐方案
**方法**: gate-setsid-on-TIOCSCTTY-capability-not-legacy-macro

把"是否 `setsid()`"的判据从旧编译宏改成**能力判据**：凡系统提供 `TIOCSCTTY` 者，一律在子进程先 `setsid()`，再 `ioctl(0, TIOCSCTTY, 0)`；原 `TIOCNOTTY` 语义保持不变。

```
# 改前：#if defined(_POSIX_SOURCE)
# 改后：#if defined(_POSIX_SOURCE) || defined(SOLARIS) || \
#                defined(__386BSD__) || defined(__FreeBSD__) || \
#                defined(TIOCSCTTY)
        setsid();
```

`TIOCSCTTY` 由系统 `<sys/ioctl.h>` 直接给出，判据就用 `defined(TIOCSCTTY)`：既**不是**写死平台名，也**不需要** configure 额外探测出另一枚 `HAVE_` 前缀的能力宏——上游 `config.c` 的探测清单与本仓归档里都不存在那样的宏，照那种字面写会让条件永假、缺陷复发。

**禁止**:
1. ⛔ 用 `__OHOS__` / `-D__OHOS__` 之类平台宏做分支（掩盖了"这是能力差异而非平台差异"的事实，且平台禁则）。
2. ⛔ 放宽或删掉前台判定/`TIOCSCTTY` 调用让程序"跑起来"——那是把功能砍掉冒充通过。
3. ⛔ 只在测试里加 sleep 等提示符出现；本缺陷与调度无关，是绑定失败。

## 验证方式
同一份源码只改 `dropctty()` 的一支，各构建一次，在真 pty 下跑：

```
splitvt -norc -upper /bin/sh -lower "/bin/echo LOK"
# 向 master 写入：echo XOLY<CR>
```

| 构建 | 子窗口提示符 | 命令是否执行 |
|---|---|---|
| 未扩 POSIX 支（`setpgid` + `TIOCNOTTY`） | 无 `$` | 只回显 `echo XOLY`，**不输出** `XOLY` |
| 扩 POSIX 支（`setsid()`） | 有 `$ ` | 输出 `XOLY` ⇒ 真执行 |

消费者测试把这条钉成两条断言：`upper window shell became interactive`、`command typed into the upper window was executed`。

## 影响范围
所有"fork 子进程 + 在子进程里 `TIOCSCTTY` 绑定 pty"的程序：终端多路复用器、屏幕键盘、pty 包装器。判据只有一条——**把 legacy 分支接到本平台时，`setsid()` 是否还被旧编译宏挡着**。与具体发行版无关，与 glibc/musl 无关。
