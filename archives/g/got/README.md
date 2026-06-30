# got

OpenBSD 的游戏操作系统版本控制系统（Game of Trees）。

got 是一个用 C 语言编写的版本控制系统，设计目标是简单、安全、可移植。
它提供了 git 仓库的读写支持，但使用更简单的命令界面。

## 主要组件

- **got**: 主命令行工具
- **gotadmin**: 管理工具
- **gotctl**: 控制工具
- **gotsh**: SSH shell
- **gitwrapper**: git 命令包装器
- **tog**: 终端图形界面
- **gotd**: 服务器守护进程
- **gotwebd**: Web 界面守护进程

## 来源

- 官方网站: https://gameoftrees.org
- 源码: https://github.com/OpenBSD/got-portable

## 编译依赖

- libbsd
- libmd
- libcrypto (OpenSSL)
- libevent
- libuuid
- zlib
- ncurses (tog)
