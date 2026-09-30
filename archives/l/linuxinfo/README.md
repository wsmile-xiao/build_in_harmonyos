# linuxinfo — 系统信息一行打印工具

## 软件简介

linuxinfo 是一个很老的 Linux 命令行工具：读 `/proc/cpuinfo`、`/proc/meminfo`，
再配一次 `uname(2)`，把当前系统压成三行摘要打印出来。最初由 Alex Buell 编写，
2014 年起由 Debian 开发者 Helge Kreutzmann 接管维护并把历年攒下的 Debian 补丁并回上游。

它不做任何"探测硬件能力"的事，也不写任何东西 —— 纯只读、退出即结束，
因此在鸿蒙 PC 上等价于一次 `/proc` 可读性 + `uname` 语义的活体检查。

```
$ linuxinfo
HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026
Three ARM v7 instruction set 528MHz processors, 2001.00 total bogomips, 29xxxM RAM
System library 2.38
```

**命令行**（`linuxinfo.c: main()` 逐字核对）:
- 无参: 打开 `/proc/cpuinfo` 并打印三行摘要；打不开则 `return -2`
- `-v`: 打印 `<argv[0]> <VERSION>`（VERSION 由 configure 的 `DEFS` 注入）
- `-h`: 打印版本号 + 两行用法
- `<文件路径>`: 把该文件当 cpuinfo 解析 —— 本包唯一可喂确定性输入的入口

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 4.2.3 | pending-build ⏸（骨架已入库，未跑构建） | — | 2 |

## 货源

- 官网：`https://www.helgefjell.de/linuxinfo.php`（https 形态实测 3 次均 200 / 4701 B）

官方发布在维护者自己站点的 `data/` 目录下，由其下载页
`http://www.helgefjell.de/linuxinfoitem.php?name=download` 直接列出：

- `https://www.helgefjell.de/data/linuxinfo/linuxinfo-4.2.3.tar.xz`
  （sha256 `003123eebb097fd8e12a299bd4ea8b9ed6988311b2412df132b148f3ca9a705a`，169860 B）
- 同目录有配套 PGP detached 签名 `...tar.xz.sig`
- 上游**没有** GitHub/GitLab 官方托管；旧域名 `www.munted.org.uk` 包内 README 自述"no longer active"
- Debian 池址仅用于交叉核验哈希（`.orig.tar.xz` 与官方件逐字节同值），**不作为配方货源**

## 平台适配要点（跨版本通用）

| # | 要点 | 归属知识 |
|---|------|----------|
| 1 | `configure` 生成的 `config.status` 用 `umask 077` 建临时目录，HMDFS 上该目录属主不可写 → `subs1.awk: Permission denied` | E011 / E114 / E118 |
| 2 | `config.guess` 认不出 `uname -s = HarmonyOS`，但 `config.sub` 认 `ohos` 后缀 → 显式喂 `--build/--host`，不改生成文件 | E007 家族（本包不需补丁） |
| 3 | `GetSystemLibcInfo()` 无保护地三选一 `.weak` glibc 符号，musl 上一个都不导出 → 读地址 0 崩溃 | E047（HMDFS/libc 语义族） |
| 4 | `pcre2`（仅 `--with-pcre`，x86 专用）与 `po4a`（仅翻译 man，官方件已自带成品）都**不是**依赖 → 零 `requires()` | — |
| 5 | 单二进制 CLI，`package_type=application`，需软件级 `commands.json` | R38 |

## 依赖

无。
