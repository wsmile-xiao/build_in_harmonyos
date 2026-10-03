# E545 — 守护进程类 CLI 的 pty 测试只能抓到单帧（script 随前台父进程退出即销毁 pty）

> Draft（待知识库主编审核 promote）｜对应: `knowledge/drafts/E545-draft-0BF2.kv`
> 来源包：spinner/1.2.4（OHOS PC aarch64）

## 错误特征

测试脚本给守护进程类 CLI 的 pty 断言只抓到**一帧**输出，且加大 `timeout`
完全无效——多次运行字节数完全相同：

```
ok E1 - daemon run on a pty emits output (bytes=12)
timeout=6  -> bytes=12 frames=1
timeout=12 -> bytes=12 frames=1
timeout=20 -> bytes=12 frames=1
```

若把守护进程改成后台运行（`&`），则一帧都抓不到，并伴随：

```
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
```

## 触发条件

- 构建系统: 任意（与构建无关，是**测试方法**问题）
- 阶段: testing
- 被测对象: fork 出后台守护进程、核心行为是"周期性向控制终端写输出"的 CLI
  （tty 动画 / 连接保活 / 进度类守护进程）
- 测试手法: `script -qc "<daemon> ..." /dev/null`

## 根因分析

pty 的生命周期与**前台进程**绑定，与守护进程无关：

1. 被测程序 fork 出守护子进程后，前台父进程立即退出；
2. pty 由 `script(1)` 分配，`script` 随前台父进程退出而销毁 pty；
3. 守护子进程失去控制终端，再写 pty 即触发 SIGSEGV。

所以 `timeout` 设多大都没用——`script` 根本没在等守护进程。而改成 `&` 后台化
同样因为失去控制终端而变成 0 帧。

**根因是"以为 pty 会在 timeout 内一直存在"，实际 pty 的寿命 = 前台进程寿命。**

## 解决方案

### 推荐方案

在同一 shell 内让守护进程**保持前台**，并追加 `sleep` 撑住 pty：

```sh
TERM=vt100 timeout 25 script $style "sh -c '<daemon> -F -T 1; sleep 6'" spin.ts \
    > spin.out 2> spin.err
cat spin.ts spin.out > spin.all        # 两个输出通道求并集（见 E547）
```

> ⚠️ typescript **不要**指向 `/dev/null`：部分 `script` 实现只写 typescript 文件
> （实测 HarmonyOS worker 即如此），那样会丢光输出，且本地 util-linux 环境仍全绿。
> 详见 **E547**。

实测该手法可稳定抓到 6~14 帧（spinner 1.2.4 实测 14 帧 / 168 字节）。

断言要从"有输出"升级为"**在持续旋转**"——按完整帧计数，而不是按字节数：

```sh
HEAD=$(printf '\0337\033[H\033[7m')       # ESC7 + ESC[H + ESC[7m
frames=$(LC_ALL=C grep -a -o -F "$HEAD" spin.out | wc -l)
gate $([ "$frames" -ge 3 ] && echo 0 || echo 1) E2 "daemon sustains rotation: >=3 frames (frames=$frames)"
```

⚠️ 必须用 `grep -F`：VT100 序列含字面 `[` `]`，当正则会被解释成字符组，
导致帧计数恒为 0（本项目实际踩过一次）。

字形覆盖可按字逐个定长匹配：

```sh
LC_ALL=C grep -a -q -F "$HEAD\\" spin.out && g_bs=1
LC_ALL=C grep -a -q -F "$HEAD|" spin.out && g_pipe=1
LC_ALL=C grep -a -q -F "$HEAD/" spin.out && g_slash=1
LC_ALL=C grep -a -q -F "$HEAD-" spin.out && g_dash=1
glyphs=$((g_bs + g_pipe + g_slash + g_dash))
```

### 禁止做法

- ❌ `script -qc "<daemon> -F -T 1" /dev/null`（不加 `sh -c` 包裹）——父进程一退 pty 即销毁
- ❌ `script -qc "sh -c '<daemon> ... & sleep 6'"`——后台化使守护进程失去控制终端
- ❌ 用 `grep -o`（正则模式）匹配含 `[`/`]` 的转义序列
- ❌ typescript 指向 `/dev/null`——见 E547

### 回退方案

宿主无 `script(1)` 时用 Python 的 `pty` 模块分配 pty：

```sh
python3 -c "import pty; pty.spawn(['<daemon>','-F','-T','1'])"
```

仍不可用则把该组断言标记 **skipped** 并在汇总行显式打印 skipped 计数
（不要打印成 `ok`，否则会被误读为通过）。

## 验证

```bash
# 命中本模式：三次 timeout 结果字节数相同
for t in 6 12 20; do
  timeout $t script -qc "<daemon> -F -T 1" /dev/null | wc -c
done

# 修正后：应看到远大于单帧长度的输出
TERM=vt100 timeout 20 script -qc "sh -c '<daemon> -F -T 1; sleep 6'" /dev/null | wc -c
```

## 关联条目

- 原则: R34（测试必须实质依赖被测包的真实行为，不能只验证"吐过东西"）
- 相关: E429（autotools 应用型配方 DESTDIR staging）
