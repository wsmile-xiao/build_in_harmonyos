# kernel-style kbuild 包用命令行变量注入 `EXTRA_KLIBCCFLAGS` 会整体覆盖目录级配置宏（klibc/usr-dash 编译失败）

> Draft: DRAFT-KBUILD-EXTRA-KLIBCCFLAGS-CMDLINE-OVERRIDE
> Stem: `klibc-dash-extra-klibccflags-cmdline-override` — pairs with the same-stem `.kv`
> 来源：klibc-dash/2.0.14 适配（2026-09-25，HarmonyOS PC aarch64 + clang 15）

## 基本信息

- **ID**: DRAFT-KBUILD-EXTRA-KLIBCCFLAGS-CMDLINE-OVERRIDE
- **严重度**: 2
- **类别**: build-system|portability|headers|compile
- **触发工具**: make|clang|gcc|conan
- **阶段**: compilation|configuration

## 错误特征

交叉编译 kernel-style kbuild（klibc 家族）时，若把架构标志挂在命令行变量上：

```bash
make KLIBCARCH=arm64 CC=clang ... EXTRA_KLIBCCFLAGS=--target=aarch64-linux-ohos -j1
```

`usr/dash` 的编译会在**头文件声明**处报出两组看似无关的错误（错误行完全指向 `system.h`）：

```
usr/dash/system.h:90:6: error: expected ')'
long sysconf(int) __attribute__((__noreturn__));
      ^
usr/dash/system.h:90:6: error: cannot redeclare builtin function '__builtin_constant_p'
```

完整 include 链会显示 `sysconf` 宏来自 `usr/include/sys/sysconf.h:38`。

## 根因

GNU make 的**命令行变量赋值优先级最高**，会覆盖 Makefile 内所有同名赋值（含 `:=` 与 `+=`）。
而 `usr/dash/Kbuild:8-10` 恰恰用 `EXTRA_KLIBCCFLAGS` 承载三类必需内容：

```make
EXTRA_KLIBCCFLAGS := -I$(srctree)/$(src) -I$(objtree)/$(obj)
EXTRA_KLIBCCFLAGS += -include $(srctree)/$(src)/config.h
EXTRA_KLIBCCFLAGS += $(config-cppflags)      # -DBSD=1 -DSMALL -DJOBS=0 -DHAVE_CONFIG_H -DSHELL ...
```

命令行一覆盖，`config.h` 不再被 `-include` → `HAVE_SYSCONF` 未定义 → `system.h:90` 的
`long sysconf(int);` 声明生效 → 被 klibc 的函数式宏展开：

```c
/* klibc 的 usr/include/sys/sysconf.h */
#define sysconf(x) (__builtin_constant_p(x) ? __sysconf_inline(x) : sysconf(x))
```

于是报出 `expected ')'` 与 `cannot redeclare builtin function '__builtin_constant_p'`。

注意 `usr/klibc/Kbuild` **不设置**该变量，所以同一份配方对 libc 本体构建正常——只有
`usr/dash`（以及同为 kbuild 子目录的 `usr/gzip`）会踩中，表现为「libc 能编、dash 不能编」。

## 修复

**不要用命令行变量注入 `EXTRA_KLIBCCFLAGS`/`EXTRA_KLIBCLDFLAGS`**，把架构标志写进
`CC` / `LD` 自身的命令行内容（kbuild 通过 `$(CC)`/`$(LD)` 调工具，标志自然传递）：

```bash
make KLIBCARCH=arm64 KLIBCKERNELSRC="<kernel-headers>" KLIBCASMDIR="aarch64-linux-ohos/asm" \
     CC="clang --target=aarch64-linux-ohos" HOSTCC=clang \
     AR=llvm-ar RANLIB=llvm-ranlib STRIP=llvm-strip NM=llvm-nm \
     OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump \
     LD="ld.lld -m aarch64linux" PERL=perl -j1
```

`HOSTCC` 保持本机 clang（hostprogs 如 `mkinit`/`mknodes`/`mksyntax` 需在本机运行）。
修复后 `usr/dash/static/sh`、`shared/sh` 与 libc 全部产出（exit 0）。

## 验证与判据

- 复验：`make … -j1` → exit 0；`usr/dash/static/sh` 存在且可运行（签名后 `sh -c 'echo hello'` → `hello`）
- 判据：`grep -n "EXTRA_KLIBCCFLAGS" <src>/usr/*/Kbuild` 命中即需警惕该变量被命令行覆盖
- 关联：E098（无 GNU install）、E077（OHOS ELF 签名）
