# sockstat

打开套接字（open socket）明细查看器 —— FreeBSD `sockstat(1)` 的 Linux 实现。

## 是什么

`sockstat` 读取 `/proc/net/{tcp,udp,raw,tcp6,udp6,raw6,unix}` 的套接字表，
取出每条记录的 inode，再遍历 `/proc/<pid>/fd` 用 `stat()` 找到 inode 匹配的
socket fd，从而为**每个打开的套接字**打印一行：

```
USER     PROCESS              PID      PROTO  SOURCE ADDRESS            FOREIGN ADDRESS           STATE
root     systemd              1        unix   /run/systemd/journal/stdout
systemd- systemd-resolve      191      tcp4   127.0.0.53:53             *:*                       LISTEN
```

相比只列监听端口的 `netstat -t`，`sockstat` 给出的是**进程视角**的完整
socket 清单（含 unix domain socket），并支持按 PID / 用户 / 端口 / 协议过滤。

## 快速上手

```bash
sockstat              # 全部打开的套接字
sockstat -4           # 仅 IPv4
sockstat -6           # 仅 IPv6
sockstat -u           # 仅 unix domain socket
sockstat -l           # 仅监听态
sockstat -c           # 仅已连接
sockstat -R tcp       # 仅 TCP 族（udp / raw / unix 同）
sockstat -p 0-1023    # 仅本地或对端端口落在该区间
sockstat -P 1234      # 仅指定 PID
sockstat -U root      # 仅指定用户（支持用户名或 uid）
sockstat -o           # 旧行为：多个搜索条件以 | 组合（0.4.1 起默认改为 &）
sockstat -h           # 用法
```

> ⚠️ `-G <组>` 在上游 0.4.2 上**必然段错误**（`grp->gr_mem` 的 NULL 终止项被
> 解引用后传给 `getpwnam()`），普通 Linux 同样复现，属上游缺陷。
> 详见 `0.4.2/notes.md`。请勿依赖该选项。

> ⚠️ 上游**没有** `--version` 选项：`#define VERSION "0.4.2"` 从未被引用，
> `getopt` 选项串也不含 `v`/`V`。

## HarmonyOS PC 适配说明

- 交叉编译目标 `aarch64-linux-ohos`，产物 ELF64 PIE，`NEEDED` 仅 `libc.so`
- **零补丁**：上游源码对 OHOS musl sysroot 干净编译（`<err.h>`、
  `inet_lnaof()` 等 BSD 扩展在 sysroot 中均可用）
- ELF 需 `sign-elf` 签名后才能在鸿蒙设备执行（平台常规，CI `sign.sh` 处理）
- **沙箱限制**：OHOS 普通 uid 下 `/proc/net` 目录可列举但**文件内容不可读**
  （12/12 EACCES），因此"读表"类调用会以
  `can not open file /proc/net/<file>` + `SIGABRT`（rc=134）结束。
  这是平台权限模型差异（Linux 上同一代码读得通），非适配缺陷；
  参数解析路径（`-h` 等）不受影响。

## 版本

| Conan 引用 | 上游版本 | 说明 |
|---|---|---|
| `sockstat/0.4.2` | 0.4.2 | 首次适配 HarmonyOS PC（2026-10-02） |

## 上游

- 仓库：<https://codeberg.org/alteholz/sockstat>
- 许可：BSD-3-Clause（Copyright 2002 Dag-Erling Smørgrav / 2008 William Pitcock / 2018-2025 Thorsten Alteholz）
