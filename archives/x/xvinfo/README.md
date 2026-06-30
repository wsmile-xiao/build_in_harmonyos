# xvinfo

xvinfo 是 X Video 扩展适配器信息查询工具，用于打印 X-Video extension adaptor 的详细信息。

## 功能概述

- 查询 X 服务器的视频扩展适配器信息
- 显示适配器类型、端口数量、图像格式等

## OHOS 适配

- **构建系统**: autotools
- **关键补丁**: config.guess/config.sub E007适配、configure mktemp权限修复
- **需手动编译 libXv**: cmd-pkgs 无预编译包

## 运行依赖

- X 服务器（查询需要运行 X 服务）

## 参考资料

- 源码: https://gitlab.freedesktop.org/xorg/app/xvinfo
- 版本: 1.1.5
