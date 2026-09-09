# bsd-games

bsd-games 3.3 — 经典 BSD 文本终端游戏合集，包含 18 个来自 UNIX 传统的
文本模式游戏：

adventure / arithmetic / atc / battlestar / caesar / cribbage / dab /
drop4 / gofish / gomoku / hangman / klondike / robots / sail / snake /
spirhunt / worm / wump

- 上游: https://bsd-games.sourceforge.io/
- 许可证: BSD-3-Clause
- 构建系统: autotools（手写 configure + make）
- 依赖: ncurses（终端 UI）

## 适配说明

- OHOS 无 `users` 组：`Config.mk.in` 的 `INSTALL_SCORE` 去掉 `-g users`
- conan ncurses 包仅提供 `ncursesw.pc`：配方在 build_folder 内别名
  `ncurses.pc` 供 configure 的 pkg-config 探测
- 产物：18 个游戏可执行文件 + man 手册 + score 文件（纯应用包）

## 测试

- 上游无测试（源码包无 tests/，Makefile 无 test/check 目标；
  Alpine aports APKBUILD 官方标注 `options="!check" # no tests`）
- test_package 自研 21 项断言：18 个二进制存在性 + caesar rot13 功能
  断言（默认/显式偏移）+ wump -h 用法输出
