# ticker

Ticker 是一个可配置的文本滚动器：把一条消息在屏幕顶行或底行滚动显示（类似股票报价机效果）。它支持通过 SysV 共享内存与外部程序通信，由外部程序周期性更换显示文本，因此可实现真正的股票报价板等场景。

## 功能概述

- `-u`/`-l`：选择在屏幕顶行或底行滚动。
- `-f`/`-b`：前景/背景色；`-d`：滚动延迟（秒，可小数）；`-s`/`-S`/`-c`：SysV 共享内存段读取。
- `+`/`-`/方向键调速，空格暂停。
- 自带 `sysinfo-ticker`（perl 示例：把 `uptime` 经共享内存送给 ticker 显示）。

## OHOS 适配

- 适配版本：1.16（Debian native 包，Debian QA Group 维护；作者 Joey Hess 原站 https://joeyh.name/code/ticker/）。
- 构建：2002 年手写 `configure` + 手写 `Makefile`，必须源码内构建；编译器与 S-Lang 标志来自 Conan 工具链环境。
- 依赖：唯一第三方依赖 `slang/2.3.3`（S-Lang 终端库，仓内已适配）。
- 已知限制：滚动主循环需要真实终端，headless 运行器（CI/真机预检）只自动化 `-h`/`--help`/参数错误路径与产物属性检查；交互滚动以 Debian autopkgtest 同口径为准。
- 与 Linux 的差异：OHOS 交叉编译（aarch64），动态链接 conan 提供的 `libslang`。

## 依赖关系

- 编译依赖：`slang/2.3.3`（精确引用）。
- 运行依赖：同上（`bin/ticker` NEEDED `libslang`，随 conanrun 环境解析）。

## 参考资料

- 作者页：https://joeyh.name/code/ticker/
- Debian 源码：https://salsa.debian.org/debian/ticker.git（Vcs-Git）
- 本版归档：`archives/t/ticker/1.16/`（配方、测试、笔记）
