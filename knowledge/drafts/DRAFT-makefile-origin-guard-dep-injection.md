# DRAFT: 手写 Makefile 的依赖注入缝——origin 守卫 + ?= 变量外部注入

> 来源：mupen64plus-core 2.6.0 适配（N64 模拟器核心，任务 #6728，2026-09-09）
> 状态：草稿（随 PR 提交，定稿编号由主编确认）

## 问题场景

手写 GNU Makefile（非 autotools/cmake）的 C/C++ 项目在 OHOS 交叉编译环境全灭：

1. **OS 探测拒识**：`UNAME ?= $(shell uname -s)`，OHOS 设备返回 `HarmonyOS`，
   Makefile 的 ifeq 链只有 Linux/Darwin/FreeBSD/MINGW 分支 →
   `*** OS type "HarmonyOS" not supported. Please file bug report`
2. **依赖探测失败**：zlib/libpng/SDL 探测走 `pkg-config --modversion` /
   `which sdl2-config`，交叉目标的 conan 包不在系统 pkg-config 路径 →
   `*** No zlib development libraries found!`
3. **编译器硬编码**：`CC = $(CROSS_COMPILE)gcc`，无 gcc 或需用 clang 时无法通过
   环境变量覆盖（Makefile 文件内赋值优先于环境变量）

## 根因与机制

此类 Makefile 的探测段普遍带**逃逸阀**：

```make
ifeq ($(origin ZLIB_CFLAGS) $(origin ZLIB_LDLIBS), undefined undefined)
  ...pkg-config 探测...
endif
```

`$(origin VAR)` 返回 `undefined` 仅当变量**从未被定义**——预定义同名变量
（命令行/环境）即整体跳过探测分支。UNAME 用 `?=`（条件赋值）同理可外部覆盖。
CC/CXX 虽是文件内无条件赋值，但 **make 命令行变量优先级最高**，命令行传入即覆盖。

## 方案（三层注入，零补丁）

```bash
make -C projects/unix all \
  UNAME=Linux \
  ZLIB_CFLAGS="-I$ZLIB_PREFIX/include" ZLIB_LDLIBS="-L$ZLIB_PREFIX/lib -lz" \
  LIBPNG_CFLAGS="-I$PNG_PREFIX/include" LIBPNG_LDLIBS="-L$PNG_PREFIX/lib -lpng16" \
  SDL_CFLAGS="-I$SDL_PREFIX/include/SDL2 -D_REENTRANT" SDL_LDLIBS="-L$SDL_PREFIX/lib -lSDL2" \
  CC=$CROSS_CC CXX=$CROSS_CXX
```

conanfile.py 实现要点：

- `requirements()` 正常声明 conan 依赖（zlib/libpng/sdl2）
- `build()` 用 `self.run("make ... " + " ".join(args))`，args 由
  `self.dependencies["sdl2"].package_folder` 等构造
- **含空格的值必须 shell 引号包裹**（`shlex.quote`）——否则 make 把
  `-D_REENTRANT` 解析为 make 自身选项（`make: invalid option -- D`）

## 识别清单（何时适用）

```bash
# 探测守卫一键枚举
grep 'ifeq ($(origin' Makefile
# OS 探测变量确认 ?=
grep 'UNAME ?=' Makefile
```

## 适用边界

- ✅ 手写 Makefile + pkg-config 探测（mupen64plus-core 及大量模拟器/游戏项目）
- ❌ autotools（有 config.guess 机制，见 E007）
- ❌ cmake（有 CMAKE_SYSTEM_NAME，见 E092）
- 无 origin 守卫的项目：退路是 pkgconf tool_requires + PkgConfigDeps（生成 .pc
  + PKG_CONFIG_PATH），patch 探测段是最后手段

## 关联

- E097（BearSSL 自定义 Makefile）——同为手写 Makefile 但无守卫，走了
  custom-config-mk；本条是「有守卫」的对偶形态，注入优于 patch
- E016（汇编指令不支持）——本项目 arm64 汇编直接可用（见姊妹草稿：
  GAS ARM64 汇编经 clang 集成汇编器零补丁编译）
- E540（runner PATH 缺 /data/service/hnp/bin）——同属 Makefile 生态的运行时路径
