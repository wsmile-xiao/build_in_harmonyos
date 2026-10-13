# proot

proot 是一个**用户态的 chroot / mount --bind / binfmt_misc** 实现：不需要任何特权
也不需要内核支持，就能把一组目录"绑定"成一个看起来像独立 Linux 发行版的根文件系统
（guest rootfs），并在其中执行任意程序。核心机制是 ptrace(2)：proot 跟踪 guest 进程的
每一次系统调用，在用户态重写路径、模拟 chroot/绑定、伪造 uid/gid（`-0`）等。

## 功能概述

- `proot -r ROOTFS CMD...` — 以 ROOTFS 为根文件系统执行命令
- `-b HOST:GUEST` / `-m` — 把宿主路径绑定进 guest（可重复）
- `-R` / `-S` — 推荐组合（自动绑定 /etc、/dev、/proc、$HOME 等；`-S` 附带 `-0`）
- `-0` / `-i uid:gid` — 伪造 root / 指定用户身份（fakeroot 式）
- `-w path` — 指定 guest 工作目录；`-q qemu` — 经 QEMU 执行 guest 程序（binfmt 式）
- `--kill-on-exit`、`-v N`、`-l`（link2symlink）、`-p`（端口映射）、`-n`（netcoop）等扩展
- `-V/--version`、`-h/--help` — 版本与用法

## OHOS 适配（aarch64，HarmonyOS PC）

- 构建系统为手写 GNUmakefile；proot 依赖 `talloc`（本仓已有 `talloc/2.4.4`）与
  源码内自带的 uthash（CARE 工具未构建）。适配补丁 4 个（见 `5.4.0/conandata.yml`）：
  1. **CIRCLEQ 家族缺失**：OHOS C 库的 `<sys/queue.h>` 是 FreeBSD 衍生版，已移除
     CIRCLEQ_*（FreeBSD 2018 年删除）；proot 的绑定链表依赖它 → 在 `#ifndef CIRCLEQ_HEAD`
     守卫下补上标准定义（纯特性检测，无平台宏）。
  2. **`get_current_dir_name()` 缺失**：GNU 扩展，OHOS C 库不提供 → 改用上游
     `__ANDROID__` 分支同款的可移植 `getcwd()` 写法。
  3. **`sockaddr_storage` 双重定义**：`<linux/net.h>` 经 `<linux/socket.h>` 定义内核侧
     同名结构，与 musl 系 `<sys/socket.h>` 冲突 → 包含 UAPI 头期间重命名内核侧结构
     （knowledge E091 同类处置）。
  4. **上游测试支持**：`test/ptrace-2.c` 使用 glibc 专属的 `enum __ptrace_request`
     → 无该类型时回退为 `int`（Alpine Linux 对同一测试的相同修法）。
- 上游 `make install` 依赖 `install(1)`（OHOS 无此命令），安装改由 conan `package()` 完成。
- 版本号通过 `VERSION=5.4.0` 显式传入（上游从 `git describe` 推导，tarball 无 .git；
  Alpine 亦如此处理）。
- **平台能力边界（重要）**：OHOS 内核对非特权进程禁用 ptrace(2)——proot 的每一次
  tracee 执行都会在 `ptrace(TRACEME)` 处被拒绝（"Permission denied"），这是内核策略，
  任何用户态补丁都无法绕过。因此本平台上 proot 的**隔离执行功能不可用**；CLI 表面
  （版本/帮助/参数校验）完整可用，上游测试套件的结果与证据见
  `5.4.0/reports/test-report.md`，消费侧回归由 `test_package/test_proot.sh` 的 16 条断言覆盖。

## 依赖关系

- 编译依赖：`talloc/2.4.4`（Conan 制品仓）；uthash 随源码内置
- 运行依赖：无（动态链接 OHOS libc）

## 参考资料

- 上游仓库：<https://github.com/proot-me/proot>
- 源码归档：<https://codeload.github.com/proot-me/proot/tar.gz/refs/tags/v5.4.0>（GitHub 官方 tarball 端点）
- 许可：GPL-2.0-or-later
