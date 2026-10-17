# curseofwar 1.3.0 适配笔记

## 编译环境
- 构建系统: make（上游手写 Makefile，ncurses 前端；无 configure 脚本）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4（OHOS SDK sysroot, musl）
- 状态: published（conan-verify G1-G4/L2/L4/L5 全 PASS）

## 编译步骤

1. 上游源码: GitHub a-nikolaev/curseofwar tag v1.3.0（sha256 与 Debian orig.tar.gz 1.3.0-3 完全一致: `2a90204d95a9f29a0e5923f43e65188209dc8be9d9eb93576404e3f79b8a652b`）
2. conan 依赖: ncurses/6.6（制品仓已发布，宽字符静态库 libncursesw.a）
3. 构建: `make -j1 CC=clang CFLAGS="-O2 -Wall" CPPFLAGS="-I<ncurses>/include -DVERSION='\"1.3.0\"' -DINSTALL_DATA='\"<pkg>/res/curseofwar/\"'" LDFLAGS=... LDLIBS="-lncurses -lm"`
4. 安装: copy 二进制到 package_folder/bin + LICENSE/README/CHANGELOG

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 报 path.c `INSTALL_DATA` undeclared | 命令行覆盖 CPPFLAGS 后 Makefile 自带的 `-DINSTALL_DATA` 丢失 | CPPFLAGS 显式补回 `-DINSTALL_DATA='\"...\"'` |
| 2 | conan create `sh: no closing quote` | 三层引号转义（Python→bash→mksh）中 `\"\\\"x\\\"\"` 形式在 /system/bin/sh (mksh) 下解析失败 | 宏值改用单引号包双引号 `-DVERSION='\"1.3.0\"'`：bash 剥外层双引号、make 保留单引号内双引号、mksh 剥单引号、clang 收到 `-DVERSION="1.3.0"` |
| 3 | test.sh 1/3 失败（无输出即退出） | 上游 `-v` 打印版本后 get_options 返回 1（设计如此），bash errexit 下命令替换非零即退出 | `set +e` 包裹命令替换，并把 rc=1 纳入断言（版本+退出的预期行为） |
| 4 | CI/conan 环境测试 3 失败 | 环境 TERM=ansi 时 ncurses 渲染日期行的方式与 xterm 不同（日期数字被拆散） | test.sh 强制 `export TERM=xterm`（测试确定性），TERMINFO 指向 ncurses 包的 terminfo |
| 5 | `-lncurses` 链接失败 | ncurses/6.6 只提供 libncursesw.a（宽字符版） | 构建目录建 `libncurses.a -> libncursesw.a` 符号链接（dhex 0.69 / dialog 先例） |

## 源码修改

无补丁（patches: {}）。上游纯 C + POSIX API（含 multiplayer 的 UDP socket、getopt、sigaction/setitimer），musl 全兼容，无需任何源码修改。

## 依赖版本

- ncurses/6.6（制品仓 ohpcd remote，静态宽字符库）

## 验证结果

```bash
# conan-verify: G1 G2 G3 G4 L2 L4 L5 全 PASS（ohos-aarch64 profile）
# test_package 三断言:
#   1. curseofwar -v → 精确输出 "1.3.0"（rc=1 为上游设计）
#   2. curseofwar -h → 含 "Command line arguments" + "Written by Alexey Nikolaev"
#   3. 无头游戏循环 smoke（固定种子 -R 42, timeout 6s）:
#      - "Map is generated" 渲染 ✓（地图生成/玩家放置完成）
#      - 游戏内日期 29 次推进更新（\033[19d<DD> 序列）✓（kings_move/simulate 主循环真实运转）
#      - endwin 终端恢复序列 ✓（SIGTERM 优雅清理）
# 本地实测: 3/3 PASS (rc=0)
```

## 注意事项

- 游戏为 SIGALRM 定时器驱动的实时循环；stdin 管道 + `fcntl(O_NONBLOCK)` 下 fread 输入路径不可用（上游固有行为，交互式 TTY 正常）——无头验证走"运行→观察时钟推进→SIGTERM"路径
- INSTALL_DATA 指向包内 res/curseofwar/（SDL 图片资源不随 ncurses 版本安装）
- 上游无任何测试套件（Makefile 仅 all/clean/uninstall/install 目标；CMakeLists 无 enable_testing）——按 rule8 补 3 个鸿蒙特有测试断言
---

**编译结束**: 2026-09-11 03:13
**最终状态**: published
