# bmkdep

bmkdep 是一个可移植的 BSD `mkdep` 实现，用于根据 C 编译器输出生成 Makefile 依赖列表。

## 功能概述

- 调用 C 编译器生成头文件依赖；
- 合并已有 `.d` 依赖文件；
- 支持目标前缀、多后缀、程序模式、追加和 `.OPTIONAL` 输出；
- 提供 `bmkdep(1)` 手册页。

## HarmonyOS 适配

- 上游 Makefile 依赖 BSD make 基础设施，HarmonyOS 配方直接编译 `mkdep.c` 和 `findcc.c`；
- 默认运行时编译器设为 `clang`，仍可通过 `CC` 环境变量覆盖；
- 临时目录优先使用 `TMPDIR`，未设置时回退到 `/data/local/tmp`；
- 正式制品目标为 HarmonyOS 6.0/aarch64，另在 HarmonyOS 6.0 PC x86_64 虚拟机上进行运行验证。

## 依赖关系

- 编译依赖：HarmonyOS clang；
- 运行依赖：系统 libc；正常编译器模式还需要可执行的 C 编译器，`-d`/`-D` 后处理模式不需要编译器。

## 参考资料

- [上游源码仓库](https://github.com/trociny/bmkdep)
- [pkgsrc 软件说明](https://pkgsrc.se/devel/bmkdep)
