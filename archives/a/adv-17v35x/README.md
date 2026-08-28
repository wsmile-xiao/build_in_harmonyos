# adv-17v35x — 研华 PCIe 多串口驱动（用户态工具）

Advantech ACOM 系列（EXAR 芯片组）PCI/PCIe 多串口卡 Linux 驱动
（上游版本 5.0.7.0，Debian 源包 adv-17v35x 5.0.7.0-1）。

## 本归档内容

上游源码含两层构建入口：

1. **Linux 内核驱动模块**（`adv17v35x.c` + 顶层 `Makefile`，需内核头文件树）：鸿蒙 PC
   无内核构建环境，无法构建，本归档不包含该部分产物。
2. **用户态工具 getconfig**（`getconfig/getconfig.c`）：纯 C 工具，查询串口
   RS232/RS422/RS485 模式。本归档按 application 包交付 `bin/getconfig`。

## 构建与使用

- 构建系统：makefile（`cd getconfig && make CC=<clang>`），OHOS clang 交叉编译。
- 安装产物：`bin/getconfig`。
- 运行：`getconfig TTYNAME TTYNUM`（无参数时打印 Usage 并退出 1）。

## 许可证

GPL-2.0-or-later（源码文件头声明 GPL v2 或更高版本）。

## 链接

- 上游 Debian 打包仓库：https://salsa.debian.org/debian/adv-17v35x
- 源码 orig tarball（Debian pool）：https://deb.debian.org/debian/pool/main/a/adv-17v35x/