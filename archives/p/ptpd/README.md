# ptpd

> IEEE 1588 精密时间协议（PTP）守护进程 `ptpd2`，可作主时钟（master）、从时钟（slave）
> 或混合模式（hybrid），支持软件/硬件时间戳与 libpcap 抓包后端。

## 简介

ptpd 2.3.1 用 C 写成，构建系统为 autotools（上游发布包含**已生成**的 `configure`）。
产物是单个守护进程 `ptpd2`（安装到 `bin/`）以及 man 手册。它通过
`SO_TIMESTAMPING`（或回退到 `SO_TIMESTAMP`/`ioctl`）获取收发报文时间戳，并用
`adjtimex()` 校准系统时钟。

## OHOS 适配要点

- 直接运行上游随包的 `configure`，不 regenerate；显式传
  `--build/--host=aarch64-unknown-linux-gnu`，避免 `config.guess` 无法识别 bionic。
- 可写 HomeArea（HMDFS）不按 `umask 077` 生效，`configure` 的 `config.status` 会失败 →
  在 `build()` 里改为 `umask 022`。
- bionic 有 `<utmpx.h>` 但缺 `setutxent()/pututxline()/endutxent()` →
  `ac_cv_header_utmpx_h=no`（并关闭经典 utmp 路径）。
- bionic 缺 `ether_ntohost()`（但有 `ether_aton()/ether_ntoa()`）→ 补丁降级为数字 MAC。
- `<linux/socket.h>` 与 `<sys/socket.h>` 的 `sockaddr_storage` 重定义 → 补丁预定义
  `_UAPI_LINUX_SOCKET_H`。
- 关闭 SNMP（制品仓无 net-snmp）；libpcap 可选。

## 平台能力说明

OHOS 上 `SO_TIMESTAMPING` 套接字选项可被内核接受，但**没有** `/dev/ptp0`
（PTP 硬件时钟），且 `adjtimex()` 被 seccomp 拦截并触发 SIGSYS（signal 31）。
因此 ptpd 在 OHOS 上可用于构建、启动、观察/监控，但无法校准系统时钟；
需要时钟驯服时请使用 `-n` / `clock:no_adjust=Y` 之类的“只观测”配置。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| libpcap | 1.10.6 | 可选，`-o ptpd/*:pcap=True`（默认）时启用抓包后端 |

## 构建与验证

```sh
conan create archives/p/ptpd/2.3.1-debian1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 参考

- [上游项目](https://sourceforge.net/projects/ptpd/)
- [Debian 源包](https://sources.debian.org/src/ptpd/2.3.1-debian1-6/)
