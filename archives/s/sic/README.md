# sic

> suckless 的**极简 IRC 客户端**：约 250 行 C，从标准输入读命令，把所有频道
> 流量多路复用到标准输出。

## 简介

`sic` 是一个极快、极小、极简的 IRC 客户端。它从标准输入读取命令，把服务器
输出全部打印到标准输出；它还会把所有频道流量多路复用到同一路输出，因此不必
切换不同的频道缓冲。

## OHOS 适配要点

- 单源文件 `sic.c`（内部 `#include` 随包的 `strlcpy.c` 与 `util.c`），无三方依赖。
- 用上游 `Makefile` 构建，在 make 命令行注入 OHOS 工具链的 clang；
  `config.h` 由 Makefile 从 `config.def.h` 生成。
- 上游无测试；配方在 `test_package` 中补全消费者测试：真跑安装后的二进制，
  并与本地 TCP 服务器完成一次 IRC 注册握手（`NICK`/`USER` + `PING`/`PONG`）。
- 产物是 CLI 工具，安装 `bin/sic` + `share/man/man1/sic.1`，并提供软件级
  `commands.json`。

## 依赖

无。

## 使用

```sh
# 连接默认服务器（irc.oftc.net:6667）
sic

# 指定服务器、端口与昵称
sic -h irc.libera.chat -p 6697 -n mynick

# 查看版本
sic -v
```

## 参考

- [sic 官方页面](https://tools.suckless.org/sic/)
- [源码仓库](https://git.suckless.org/sic)
