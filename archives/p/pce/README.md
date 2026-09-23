# PCE

PCE 是 Hampa Hug 维护的微机模拟器合集，包含 IBM PC 5150、Macintosh Plus、RC759 Piccoline 及 6502/ARM/SPARC/PPC405 等模拟器。

## 功能概述

- `pce-ibmpc`：IBM PC 5150/XT 仿真（含 Olivetti M24 支持）
- `pce-macplus`：Macintosh Plus/128K/512K/SE/Classic 仿真
- `pce-rc759`：RC759 Piccoline 仿真
- `pce-sim405` / `pce-sim6502` / `pce-simarm` / `pce-sims32`：CPU/系统模拟器
- 配置文件、ROM 扩展与磁盘工具随源码发布

## OHOS 适配

- 构建系统为 Autotools，采用原生构建（build 与 host 均为 aarch64）。
- 为适配无显示/声卡的 HarmonyOS 环境，关闭 X11、SDL、readline、tun 与 OSS，仅保留 null/stdio 终端。
- 2013 版 `config.sub` 已识别 aarch64，OHOS 下使用标准 `aarch64-unknown-linux-gnu` triplet，无需补丁。
- `e68000` CPU 内核需 `-fcommon` 才能在 clang 15 下链接。
- 上游无测试套件；消费者测试对 7 个二进制做 `-V` / `--help` 冒烟验证。

## 依赖关系

- 编译依赖：无（仅需系统 clang/make）。
- ROM 构建可选依赖 NASM，本配方保持默认关闭，不引入依赖。
- 运行依赖：无；启动仿真仍需用户自备 ROM/磁盘镜像。

## 参考

- 官网：http://www.hampa.ch/pce/
- 下载页：http://www.hampa.ch/pce/download.html
- 源码：http://www.hampa.ch/pub/pce/pce-0.2.2.tar.gz
- 镜像：https://cdn.netbsd.org/pub/pkgsrc/distfiles/pce-0.2.2.tar.gz
