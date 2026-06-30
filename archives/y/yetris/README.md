# yetris — 终端俄罗斯方块游戏

## 基本信息

- **描述**: yetris 是一个可定制的 Tetris™ 克隆，运行于终端环境。支持多种方块系统（SRS 等）、自定义颜色、配置文件和分数记录。
- **主页**: http://yetris.alexdantas.net/
- **许可证**: GPLv3
- **作者**: Alexandre Dantas <eu@alexdantas.net>

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.3.0 | built | 2026-06-18 |

## 依赖

- ncurses（静态链接）

## 构建说明

yetris 使用纯 Makefile 构建，无 configure 脚本。

关键编译参数：
- `PREFIX=$DEFAULT_PREFIX` — 安装前缀
- `CFLAGS_PLATFORM="-I$DEFAULT_PREFIX/include -Wno-narrowing"` — 头文件路径 + C++11 narrowing 抑制
- `LDFLAGS_PLATFORM="-L$DEFAULT_PREFIX/lib"` — 库文件路径

平台注意事项：
- ncurses.h 需修复 C++ bool 兼容性（`#if 0` → `#if defined(__cplusplus)`）
- PieceDefinitions.cpp 中的负整数 char 初始化触发 C++11 narrowing，需 `-Wno-narrowing`
