# libowfat 0.34

libowfat 是 Felix von Leitner 的底层组件库("Liberate your programs from
your OS' libc"),以手写 GNU Makefile 驱动,包含 byte/str/fmt/scan/
stralloc/array/buffer/io/socket/textcode/cdb/critbit/dns 等 21 个模块
静态归档与一个伞形 `libowfat.a`。

- 上游: https://www.fefe.de/libowfat/
- 许可证: GPL-2.0-only
- 构建系统: 自定义 GNU Makefile(上游无 CMake/Autotools,无真正 install)
- 目标平台: linux / ohos(aarch64-linux-ohos 已验证,HarmonyOS PC 原生构建)
- 产物: 仅静态库(上游无共享库规则)
- 依赖: 无第三方依赖;链接期 libc + pthread

## 用法

```cmake
find_package(libowfat REQUIRED)
target_link_libraries(myapp PRIVATE libowfat::libowfat)
```

伞形目标链接 `libowfat.a`(内含全部模块对象)并自动带上 pthread。
如需最小链接集,可用模块组件目标(`libowfat::byte`、`libowfat::str`、
`libowfat::fmt`、`libowfat::scan`、`libowfat::array`、`libowfat::buffer`、
`libowfat::io`、`libowfat::socket` 等 21 个)。

头文件为扁平布局 `#include <libowfat/byte.h>` 等,与上游 install-inc 一致。

## 构建说明

配方以 make **命令行变量**注入绝对路径的 CC/AR/RANLIB 与 CFLAGS:
上游 GNUmakefile 会无条件按 PATH 扫描重赋 CC(环境变量被丢弃),命令行
变量是唯一可靠的覆盖途径;同时规避"PATH 偶然命中裸 gcc/clang"。
sysdeps 特性头(have*.h/iopause.h)全部由**目标编译器**编译期探测生成,
无宿主污染(详见 notes.md)。

唯一的宿主执行环节是 `ent` 实体表生成器(entities.json → entities.h);
原生 OHOS 构建下目标编译器产物即可执行。

补丁 `0001-no-hardlink-headers.patch`:上游 `headers` 规则的 `ln -f`
硬链接在本文件系统上 EPERM,改为 `cp -f`(语义不变)。

## 测试

- 上游 `t` 二进制:77 个 UNITTEST 集成,注意**退出码倒置**(exit 1 =
  通过,exit 0 = 失败),详见 notes.md 与 manifest.yaml。
- test_package:从安装包验证 byte/str/array/buffer/fmt/scan/io 七个
  核心模块,34 个断言。
