# ninvaders

nInvaders — 终端版太空侵略者（Space Invaders）游戏

## 简介

nInvaders 是经典的太空侵略者（Space Invaders）游戏在终端上的实现，使用 ncurses 库渲染。玩家操控飞船抵御外星人入侵，包含外星人、飞船、UFO 和掩体等经典游戏元素。

## 基本信息

| 属性 | 值 |
|------|---|
| 名称 | nInvaders |
| 版本 | 0.1.1 |
| 语言 | C |
| 构建系统 | Makefile（非 autotools，无 configure 脚本） |
| 许可证 | GPL-2.0-or-later |
| 运行依赖 | ncurses（编译时静态链接，运行时仅需 libc） |
| 主页 | http://ninvaders.sourceforge.net |
| 作者 | Dettus (dettus@matrixx-bielefeld.de) |

## 编译适配要点

本项目使用简单 Makefile（非标准 autotools），在鸿蒙平台编译需注意：

1. **编译器替换**: CC 从 gcc 改为 clang
2. **-fcommon 标志**: 头文件（aliens.h、nInvaders.h）含非 extern 全局变量定义，clang 默认 `-fno-common` 会报 multiple definition 错误，需加 `-fcommon`
3. **链接器选择**: OHOS SDK 的 lld 依赖 libxml2.so.16（不可用），需用 `-fuse-ld=bfd` 切换到 GNU ld
4. **install 目标**: 原 Makefile 无 install 目标，需手动添加（支持 DESTDIR）
5. **ncurses 静态链接**: 符合 R4 铁律，运行时零外部依赖

## 已编译版本

| 版本 | 状态 | 日期 | 补丁 | 备注 |
|------|------|------|------|------|
| 0.1.1 | built | 2026-06-03 | 1个 (0001-Makefile.patch) | 需要 `-fcommon` 和 `-fuse-ld=bfd` |

## 预编译包

- `ninvaders-0.1.1-ohos-aarch64.tar.gz` (320KB)
- 仅包含 `bin/nInvaders`，运行时依赖 libc.so
- ncurses 已静态链接，无需额外安装