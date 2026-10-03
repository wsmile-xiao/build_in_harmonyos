# libflorist (FLORIST — POSIX.5 Ada bindings)

[FLORIST](https://github.com/AdaCore/florist) 是 IEEE STD 1003.5 (POSIX.5)、
IEEE STD 1003.5b 以及部分 IEEE STD 1003.5c 的 Ada 绑定实现，最初由佛罗里达州立
大学 (FSU) 在美国国防部 POSIX Ada Real-Time (PART) 项目下开发，1999 年后交由
AdaCore 维护。它让 Ada 程序可以直接调用 POSIX 操作系统服务（进程、文件、
信号、定时器、消息队列、共享内存、socket、终端控制等）。

上游以 GNAT（GNU Ada 编译器）为唯一目标编译器。

## 已编译版本

- `2025.1.0`：`built`

## OHOS 适配要点

### 1. 必须原生构建（无交叉 Ada 编译器）

ohpcd 中唯一的 Ada 工具链 `gcc-ada/9.5.0` 与其装配工具 `binutils/2.46.0`
**都只有 OHOS/armv8 制品**，不存在 Linux x86_64 的交叉 Ada 编译器。因此：

```
conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
```

配方 `validate()` 对交叉构建显式拒绝，避免留下难以定位的失败。

### 2. 只能产出静态库

`gcc-ada/9.5.0` 安装的 Ada 运行库（`adalib/libgnat.a`、`libgnarl.a`）是
**非 PIC** 的静态归档，链接进共享对象会报
`relocation R_AARCH64_ADR_PREL_PG_HI21 ... can not be used when making a shared object`。
故本包 `shared=False`，`validate()` 拒绝 `shared=True`。

### 3. gprbuild / gprinstall / gnatprep 均缺失

上游 `Makefile.in` 的 `floristlib-%` 目标调用 `gprbuild -Pflorist`，`install-%`
调用 `gprinstall`；`*.gpb` 模板依赖 `gnatprep`。而 `gcc-ada/9.5.0` 只提供
`gnatmake`/`gnatbind`/`gnatlink`/`gnatchop`/`gnatclean`/`gnatls`。本配方的对策：

- 库的编译改为**直接调用 `gnatmake`**（`-Dobj` 汇总对象与 ALI）；
- 安装改为**显式布局**，复刻上游文档承诺的 `<prefix>/floristlib/*` 与
  `<prefix>/share/gpr/florist.gpr`（见上游 README）；
- 内置一个最小 `gnatprep` 替身 `tools/gnatprep-shim.py`（两个 `.gpb` 只用到
  `#if/#else/#end if` 条件指令）。

### 4. 必须同时编译库内 C 单元

`florist.gpr` 声明 `for Languages use ("C", "Ada")`。`libsrc/posix-macros.c`
提供 `fetch_errno`/`store_errno`、`wifexited`、`s_isdir` 等被 Ada 以
`pragma Import (C, ...)` 引用的符号；漏编会导致最终链接报
`undefined reference to 'store_errno'`。因此配方在 Ada 编译后显式编译
`libsrc/posix-macros.c` 与 `libsrc/posix-macros-sockets.c` 入归档。

### 5. 平台适配补丁

`patches/0001-musl-signal-range.patch`：`c-posix.c` / `c-posix-signals.c` 中的
`sigismember()` 越界守卫假定 glibc 语义（越界返回 `-1`）。OHOS 使用 musl，
越界返回 `0`，于是 `first_bad` 恒为 `-1`，两处守卫都误判信号区间无效并向下
取整，最终生成 `NSIGS : constant := -2` 与越界空数组，使 `posix-signals.ads`
成为非法 Ada（`dynamic or empty choice in aggregate`）。补丁改为仅在
`first_bad` 有效时收紧上界。

### 6. 其他已固化的平台处理（不入补丁，均在配方内）

| 现象 | 根因 | 配方内对策 |
|------|------|-----------|
| `configure: error: cannot run C compiled programs` | OHOS 拒绝执行未签名 ELF，conftest 被杀（E064） | `--build` 与 `--host` 取不同三元组，使 autoconf 经 canonical 路径进入交叉分支 |
| `configure: error: cannot guess build type` | 上游 `config.guess` 不识别 HarmonyOS（E007） | 本包 configure 未调用 config.guess 做三元组推断（三元组显式传入），未触发；如后续版本触发需按先例补 config.guess/config.sub 补丁 |
| `config.status: could not setup config files machinery`（`can't create ./confXXXXXX/subs1.awk`） | configure/config.status 以 `umask 077` 建临时目录，HMDFS 下该目录不可写 | 配方生成 `mktemp` 垫片置于 PATH 首位（强制 `umask 022`），不改动生成文件（R6） |
| 生成器 `c-posix` 运行时段错误 | 动态链接的 gcc-ada 二进制首次 stdio `stderr` 访问即崩溃（`write(2, ...)` 正常） | 生成器一律 `-static` 链接 |
| `fatal error, run-time library not installed correctly` | GNAT 运行库路径未导出 | `VirtualBuildEnv` + 显式 `ADA_INCLUDE_PATH`/`ADA_OBJECTS_PATH`/`GCC_EXEC_PREFIX` |
| Ada 与 C 胶水混链风险 | profile 注入 OHOS clang 作 `$CC` | `generate()` 把 `CC`/`CPP` 固定回 gcc-ada 的 gcc，保证 Ada 与 C 同源 |

### 7. 消费者使用方式

本包不产出可执行文件（纯库），无需 `commands.json`。

```conan
[requires]
libflorist/2025.1.0
```

包内布局与上游一致，Ada 源规格与静态库同处 `floristlib/`：

```
floristlib/
  posix.ads, posix.adb, ...        # 上游 Ada 规格与实现（含 threads/ 子目录单元）
  *.ali                            # 编译产物（Ada 库信息文件）
  libflorist.a                     # 静态库
share/gpr/florist.gpr              # 项目文件（已重定向到 floristlib）
share/gpr/florist.gpr.upstream     # 上游原始项目文件（参考）
licenses/COPYING                   # GPL-2.0
```

消费者编译示例（GNAT）：

```sh
gnatmake -I<prefix>/floristlib -aL<prefix>/floristlib \
         main.adb -cargs -largs -lflorist
```

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| `gcc-ada/9.5.0` | tool_requires | GNAT 编译器（OHOS/armv8） |
| `binutils/2.46.0` | tool_requires | `as` / `ld`（OHOS/armv8） |

## 许可证

GPL-2.0-or-later，并带 GNAT 特有的 GCC 例外条款（`COPYING` 随包安装至
`licenses/`）。源文件头部声明：
*FLORIST is free software; you can redistribute it and/or modify it under terms
of the GNU General Public License as published by the Free Software Foundation;
either version 2, or (at your option) any later version.*

## 参考

- [AdaCore/florist](https://github.com/AdaCore/florist)
- [FSU FLORIST 项目页](https://cs.fsu.edu/~baker/florist.html)
