# reptyr

reptyr 是一个把**正在运行的进程重挂到新终端**的小工具：当你在一个终端里启动了长任务
（编辑器、编译、会话），想关掉该终端又不中断任务时，`reptyr <PID>` 可以把目标进程
"偷"到当前终端继续使用。核心机制是 ptrace(2)：附加目标进程 → 保存/恢复寄存器与内存映射 →
在新 pty 上重建控制终端（TIOCSCTTY/TIOCSPGRP、fd 重定向、终端状态与窗口大小复制）。

## 功能概述

- `reptyr PID` — 把进程重挂到当前（新）pty
- `reptyr -T PID` — 夺取目标整个终端会话（实验特性；连带该终端所有进程）
- `reptyr -s PID` — 目标未连接终端时也强制附加 fd 0-2
- `reptyr -l` / `-L [CMD]` — 仅新建 pty 对并播报 slave（`-L` 令子命令 stdio 接到 slave，
  导出 `REPTYR_PTY`）；该模式不使用 ptrace
- 安装：`bin/reptyr`、英文/法文 man（`man reptyr`）、bash 补全

## OHOS 适配（aarch64，HarmonyOS PC）

- 构建系统为手写 Makefile；适配补丁 2 个（见 `0.10.0/conandata.yml`）：
  1. **平台后端选择**：Makefile 以 `uname -s` 匹配 `Linux`，OHOS 返回 `HarmonyOS`
     导致 linux 后端目标缺失、链接失败 → 令 `HarmonyOS` 与 `Linux` 同分支（E007 家族，
     手写 Makefile 变体；纯平台识别，无平台宏）。
  2. **sockaddr_storage 重定义**：`<linux/net.h>` → `<linux/socket.h>` 与 `<sys/socket.h>`
     在 musl 系系统上重复定义该结构（`-Werror` 下直接失败）→ 包含 linux 头文件期间
     以 `#if defined(__linux__) && !defined(__GLIBC__)` 守卫改名（E091 同类处置）。
- 上游 `install` 目标依赖 `install(1)`（OHOS 无此命令），安装改由 conan `package()` 完成。
- **平台能力边界（重要）**：OHOS 内核对非特权进程禁用 ptrace——同一 SSH 会话内
  `PTRACE_ATTACH`/`SEIZE`（父子、祖孙）、`PTRACE_TRACEME`、`process_vm_readv` 全部返回
  `EPERM`（进程处于 seccomp filter 模式且无 `CAP_SYS_PTRACE`），`PR_SET_PTRACER` 返回
  `EINVAL`。因此 `reptyr PID` / `-T` / `-s` 的核心附加功能在该平台被系统策略阻断（补丁无法绕过）；
  `-l` / `-L` 的 pty 管理功能正常。复现探针与证据见 `0.10.0/reports/ptrace-capability-probe.txt`。
- 上游测试 2 用例（basic.py / tty-steal.py，pexpect）在该边界失败（0/2，非适配缺陷，已如实申报）；
  消费侧回归由 `test_package/test_reptyr.sh` 的 18 条断言覆盖。

## 依赖关系

- 编译依赖：无（仅系统 libc；W0 检查 `requires` 为空）
- 运行依赖：无

## 参考资料

- 上游仓库：<https://github.com/nelhage/reptyr>
- 源码归档：<https://codeload.github.com/nelhage/reptyr/tar.gz/refs/tags/reptyr-0.10.0>（GitHub 官方 tarball 端点）
- 许可：MIT
