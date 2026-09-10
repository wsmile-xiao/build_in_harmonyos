# myman

受 Namco Pac-Man 启发的迷宫游戏（MyMan video game），Copyright 1997-2009
Benjamin C. Wiley Sittler，MIT 许可。支持多种终端与图形后端（ncurses/slang/
PDCurses/libcaca/SDL/GGI 等）；在 X Window System 显示上通过 PDCurses for X
（XCurses）渲染。

- 上游版本：2009-10-30（myman-wip-2009-10-30，VERSION 0.7.1）
- 源码：https://downloads.sourceforge.net/project/myman/myman-cvs/myman-cvs-2009-10-30/myman-wip-2009-10-30.tar.gz
- 官方主页：https://myman.sourceforge.io/

## HarmonyOS PC 适配（archives/m/myman/2009-10-30）

- X11 显示链路：myman 源码（simple.mk 编译单元：src/myman.c + src/utils.c +
  src/logic.c + mygetopt/mygetopt.c，`-DXCURSES`）+ PDCurses 3.4 X11 端口静态库
  （libXCurses.a）+ vendored X11 依赖（xtrans/libICE/libSM/libXt/libXmu/libXpm/
  libXaw，xeyes 1.3.1 同款方法）+ conan 依赖 libx11/6.4.0 + libxext/6.4.0
  （ohpcd 已发布 OHOS armv8 binary）。
- 游戏数据（迷宫 chr/、精灵 spr/、关卡 lvl/）随包安装到 share/myman/；
  运行时 `cd` 到数据目录或用 `-m/-s/-t` 指定文件路径。
- 音效未启用（SOUND 默认 0），sfx/ 不随包。

## 运行

```
myman -k          # 打印键位说明后退出（无需 X server）
myman -L          # 打印版权/许可信息
myman -h          # 用法说明
cd share/myman && myman   # 进入 X11 游戏模式（需要 X display 与 -geometry 等参数）
```

XCurses 模式额外参数（如 -geometry/-font 等）见 `myman -h` 输出。

## 构建说明

上游构建系统为根 Makefile（GNU Make 巨兽，依赖 gsed/col/groff）+ 自定义
configure（仅把根 Makefile 拷为 GNUmakefile）+ 官方简化构建 simple.mk。
本配方不使用根 Makefile（其对 toybox/OHOS 环境不可控），按 simple.mk 提取
编译单元手写编译命令；PDCurses 3.4 用其自带 autotools configure（显式
--x-includes/--x-libraries 跳过 xmkmf/Imakefile 探测），只构建静态库
libXCurses.a。无补丁（源码零修改，参数全部经 configure/编译命令注入）。
