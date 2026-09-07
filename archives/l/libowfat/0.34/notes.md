# libowfat 0.34 适配笔记

## 概要

| 项目 | 值 |
|---|---|
| 上游 | https://www.fefe.de/libowfat/ (Felix von Leitner) |
| 版本 | 0.34 (tarball `libowfat-0.34.tar.xz`, 223960 字节, 1061 个文件) |
| SHA256 | `d4330d373ac9581b397bc24a22ad1f7f5d58a7fe36d9d239fe352ceffc5d304b` |
| 许可证 | GPL-2.0-only (源码树 COPYING 为 GPLv2) |
| 构建系统 | 上游手写 GNU Makefile(无 CMake/Autotools,INSTALL 自述"没有真正的 make install") |
| 目标 | aarch64-linux-ohos(HarmonyOS PC 原生构建) |
| 产物 | 22 个静态归档:21 个模块库 + 1 个伞形 libowfat.a;仅静态,上游无共享库规则 |
| 公共头 | 37 个(INCLUDES 列表,安装为 `include/libowfat/*.h` 扁平布局) |
| 依赖 | 无第三方库依赖;链接期仅 libc/pthread(`t` 与 io 层用 `-lpthread`) |

## 上游源与镜像

- 官方 `https://www.fefe.de/libowfat/libowfat-0.34.tar.xz`:本网络下 TLS 握手失败(SSL error)。
- 镜像 `https://ftp.fau.de/unix/ftp.fefe.de/libowfat/`:返回 273 字节 HTML 错误页。
- 采用 `https://cdn.netbsd.org/pub/pkgsrc/distfiles/LOCAL_PORTS/libowfat-0.34.tar.xz`(NetBSD pkgsrc distfiles CDN),字节级校验一致,SHA256 与 pkgsrc wip/libowfat distinfo 记录相符。

## 构建系统审计(GNUmakefile)

### CC 的 PATH 扫描重赋(关键坑)

GNUmakefile 69-74 行**无条件**按 PATH 扫描重赋 CC:PATH 里有 `gcc` 就用 gcc,否则用裸名 `clang`。环境变量 CC 会被静默丢弃(实测:`env CC=env-clang make -n ent` 的探针命令仍为裸 `clang`)。make 命令行变量优先级高于 makefile 内任意赋值,是唯一可靠的注入方式——因此配方向 make 传**绝对路径**的命令行变量 `CC=`,杜绝"PATH 偶然命中裸 gcc/clang"。

### CFLAGS 同理

44 行 `CFLAGS=...` 无条件赋值;命令行变量可整体覆盖(`+=` 对命令行来源变量不生效,须一次拼全)。

### AR/RANLIB

仅以 `$(CROSS)$(AR) cru` / `$(CROSS)$(RANLIB)` 形式引用,无重赋块,但裸名仍靠 PATH 解析;配方同样以绝对路径命令行变量传入(`llvm-ar`/`llvm-ranlib` 或 SDK 提供的 `ar`/`ranlib`)。

### sysdeps 探针(无宿主污染)

所有 `try*.c` 探针(tryuint128/tryepoll/trypoll/trysl/tryip6/tryn2i/…)都是**纯编译期探测**:规则形如 `-rm -f $@; if $(DIET) $(CCC) $(CFLAGS) -c tryX.c 2>/dev/null; then cp .h1; else cp .h2; fi`,`$(CCC)` 即目标 `$(CC)`。因此 `have*.h`、`iopause.h`(select.h 同理,由 trypoll.c 决定)描述的是 **OHOS 目标**而非构建宿主。唯一的宿主执行环节是 `ent`(entities.json → entities.h 的生成器,由 `$(CC) -g` 编译后运行);本机为 OHOS 原生构建,目标编译器产物即可执行,无需 host/target 分裂。`libsocket` 是一个文本文件(Linux/OHOS 上为空),不是库。

### make clean 的坑

`make clean` 会删除 `.h1/.h2` 模板文件自身(上游 bug),因此配方**不调用** clean,conan 的干净源码目录天然满足可重复构建。

### 硬链接失败(本环境补丁)

`headers` 目标与 `libowfat/%` 规则用 `ln -f` 硬链接;HarmonyOS PC 文件系统对硬链接创建返回 EPERM。补丁 `0001-no-hardlink-headers.patch` 将两处 `ln -f` 改为 `cp -f`,语义不变(文件落入 `libowfat/`)。

### 安装

上游无真正 install;配方自行收集:伞形 `libowfat.a` + 21 个模块 `.a` + 37 个公共头(扁平 `include/libowfat/`)。

## 上游测试(`t`)

- `UNITTESTS=$(shell grep -l UNITTEST */*.c)` → 77 个源文件带 UNITTEST 宏,链接进单一 `t` 可执行文件。
- `t` 需要可写 CWD(io 测试写 `t.tmp` 等)与 ~1.1MB 的管道回环。
- **退出码倒置**(上游故意的):`return totalread == total;` — **exit 1 = 全部 1120372 字节回读成功 = 通过;exit 0 = 失败**。配方按此解释。
- 原生 OHOS 实测:构建成功,`./t` 多次运行稳定 exit 1(通过)。
- t.c 的 rdtscl 使用点全部位于 `#if 0` 块内(line 35 定义宏),aarch64 无障碍。

## 工具链传播实测(证据)

1. **正例**:命令行变量 `CC=/abs/clang`(PATH 内无 gcc)→ 探针命令全部为该绝对路径 clang(如 `if clang ... -c trysl.c`),`haveuint128.h` 等正确生成,`./t` 通过。
2. **反例**:仅设环境变量 `CC=env-clang` → 探针命令为裸 `clang`(PATH 扫描重赋,环境变量被丢弃)。
3. **负向验证**:PATH 收缩为 `/usr/bin:/bin`(无任何编译器、无 make、无 ar),仅以绝对路径命令行变量传 CC/AR/RANLIB + 可写 TMPDIR → 完整构建 + `./t` 通过(exit 1)。证明配方不依赖 PATH 偶然命中。
4. TMPDIR 必须可写:OHOS clang wrapper 需要 `/tmp` 临时区;本机 `/tmp` 只读,负向验证时显式 `TMPDIR=<workdir>/tmp`。conan build 目录天然可写,`conan create` 实测无需额外设置。

## Conan 2 配方要点

- `package_type = "static-library"`(上游只有静态归档)。
- CC/AR/RANLIB 解析顺序:`tools.build:compiler_executables`(JSON conf)→ 环境变量 → 候选文件存在性校验 → PATH 解析(解析后仍是绝对路径)。任何候选必须是真实可执行文件,避免裸名。
- CFLAGS 按构建类型映射(-O2/-g…),fPIC 由选项控制,一次性命令行变量传入。
- components 暴露 21 个模块库,伞形 `libowfat`(`libs=["owfat"]`)为默认链接目标,`system_libs=["pthread"]`。
- 头文件按上游 install-inc 语义扁平安装到 `include/libowfat/`。

## 知识库查重结论

- 探针全部为目标编译器编译期探测(无运行探针)→ **E284**(目标平台配置头)与 **E359**(构建机工具/宿主执行)已覆盖;`ent` 生成器属 E359 的 HOSTCC 模式(本机原生构建,同一编译器即可)。
- CC 的 PATH 扫描重赋(环境变量被丢弃)→ **E095** 自定义 Makefile 忽略环境 CC 的根因一致。
- E546 不存在(知识库最新为 E542);E072 是 config.sub 三元组问题,与本案不同。
- **结论:复用 E284/E359/E095,不新建知识草稿。**
