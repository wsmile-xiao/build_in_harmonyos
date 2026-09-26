# DRAFT：交互式 termios 口令读取——恢复前二次 `tcgetattr` 会让 `tcsetattr` 变空操作

> Contributor: CIW ｜ Status: Draft ｜ Updated: 2026-09-21
> Source: mini-httpd 1.30 适配（PR #11542，musl/OHOS，`htpasswd` 工具）
> 同 stem 知识文件：`DRAFT-mini-httpd-1.30-termios-restore-in-interactive-getpass.kv`

## 背景

`mini-httpd` 的 `htpasswd` 工具在 musl/OHOS 上需要补丁才能编译（musl 无 glibc 的 `getpass` 语义）。
补丁按上游原有结构实现：关闭终端回显 → 读口令 → 恢复终端状态。功能在**构建与自动化测试**上完全正常，
但 AI 静态审查在整改版上标出一个 P2：**恢复终端状态前又读了一次 termios**，导致恢复失效。

## 错误特征

- 交互式（`stdin` 是 tty）执行 `htpasswd -c pwfile user`，输入口令后**终端 ECHO 不再恢复**，用户看不到后续输入；
- 进程退出码 0、无任何报错、无日志；
- **自动化消费者测试与 CI 全部通过**——因为测试的 `stdin` 是管道/文件，根本不进 `isatty()` 分支。

## 根因分析

```c
/* 关闭回显 */
if (tcgetattr(STDIN_FILENO, &told) == 0) {
    struct termios t = told;
    t.c_lflag &= ~ECHO;
    (void) tcsetattr(STDIN_FILENO, TCSAFLUSH, &t);
}
/* ... 读取口令 ... */
if (tcgetattr(STDIN_FILENO, &told) == 0)        /* ← 二次读取：把"已关回显"的状态覆盖进 told */
    (void) tcsetattr(STDIN_FILENO, TCSAFLUSH, &told);   /* 写回同一状态 → 空操作 */
```

`told` 本应保存**修改前**的原始状态；第二次 `tcgetattr` 把"当前（已关闭 ECHO）"读进了同一个变量，
于是恢复动作写回的还是"关闭"状态。**这不是概率问题，是确定性逻辑错误**，只是触发条件需要 tty。

同类缺陷在别处的表现形式可能更隐蔽：有些实现是"保存一次 + 恢复两次"或"恢复用了 `TCSANOW` 改了排空语义"，
审查要点相同——**恢复行之前不得出现第二次读取**。

## 推荐方案

**保存一次、写回一次，并用标志守卫**：

```c
int tty_changed = 0;
if (tcgetattr(STDIN_FILENO, &told) == 0) {
    struct termios t = told;
    t.c_lflag &= ~ECHO;
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &t) == 0)
        tty_changed = 1;
}
/* ... 读取口令 ... */
if (tty_changed)
    (void) tcsetattr(STDIN_FILENO, TCSAFLUSH, &told);   /* 写回的是"关之前"的原始状态 */
```

顺带清理同一函数里因"剥离换行前取长度"造成的不可达分支（如 `if (len > sizeof(buf)-1) password[sizeof(buf)-1] = 0;`）。

**静态审查口径（可直接进 checklist）**：任何"关回显 → 恢复"的代码块，`tcsetattr` 之前不允许出现第二次 `tcgetattr`。

## 适用范围与反例

- **适用**：自行用 termios 实现口令读取的上游（musl/OHOS 上更常见，因为直接调 libc `getpass` 的少）；
  htpasswd/auth 类工具、带交互式 `--password` 提示的 CLI、服务端管理工具。
- **不适用**：直接调用 glibc `getpass`（其内部实现正确）的包。
- **反例/边界**：仅在 tty 下触发 ⇒ **不能用"自动化测试通过"证明此缺陷不存在**；
  修补丁也不得改成 `TCSANOW` 之类改变排空语义的写法。

## 验证证据

- 补丁 `patches/0001-musl-getpass.patch`：新增 `int tty_changed = 0;`，首次 `tcgetattr` 成功置 1，
  恢复改为 `if (tty_changed) (void) tcsetattr(STDIN_FILENO, TCSAFLUSH, &told);`，并删除不可达的 `len > 80` 分支。
- 设备本地 `conan create archives/m/mini-httpd/1.30 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` 通过；
  消费者 smoke 输出 `mini-httpd consumer OK: htpasswd + HTTP round-trip`（**非 tty 路径**）。
- 交互式 tty 分支无法在无 pty 的 CI 中触发：证据为源码逻辑 + 对照仓库既有"只保存一次"的实现
  （`apg` / `bacula-client` / `isync` 等包的同类代码）。
- **如实标注**：本条的交互路径**未经自动化验证**，属人工/静态审查发现。

## 新增价值（查重说明）

- 既有条目覆盖的是"musl 缺 `getpass` / 相关符号缺失 → 需要补丁"（符号与构建层面）；
  **本条覆盖的是补丁内部的终端状态机错误**——即"补丁写对了能编译，但交互语义写错了"，
  且明确指出**为什么自动化测试天然测不到**。这一层在既有条目里没有，构成新增适用面。
- `.kv` 侧提供 `prescan_pattern`/`prescan_globs`，可被工具自动预扫描这类"恢复前二次读取"的写法。
