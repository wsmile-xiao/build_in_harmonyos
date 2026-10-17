# rephrase

`rephrase` 是一个**口令（passphrase）变体恢复工具**：当你还记得口令的大部分内容、只对个别片段拿不准时，用它把"你写的模式"展开成所有可能组合，逐个喂给真正的校验方去试，并告诉你是哪一种组合命中了。它不猜字典，只穷举**你自己给出的**候选写法，因此组合数可控。

上游 [roguedaemon.net/rephrase](https://www.roguedaemon.net/rephrase/)（作者 Phil Lanch，GPL-3.0-only，最后更新 2014 年 0.2 版）。

## 功能概述

- `rephrase <key>` — 对 GnuPG 私钥做恢复（等价于 `--gpg-key`）
- `rephrase --gpg-key <key>` — 用 `gpg --default-key <key> --passphrase-fd 0 --batch --no-tty --dry-run --clearsign /dev/null` 校验候选口令
- `rephrase --gpg-symmetric <encrypted_file>` — 对 GnuPG 对称加密文件校验
- `rephrase --luks <block_device>` — 用 `cryptsetup --test-passphrase --key-file /dev/fd/0 open --type luks <device>` 校验 LUKS 口令

模式语法：`(...) | (...)` 表示候选分支，`\` 转义，字面量按位展开成笛卡尔积后逐一尝试。

口令从 `/dev/tty` 直接读取并临时关闭回显（`tcgetattr` / `tcsetattr`），不经过 stdin，因此不会与传给子进程的口令管道冲突；候选口令通过匿名管道以 `--passphrase-fd 0` 交给子进程。

## 依赖关系

- 编译依赖：**无**。上游只有一个 `rephrase.c`，`Makefile` 里没有任何 `LDLIBS` / `LIBS` / `LDFLAGS` 行，只用 libc（`termios`、`mlock(2)`、`fork`/`execv`/`waitpid`、`stat`）。
- 运行依赖：**`gpg` 与 `cryptsetup`**。二者路径在编译期作为宏烧进二进制（默认 `GPG=/usr/local/bin/gpg`、`CRYPTSETUP=/sbin/cryptsetup`，可用 `make GPG=... CRYPTSETUP=...` 覆盖）。rephrase 自身不做任何密码学，只负责"组织候选口令 + 起子进程 + 看退出码"。
- 运行环境：需要一个**控制终端**（`read_pattern()` 以 `fopen("/dev/tty", "r+")` 读口令模式）；`--luks` 还需要真实块设备。

## OHOS 适配要点

- 上游构建与安装规则有两处必须偏离：**`make install` 必须以 root 运行**，且 `install-sh -c -o 0 -g 0 -m 4711` 会把产物装成 **setuid root**（`binmode = 4711`）。本配方不调用 `install` 目标，改由 `package()` 直接 `copy` 出 `bin/rephrase` 并 `chmod 0755`。
- 上游之所以要 setuid root，是因为 `main()` 第一件事就是 `mlock(&sec, sizeof sec)`，失败即 `exit(2)` 并提示 "rephrase should be installed setuid root"。实测 **HarmonyOS PC 上 `RLIMIT_MEMLOCK` 为 unlimited**，普通用户态 `mlock(2)` 直接成功 ⇒ **0755 无 setuid 安装不损失任何功能**，`exit(2)` 分支不会触发（探针见 `0.2/notes.md`）。
- `prefix = /usr/local` 只是普通 `=` 赋值（非 `?=`），命令行 `make prefix=...` 可覆盖，`install` 目标也支持 `$(DESTDIR)`——上游并没有把前缀"烧死"，只是本配方不使用该安装路径。
- 构建只需注入 `CC`（OHOS SDK clang，R33）。`Makefile` 自带 `DEFS = -DVERSION="$(version)"` 并 `CPPFLAGS += $(DEFS)`，而 `rephrase.c` 在缺少 `VERSION` 时 `#error` ⇒ 配方**不得**覆写 `CPPFLAGS`/`CFLAGS`，只覆写 `CC`。
- 符号面与 syscall 面**各需一处可移植性补丁**（实测，非预判）：OHOS libc（musl 系裁剪）**未导出** `rindex`（`index` 在）⇒ 0001 换成逐字等价的 `strrchr`；鸿蒙内核对 `setreuid()`/`setregid()` 判不可捕获的 SIGSYS(exit 159) ⇒ 0002 无条件换成放行的 `setuid(getuid())`/`setgid(getgid())`（补丁内不用平台宏，R8/PF5）。
  `tcgetattr`/`tcsetattr`/`mlock` 实测可用无需补丁；本包**不使用** `openpty`/`forkpty`/`grantpt`/`unlockpt`/`ptsname`，因此不存在 glibc `libutil`（`-lutil`）移植问题。
- 功能面限制（如实申报，见 `0.2/notes.md` 的未执行清单）：OHOS PC 未提供 `gpg` 与 `cryptsetup`，且批处理环境无控制终端 ⇒ "读模式 + 穷举试口令"的**主流程未执行**；已确定性执行的是五条消费者断言（参数解析、`-DVERSION` 烘焙、usage 文本、编译期子程序路径守卫、无 setuid 下的 mlock 门禁）。

## 参考资料

- 项目主页与手册页：<https://www.roguedaemon.net/rephrase/>
- 上游原始归档（配方取源处）：`https://www.roguedaemon.net/rephrase/rephrase-0.2.tar.gz` —— 上游作者官方站，实测 HTTP 200 / 25587 B / `sha256=54d5bb9f3d7a0e179af1a4569d1ad67a90037ab501380da096ec0eb1fcd473bf`；Debian pool 同名件已逐字核对为同一 sha256，仅留旁证（R39/PF7：conandata 只写上游官方源）
- Debian 源码包页：<https://packages.debian.org/source/sid/rephrase>
