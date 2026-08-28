# adv-17v35x 5.0.7.0 适配笔记

## 上游身份

- 项目：Advantech ACOM 系列（EXAR 芯片组）PCI/PCIe 多串口卡 Linux 驱动
- 版本：5.0.7.0（上游 readme changelog 确认 `Version 5.0.7.0 <2020-12-30>`）
- 平台任务身份：adv-17v35x / 5.0.7.0（Issue #2396，分支 feat/adv-17v35x-5.0.7.0，目标 main）
- 归档身份：conan adv-17v35x/5.0.7.0（archives/a/adv-17v35x/5.0.7.0/）

三重身份名称与版本一致，无映射偏移。

## 源码与校验

- 源码 URL（Debian 官方 pool，权威镜像源，可复现）：
  `https://deb.debian.org/debian/pool/main/a/adv-17v35x/adv-17v35x_5.0.7.0.orig.tar.gz`
  该 tarball 即上游 Advantech 驱动源码 `adv_17V35X/` 的纯净 orig 版本（Debian 雪茄制包 5.0.7.0-1 之上游源）。
- SHA256：`a53ef1a8b5f1765367e3650fdea5631ee08323ecb3e358aef443b25ba4935dd7`
  已实际下载并以 `sha256sum` 核验一致；Debian pool 元数据（dsc）一致。
- 许可证：GPL-2.0-or-later（adv17v35x.c、getconfig.c 文件头均声明 GPL v2 或更高版本）。

## 构建入口与适配方案

上游源码有两层构建入口：

1. **Linux 内核驱动模块**：顶层 `Makefile` + `adv17v35x.c` + `precomp.h`，
   构建 `make -C $(KERNEL_SRC) M=$(PWD) modules` 需要内核头文件树
   （`/lib/modules/$(uname -r)/build`）。鸿蒙 PC 无内核构建环境，该部分无法构建，
   属于真实外部限制，本归档不伪造其构建。

2. **用户态工具 getconfig**：`getconfig/Makefile`（`gcc -O -o getconfig getconfig.c`），
   纯 C 工具，用于查询串口 RS232/RS422/RS485 模式。仅依赖标准 C 头 +
   `linux/serial.h` + `asm/ioctls.h`（OHOS sysroot `aarch64-linux-ohos/asm/ioctls.h` 与
   `linux/serial.h` 均已提供）。已用 `/data/service/hnp/bin/clang` 裸编译验证：
   无需显式 --sysroot，默认目标即为 aarch64-linux-ohos，产出 arm64 OHOS ELF。

方案：按 application 包交付用户态工具 getconfig（conan `package_type=application`，
安装 `bin/getconfig`），上游测试入口、真实运行行为与统计详见 manifest 与 PR 正文
（getconfig 无参数运行时打印 Usage 并退出 1；`getconfig ttyA 0` / `getconfig ttyB 0`
退出 0）。

## 与平台的偏差（如实说明）

- 上游包主体是 Linux 内核驱动模块，鸿蒙 PC 用户态无内核构建环境，仅适配交付
  用户态工具 getconfig；内核模块部分不构建、不安装，也未在配置中伪造。
- 未使用补丁；未修改上游源码。
---

**编译结束**: 2026-08-27 07:42
**最终状态**: built
