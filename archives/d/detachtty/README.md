# detachtty

detachtty lets you run interactive programs non-interactively, and connect
to them over the network when you do need to interact with them. It has two
parts: `detachtty` (server, opens a pseudoterminal and serves a
unix-domain socket) and `attachtty` (client, attaches to the socket,
optionally over ssh).

## OHOS 适配要点

- 上游纯 Makefile（无 configure，无 test/check 目标）：`make -j1` 构建
  `detachtty` 与 `attachtty` 两个二进制。
- 编译器来自 Conan conf `tools.build:compiler_executables`（R33），不读
  shell 裸变量。
- `-lutil` 去除（仅 OHOS）：OHOS musl 把 forkpty/openpty 并入 libc，
  sysroot 仅保留空壳 `libutil.a`（E563）；Linux 保持上游默认 `-lutil`。
- 上游 `install` 规则无 strip 步骤，无需额外反剥离处理；产物直接装入
  包内 `bin/`。
- 上游无任何测试套件（见 test_package/MANIFEST.yml 审计），test_package
  以 `--version`、用法退出码与真实 socket 连接测试替代。

## 依赖关系

- 编译依赖：无（仅 libc 与 pty 接口）。
- 运行依赖：仅 libc；跨机连接时客户端需 `ssh`（可选，不声明为 Conan 依赖）。

## 参考资料

- 上游仓库：https://github.com/cosmos72/detachtty
- 源码包：https://github.com/cosmos72/detachtty/archive/11.0.0.tar.gz
- Debian 说明：detachtty lets you run interactive programs non-interactively
- 许可证：GPL-2.0-or-later（COPYING，detachtty.c 头部注明 GPLv2+）
