# myman

受 Namco Pac-Man 启发的迷宫游戏（MyMan video game），Copyright 1997-2009
Benjamin C. Wiley Sittler，MIT 许可。支持多种终端与图形后端（ncurses/slang/
PDCurses/libcaca/SDL/GGI 等）。

- 上游版本：2009-10-30（myman-wip-2009-10-30，VERSION 0.7.1）
- 源码：https://downloads.sourceforge.net/project/myman/myman-cvs/myman-cvs-2009-10-30/myman-wip-2009-10-30.tar.gz
- 官方主页：https://myman.sourceforge.io/

## 版本索引

| 版本 | 显示后端 | 关键依赖 |
|------|----------|----------|
| `archives/m/myman/0.7.0` | ncursesw 文本终端 | ncurses/6.6（SourceForge 正式源码包，数据编译内建） |
| `archives/m/myman/0.7.1` | ncursesw 文本终端 | ncurses/6.6（数据/BUILTIN_* 编译内建，仅动态依赖 libc） |
| `archives/m/myman/2009-10-30` | X11（PDCurses for X = XCurses） | libx11/6.4.0 + libxext/6.4.0 + vendored X11 栈（libXt/libXmu/libXpm/libXaw…） |

## HarmonyOS PC 适配（archives/m/myman/0.7.0，ncursesw 文本终端）

- 使用 SourceForge 官方 `myman-0.7.0.tar.gz`（SHA-256 固定于配方）；依赖 `ncurses/6.6`。
- 该版本通过包内烟雾测试执行 `myman --version` 与 `myman --help`。

## HarmonyOS PC 适配（archives/m/myman/0.7.1，ncursesw 文本终端）

- 输出驱动：`./configure --with-ncursesw`，Makefile 经 `NCURSESW_CONFIG`
  （ncurses 包的 ncursesw6-config）取 cflags/libs；依赖 `ncurses/6.6`
  （ohpcd 已发布，wide-char 静态构建）。
- 终端全屏 ncurses 图形：256 色 / ACS 画线字符 / 宽字符；内建 270+ 迷宫变体
  （myman、pacman、jrpac、gobble…）与 40+ tile/sprite 字号，运行时用
  `-v variant -z size` 选择；全部数据编译内建（BUILTIN_*），无外部数据文件。
- HarmonyOS 无 GNU coreutils/GNU sed：Makefile 的 coreutils.ok/sed.ok 自检
  通过配方生成的 wrapper 脚本（conf/install|rmdir|sed，委托 toybox）应答。
- configure/make 在非 HMDFS 目录（/data/storage/el2/base）进行，规避 E011
  （HMDFS 权限/执行位问题）。
- `make install DESTDIR=<stage>` 分拣产物：bin/myman + man6 + doc。

## HarmonyOS PC 适配（archives/m/myman/2009-10-30，X11）

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
myman -h          # 用法说明（含全部 variant/size 列表）
myman --version   # 版本信息

# 0.7.1（ncursesw 终端后端）
myman -v pacman -z big    # 以 pacman 变体、big 字号游玩

# 2009-10-30（X11 后端）
cd share/myman && myman   # 进入 X11 游戏模式（需要 X display 与 -geometry 等参数）
```

XCurses 模式额外参数（如 -geometry/-font 等）见 `myman -h` 输出。

## 构建说明

- `0.7.1`：上游自定义 configure（非 autoconf，只把根 Makefile 拷为
  GNUmakefile）+ GNU make；配方生成 toybox wrapper 应答 coreutils.ok/sed.ok
  自检，并在非 HMDFS 目录完成 configure/make。
- `2009-10-30`：上游构建系统为根 Makefile（GNU Make 巨兽，依赖 gsed/col/
  groff）+ 自定义 configure（仅把根 Makefile 拷为 GNUmakefile）+ 官方简化构建
  simple.mk。本配方不使用根 Makefile（其对 toybox/OHOS 环境不可控），按
  simple.mk 提取编译单元手写编译命令；PDCurses 3.4 用其自带 autotools
  configure（显式 --x-includes/--x-libraries 跳过 xmkmf/Imakefile 探测），只
  构建静态库 libXCurses.a。无补丁（源码零修改，参数全部经 configure/编译命令
  注入）。

## 上游与许可

- 上游：https://sourceforge.net/projects/myman/
- 源码快照：myman-wip-2009-10-30（SourceForge myman-cvs-2009-10-30）
- 许可：MIT
