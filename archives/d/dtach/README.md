# dtach

dtach 是一个小型程序，模拟 screen 的 detach（脱离）功能，允许将程序脱离终端会话运行。

## 功能概述

- 将程序从终端会话脱离（detach），在后台继续运行
- 稍后可重新连接（attach）到已脱离的程序
- 与 screen 不同，dtach 不为每个脱离会话维护独立终端，而是将程序连接到启动时所在的终端
- 适用于需要在后台持续运行但又需要交互的程序

## OHOS 适配要点

- **HMDFS umask 077 问题**：configure/config.status 使用 `umask 077 && mktemp -d` 创建临时目录时，HMDFS 文件系统会拒绝写入（Permission denied），需要移除 `umask 077`
- **Makefile 缺少 install 目标**：原版 Makefile.in 不包含 install 目标，需添加带 DESTDIR 支持的 install target
- **无测试套件**：dtach 无 `make check` 目标，需通过手动验证确认功能

## 依赖关系

- **编译依赖**: 无外部依赖，仅需标准 C 编译器和 autotools
- **运行依赖**: 仅依赖 libc.so

## 参考资料

- 官网: https://dtach.sourceforge.net/
- 源码: https://downloads.sourceforge.net/project/dtach/dtach/0.9/dtach-0.9.tar.gz
- 许可证: GPL-2.0-or-later