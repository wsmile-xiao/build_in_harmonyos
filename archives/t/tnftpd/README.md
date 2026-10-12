# tnftpd 20231001 — HarmonyOS PC 适配说明

## 概况

`tnftpd` 是 NetBSD 官方 FTP 服务端守护进程 `ftpd` 移植到其他系统的版本
（前身 `lukemftpd`），设计为在 inetd 下运行，stdio 即 FTP 控制连接。

- 上游：https://www.NetBSD.org/ （官方 autoconf tarball）
- 形态：autotools（官方 release 包自带生成的 `configure`，无需 autoreconf）
- 产物：`bin/tnftpd` 守护进程 + man 页 + examples 配置
- 依赖：bison/3.8.2（tool_require，生成 `ftpcmd.c`）；运行时仅 libc/libc++
- 许可证：BSD-2-Clause（NetBSD 风格，COPYING）

## 功能概述

- 标准 FTP 服务端（RFC 兼容），供 inetd/xinetd 或 `-D` 独立模式调用
- IPv6 支持（KAME 移植）
- `ftpusers` 登录控制与用户/组 class 关联
- `ftpd.conf` 按 class 的细粒度配置（PASV 地址、chroot、传输速率限制等）
- 内建 `ls(1)`（--enable-builtinls）实现 LIST，无需 ftp 树内有 /bin/ls
- 可选 PAM / S/Key / NetBSD blocklist 认证（本项目显式禁用）

## OHOS 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `configure` 因 LT_INIT 必跑 `config.guess`（2018-03-08），不识别 `uname -s=HarmonyOS`，起手 "cannot guess build type" | 补丁 0001 加 HarmonyOS 分支输出 `aarch64-unknown-linux-ohos`（radvd 同款） |
| 2 | `config.sub`（2018-05-05）OS 白名单不含 ohos，判 Invalid configuration | 补丁 0002 补 `linux-ohos*` / `-linux-ohos*`（native 编译，R1 不传 --build/--host/--target） |
| 3 | autoconf 的 `configure` 用 `umask 077 && mktemp -d` 建暂存目录，HMDFS setgid 目录下 `drwx--S---` 不可写（E011/E112/E114） | 补丁 0003 两处 `umask 077` → `022` |
| 4 | `ftpcmd.c` 由 `ftpcmd.y` 现场生成，release 包不含 | `tool_requires("bison/3.8.2")` |
| 5 | 并行 make 触发 HMDFS jobserver fifo EPERM（E074） | `make -j1` |
| 6 | 可选认证（PAM/S/Key/blocklist）OHOS 未发布 | `--without-*` 显式禁用，走 Unix passwd 认证 |
| 7 | `libexec_PROGRAMS` 默认装 `$prefix/libexec` | `package()` 中重命名到 `$prefix/bin`，便于 PATH 与消费者测试 |

## 测试情况

**上游无测试套件**（逐文件审计：无 test/、TESTS、check 目标、gtest 绑定），
不跑 `make check`。消费者测试（`test_package/`）真实调用被适配的
`tnftpd` 二进制：存在性/可执行/ELF 校验 + `-C <user>` 访问检查自终止验证
（守护进程无需起端口，离线确定性断言）。

## 依赖关系

- 编译期：bison/3.8.2（tool_require）
- 运行期：仅系统 libc/libc++，无 conan 依赖

## 参考资料

- 官方源码：https://cdn.netbsd.org/pub/NetBSD/misc/tnftp/tnftpd-20231001.tar.gz
- 主页：https://www.NetBSD.org/
