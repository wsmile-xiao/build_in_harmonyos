# bsdgames-nonfree

## 简介
bsd-games-non-free 2.17 是 NetBSD 经典 roguelike 游戏 **rogue** 的 Linux/OHOS 移植版。
rogue 为交互式终端地牢探险游戏（curses 界面）。

## 许可说明
rogue 主体许可为 BSD-3-Clause（上游 COPYING 声明），但含附加条款限制
商业盈利分发（README.non-free 说明），因此历史上归入 non-free 包分类。
conanfile.py/manifest.yaml 的 license 字段按主体许可填 BSD-3-Clause。

## 主要功能
- 交互式 roguelike 地牢探险
- curses 终端界面（ncursesw）
- 高分榜（scorefile）记录

## OHOS 适配
- 构建系统：自定义交互式 configure 脚本 + make
- 目标架构：aarch64-linux-ohos
- 依赖：ncurses（静态链接，conan 包 ncurses/6.4）

## 依赖
- ncurses/6.4

## 功能验证
```bash
printf "tester\nquit\ny\n" | rogue   # 输出 "Hey!  Who are you?" 启动横幅
```

## 参考
- 上游：https://www.ibiblio.org/pub/Linux/games/bsd-games-non-free-2.17.tar.gz
- README.non-free：https://www.ibiblio.org/pub/Linux/games/
