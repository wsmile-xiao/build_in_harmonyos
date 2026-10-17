# ltunify

ltunify 是 Logitech「Unifying」优联接收器的命令行配对 / 查询工具，C 语言编写，零第三方依赖（仅需 libc）。

- **官网**: https://lekensteyn.nl/logitech-unifying.html
- **上游源码**: https://deb.debian.org/debian/pool/main/l/ltunify/ （Debian 主仓库 orig tarball）
- **许可证**: GPL-3.0-or-later（见 ltunify.c / hidraw.c / read-dev-usbmon.c 头部声明；tarball 未附 LICENSE 正文）
- **分类**: 硬件 / 外设配对工具

## 软件描述

ltunify 直接读写 `/dev/hidraw*` 上的 HID++ 报文，完成接收器与键鼠的配对管理：

- `list` — 列出接收器上已配对的设备
- `pair [timeout]` / `unpair <index>` — 配对 / 解除配对
- `info` — 设备名称与型号
- `name <index> <name>` — 设置设备名（HID++ 2.0）
- 附带 `read-dev-usbmon`，解析 `/dev/usbmonX` 抓包数据（开发调试用）

## 适配说明

- **构建系统**: 上游单个裸 Makefile，无 configure 脚本，编译期零依赖
- **编译方式**: `make -C <src> CC=<conan 编译器> PACKAGE_VERSION=0.3 -j1`
- **安装方式**: **不走 `make install`** —— 构建环境的 `PATH` 不含 `/bin`，`make`/`sh` 因此查找不到 `install`（实测 `/bin/install` 存在且可执行，`--version` 报 `toybox 0.8.12`；把 `/bin` 前置进 PATH 后 `command -v install` 立即可解析），且上游把 `install` 写成字面量（无 `INSTALL` 变量可覆写），故配方内直接复制 + 补 0755 执行位
- **随包数据**: udev 规则作为 `res/udev/rules.d/` 资源分发，配方不写 `/etc`
- **测试**: 上游无测试体系；test_package 覆盖命令行面 7 条断言，硬件 I/O 面因无接收器硬件未覆盖（详见 `0.3/notes.md`）

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 0.3 | built | 2026-09-25 | 首适配，命令行面 7/7 断言通过；硬件 I/O 面未覆盖 |
