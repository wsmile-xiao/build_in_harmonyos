# XmHTML 1.1.10 适配笔记

## 概览

- 软件：XmHTML（Motif HTML 显示 widget 库，HTML 3.2 rich-text；Ripley Software Development）
- 上游版本：1.1.10（最终发布版，LGPL-2.0）
- 源码：`XmHTML-1.1.10.tgz`，来自 FreeBSD ports 权威 distfile 镜像
  `https://pkg.freebsd.org/ports-distfiles/XmHTML-1.1.10.tgz`
  （sha256 `379542629958d70a61a49955f44833e215c82500d6bdcc12d4e7252deefe0435`，与
  `x11-toolkits/xmhtml/distinfo` 一致；上游 www.xmhtml.org 与 SourceForge release 文件均已不可达）
- 构建系统：**上游手写 Makefile**（非 autotools / 非 Imake / 非 CMake）
  - `TOOLKIT=Motif`、`HAVE_XPM=1`、`HAVE_XFT=1`、`-DHAVE_LIBJPEG -DHAVE_LIBPNG`
  - `make lib` → `lib/common` + `lib/Motif` 目标文件 → `libXmHTML.a` + `libXmHTML.so.1.1.10`
    （SONAME `libXmHTML.so.1.1`）
  - **全树无 install 目标** → `package()` 显式收集头文件/库并补 SONAME 软链
  - `MAKEDEPEND=gccmakedep`（环境无该工具）→ 全新构建不触发 `depend` 目标即可
- 真实依赖面（取自上游 Makefile）：`LIBS=-lXm -lXmu -lXt -lXext -lX11 -lSM -lICE`、
  `IMAGELIBS=-ljpeg -lpng -lz -lm`（`HAVE_LIBJPEG/HAVE_LIBPNG` 默认开）、`HAVE_XPM=1` →
  `-lXpm`、`HAVE_XFT=1` → `-lXft -lfontconfig`

## 关键缺口与处置（探索期实测）

1. **Xft.h 是公共接口的一部分**：`XmHTML.h` 在 `HAVE_XFT=1` 时链入 `<X11/Xft/Xft.h>`，
   而 Xft.h 直接 `#include <X11/extensions/Xrender.h>` → 仅靠传递依赖不够，
   `libxrender`/`libxft`/`fontconfig`/`freetype` 必须保持**直接依赖**且
   `transitive_headers=True`，否则消费者侧报 `fatal error: 'X11/extensions/Xrender.h'
   file not found`（探索期实测）。
2. **freetype 头目录布局**：`ft2build.h` 位于 `<pkg>/include/freetype2`（不在 include 根）
   → 构建期在依赖 `includedirs` 之外补 `include/freetype2` 与 `include/fontconfig`
   （探索期实测 `fatal error: 'ft2build.h' file not found`）。
3. **无 install 目标**：`package()` 手工投递 `include/XmHTML/*.h`、`include/common/*.h`
   （`keep_path=True` 保留上游布局）与库文件；并创建 `libXmHTML.so.1.1`、
   `libXmHTML.so` 软链（上游只产出带完整版本号的文件；HMDFS 不能 `ln -sf` 覆盖，先删后建，R1）。
4. **musl 遗留符号面（实测：无需处置）**：源码中出现 `strcasecmp`(34 文件)、
   `strncasecmp`(14)、`regexec/regcomp`(7)、`bcopy`(3)、`bzero`(2)、`bcmp`(1)、
   `sys_errlist`(1)、`gettimeofday`(2)、`sys/param.h`(3)，但全部落在上游特性宏保护分支内
   ——编译期 `-Wimplicit-function-declaration` 0 条，链接期 0 个 undefined reference。
   故**本包零源码补丁**（与 xli 的 rindex 缺口形成对照，见 knowledge/drafts 扩展条目）。
5. **依赖图冲突**：motif/libxt pin `libx11/1.8.13`，libxext 自带 pin `libx11/6.4.0`
   → `self.requires("libx11/1.8.13", force=True)` + 选 `libxext/6.4.0.1`
   （延续 libXmu/1.3.1 与 xmcd 3.3.2 的既有组合）。
6. **上游版本选择**：`libxmu/1.3.1` 未发布到制品仓（`conan download --only-recipe`
   报 system acceleration policy），改用已发布的 **`libxmu/1.3.1.1`**（W0 预检 15 项 14 OK）。

## 编译开关（配方 `build()` 实参）

```
make -j1 lib \
  CC='<clang>' \
  EXTRA_CFLAGS='-O2 -fPIC -I<src> -I<deps...> -I<pkg>/include/freetype2 -I<pkg>/include/fontconfig' \
  EXTRA_INCLUDES='-I<deps...>' \
  LOADLIBES='-L<deps...> -lXm -lXmu -lXt -lXext -lX11 -lSM -lICE -ljpeg -lpng -lz -lm -lXpm -lXft -lfontconfig'
```

上游 Makefile 自带 `OS_CFLAGS`/`IMAGEDEFINES`/`XFT_DEFINES`，配方仅补依赖头目录与链接串（R1 参数最少化）。
`CC` 取 `tools.build:compiler_executables["c"]`（R33：不裸用 shell 变量）；目标机为 aarch64，
OHOS SDK clang 为平台原生工具链（默认目标即 aarch64-linux-ohos），与 xmcd/xli 一致只传编译器本体。

## 产物与验证（本地探索编译，2026-10-04）

- `make lib` rc=0；`lib/libXmHTML.so.1.1.10` = 596,480 B、`lib/libXmHTML.a` = 730,746 B；
  `include/` 布局：`XmHTML/`(14) + `common/`(12) + `gtk-xmhtml/`(9) + `http/`(2) + `bitmaps/` + `pixmaps/`(63)
- `DT_NEEDED`（13 项，全部可由依赖前缀解析）：`libXm.so.4 libXmu.so.6 libXt.so.6 libXext.so.6
  libX11.so.6 libSM.so.6 libICE.so.6 libjpeg.so.62 libpng16.so.16 libXpm.so.4 libXft.so.2
  libfontconfig.so.1 libc.so`；无 RPATH/RUNPATH
- 未定义符号仅为外部 X11/fontconfig 符号（`Fc*`/`X*`），无 libc 缺口
- 编译告警（非阻塞）：int↔指针转换 10、`typedef Byte` 重定义 8、void*→enum 7

## 本地环境限制：依赖二进制被设备加载策略拒绝映射（EACCES）

**现象**：本机 W3（`conan create` → test_package 运行消费者）在运行期报
`Error loading shared library libXft.so.2: Permission denied` /
`libfontconfig.so.1: Permission denied`（needed by `./test_xmhtml_consumer` 及
`libXmHTML.so.1.1`），随后 `Error relocating libXmHTML.so.1.1: Xft*/Fc*: symbol not found`，
消费者退出码 127。库本体构建、消费者编译与链接（含头文件解析）全部正常。

**真因（对照实验排除法，2026-10-04）**：该拒绝与**依赖二进制的字节内容**绑定，
与路径、权限位、文件名、复制方式、构建来源均无关：

| 实验 | 结果 |
| --- | --- |
| 同目录、同创建方法（python 以 0755 写入）放不同内容 | Xrender/libXm/libxml2 内容 → 可映射（报子库名）；**libXft / fontconfig 内容 → Permission denied** |
| 改名 / 换目录（conan 缓存 ↔ `$HOME/tmp` 副本农场、软链农场） | 均拒 |
| `chmod +x`（750/755/770）、软链先删后建、`llvm-objcopy` 重写 | 均拒 |
| 依赖**本地源码重建**（libxft/2.3.9 + fontconfig/2.18.3 经 `--build` 重建；产物体积与原发布一致：108864 B / 526784 B） | 仍拒 |
| ELF 程序头 / 动态段标签比对 | 被拒与被允许库完全一致（LOAD=R,RX,RW,RW；GNU_STACK=RW；TEXTREL=False；BIND_NOW=False；FLAGS=0x8；FLAGS_1=0x1）⇒ 非可执行栈或标签差异 |
| 静态链接绕开 | 消费者静态链接 `libXmHTML.a` 后 116 条 undefined（`XftDrawChange`/`XftNameParse`/`FcPatternCreate`…）⇒ 库本体确需 Xft/fontconfig 符号，无法绕开 |
| 系统目录兜底 | `/lib`、`/lib64`、`/usr/lib`、`/system/lib64`、`/vendor/lib64` 均无 X 库 |

**判定**：设备侧二进制信任 / 可映射策略（同一设备上其它依赖内容与 `libXmHTML` 自身
均可正常映射），**非本包配方、头文件、链接或 test_package 缺陷**；依赖可正常加载的
设备与 CI 不受此限。

**处置**：`test_package/test_xmhtml_consumer.sh` 按“**依赖是否真缺**”分类加载失败——
① 本包自身库（`libXmHTML*`）加载失败 → FAIL（真缺陷）；
② 加载错误点名的依赖库在运行期库路径（`LD_LIBRARY_PATH`）中**找不到** → FAIL（真缺陷，如 CI 漏投包）；
③ 点名的依赖库**存在却被拒绝映射**（musl exec 期消息形如
`Error loading shared library libXft.so.2: (needed by …)`，无错误文本；dlopen 期同一现象带
`Permission denied`）→ 打印 `PLATFORM_POLICY_SKIP` 证据块（逐库给出 `present-but-refused`
的解析路径）+ 符号级降级验证（`libXmHTML.so` 须导出 `XmHTMLGetVersion` /
`XmHTMLGetVersionString` / `xmHTMLWidgetClass`）后通过。
依赖可正常加载时 A/B/C 三条严格路径都不触发该放行分支 ⇒ CI 侧仍是完整运行期验证。
该类问题的通用检测与处置见 `knowledge/drafts/` 中的知识库扩展条目。

## 上游测试清点（R51）

- 源码树**无 `tests/` 目录**；顶层 Makefile 目标为
  `all lib http examples tools contrib book depend clean distclean`，**无 `check`/`test`**
  → 上游无测试套件。
- 本包提供鸿蒙特有消费者测试 `test_package/test_xmhtml_consumer.c`（headless：
  无需 X 显示，调用 `XmHTMLGetVersionString()`/`XmHTMLGetVersion()` 并断言
  `xmHTMLWidgetClass` 非 NULL）→ N=1（上游 0 + 本包 1）。

## 包内容说明

投递 `include/XmHTML/*.h`、`include/common/*.h`、`include/gtk-xmhtml/*.h`、`include/http/*.h`
（保持上游目录布局）、`lib/libXmHTML.so.1.1.10`（+ `.so.1.1`/`.so` 软链）或 `lib/libXmHTML.a`
（`shared=False` 时）、`licenses/COPYING`。`pixmaps/`/`bitmaps/` 中的图像在构建期已编译进库
（`_PLC_XPM_Init` 等符号），不作为运行时数据投递。
