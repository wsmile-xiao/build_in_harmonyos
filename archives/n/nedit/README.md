# NEdit

> Motif/LessTif 界面的 X11 多用途文本编辑器，附带用于驱动已运行实例的 `nedit-nc` 客户端。

## 简介

NEdit（Nirvana Editor）是面向 X Window System 的老牌图形化文本编辑器，使用
Motif 工具包（本仓库依赖 `motif/2.3.8`，即 `libXm.so.4`）。它以"编辑器即
程序员的瑞士军刀"为目标：C/C++/Fortran/HTML 等多语言语法着色、正则查找替换、
宏语言（内置解释器可写脚本并绑定快捷键）、多窗口/多标签、标签文件（ctags）
跳转、shell 命令集成、打印队列集成。

上游一个源码包产出两个可执行文件：

- `nedit` —— 图形编辑器本体；
- `nc` —— X 客户端，把文件/命令行通过 X 属性发给已经运行的 nedit 实例
  （Debian 把它改名安装为 `nedit-nc`，避免与 netcat 的 `nc` 冲突；本包沿用该
  改名）。

上游不使用 autotools/CMake，只有一套手写 makefile：顶层 `Makefile` 是分发器，
`makefiles/Makefile.<平台>` 提供平台变量，四个子目录各自的 `Makefile.common`
列出目标。NEdit 5.8 于 2026 年发布，仍是 GPL-2.0-or-later 的自由软件。

## OHOS 适配要点

1. **不使用顶层 `make <platform>`。** 它的最后一步是 `@source/nedit -V`——执行
   刚刚链接出来的二进制。在 `conan create` 里这必然失败（新链接的 `nedit` 没有
   指向 Conan 提供的 `libXm.so.4` 的 rpath）。配方复刻分发器的前半段（把
   `makefiles/Makefile.linux` 拷进四个子目录），然后按依赖顺序直接驱动四次子
   make。
2. **必须 `-DUSE_DIRENT`。** `util/printUtils.c` 在没有该宏时包含
   `<sys/dir.h>`；glibc 至今保留这个兼容垫片，musl（以及 OHOS）没有，会报
   `'sys/dir.h' file not found`。发行版的 `debian/rules` 可以省掉这个宏，照抄它
   的 CFLAGS 到 OHOS 上不行。
3. **`source/parse.c` 是生成文件。** 上游提供的官方回退是
   `cp source/parse_noyacc.c source/parse.c`；配方在构建前完成这次拷贝，worker
   上不需要 bison 或 yacc。
4. **不定义 `-DHAVE__XMVERSIONSTRING`。** 定义它以后 `source/help.c` 会
   `extern char _XmVersionString[]` 并依赖 libXm 导出这个私有符号；不定义时
   help.c 使用自带的 `static char _XmVersionString[] = "unknown"`，没有任何额外
   链接依赖。本包依赖的 Motif 2.3.8 被 `util/motif.c` 判定为
   `MotifKnownGood`（`XmFullVersion == 200308`），因此也不需要 Debian 的
   `-DBUILD_UNTESTED_NEDIT`。
5. **解压得到的 `nedit` / `nedit-nc` 需要签名。** 未签名的 ELF 无法从 Conan 包
   缓存执行（OHOS 上表现为 PermissionError），`package()` 会用
   `binary-sign-tool -selfSign 1` 补 `.codesign` 段。
6. **手册页额外生成，且是尽力而为。** 上游默认构建刻意不含 `docs` 目标
   （"用户可能没装 Perl"），`make -C doc man VERSION="NEdit 5.8"` 需要
   `pod2man`（一个 Perl 脚本），产物是 `nedit.1` 与 `nedit-nc.1`。配方以
   `ignore_errors` 运行这一段：worker 上没有 Perl 时少两个 man page，但两个
   编辑器仍然完整产出。

## 排除与替代

- **`nc`**：上游的 `nc` 是 NEdit 的 X 客户端，**不是** netcat。本包把它安装为
  `nedit-nc`，`bin/` 下不存在 `nc`，因此不会与系统的 netcat 冲突。需要 netcat
  请另行安装。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| motif | 2.3.8 | `libXm.so.4` 与 Motif 公开头文件（`Xm/Xm.h` 等） |
| libx11 / libxt / libxext / libsm / libice | 由 motif 传递 | X11 客户端库；`libXm.so.4` 的 DT_NEEDED，运行时必须可解析 |
| xorgproto | 由 motif 传递 | X11 协议头（编译期） |

`motif/2.3.8` 以 `transitive_headers=True, transitive_libs=True` 声明了上述
X11 栈，因此本配方只声明一条依赖边。

## 功能验证

```bash
# 版本信息（-V 与 -version 都会在 XtOpenDisplay 之前应答，无需 X 服务器）
nedit -V
nedit-nc -V

# 图形界面（需要可用的 X 显示）
nedit /tmp/example.txt
```

包内还提供 `share/X11/app-defaults/NEdit`（应用资源默认值），以及
`share/man/man1/nedit.1`、`share/man/man1/nedit-nc.1`（worker 上存在
`pod2man` 时）。使用 Conan 运行环境时 `XAPPLRESDIR` 与 `PATH` 会被自动指向
包内对应目录。

## 参考

- [官方项目页](https://sourceforge.net/projects/nedit/)
- [源码下载](https://sourceforge.net/projects/nedit/files/nedit-source/)
