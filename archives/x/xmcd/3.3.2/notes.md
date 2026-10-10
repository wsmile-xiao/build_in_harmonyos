# xmcd 3.3.2 适配笔记

## 概览

- 软件：xmcd（Motif CD 播放器/抓轨套件：`xmcd` GUI + `cda` 命令行 + `gobrowser` CDDB 浏览器）
- 上游版本：3.3.2（2006 年最后发布版；官方站 tikan.org 仅 HTTP 存活，distfile 采用 FreeBSD
  官方镜像 `pkg.freebsd.org/ports-distfiles`，sha256 与 FreshPorts 记录一致）
- 构建系统：上游 `Makefile.std`（imake 为官方主路径，OHOS 无 imake/xmkmf；README 给出 std 备选路径）
- 依赖：motif/2.3.8、libxt/1.3.1、libxext/6.4.0.1、libx11/1.8.13（force）、ncurses/6.6
  （`make.inc` 真实依赖面：`XLIBS=-lXm -lXt -lXext -lX11` + SM/ICE 传递、`CURSESLIB=-lcurses`）

## 关键缺口与处置（探索期实测）

1. **无 imake/xmkmf** → `make -f Makefile.std Makefiles` 生成各级 Makefile 后直编
   （与 xli 同一路径，见 knowledge/drafts/imake-legacy-x11）。
2. **musl 无 `<termio.h>`** → `-DUSE_TERMIOS` + 补丁 0001（`common_d/config.h` 的 `_LINUX`
   分支加 `#ifndef USE_TERMIOS` 守卫，允许从构建命令行选择 termios）。
3. **musl 未定义 HZ**（仅 `libdi_d/os_linux.c` 的 SCSI Generic `SG_SET_TIMEOUT` 路径使用）
   → 编译期 `-DHZ=100`。
4. **musl 不提供 `pthread_cancel(3)`/`pthread_setcancelstate(3)`**：libc.so 符号探测为 0；
   sysroot 的 `libpthread.a` 为空壳（0 符号），`-lpthread` 无法补齐 → 补丁 0002 引入
   `HAVE_PTHREAD_CANCEL` 特性宏：
   - `PTHR_SELF_ABORT(t)`：缺省 1 = 原语义 `pthread_cancel(t)`；`=0` 时 `pthread_exit(NULL)`
     （14 处自中止路径语义等价，语句形状保持一致，调用点无需改写）；
   - `cdda_pthr_kill()`（跨线程取消点，唯一调用者 = 心跳超时路径，其后紧随
     `cdda_pthr_stop()` 收管线）在 `=0` 时记录日志并降级为空操作。
   - 补丁内**不含平台宏**，仅特性宏（`HAVE_PTHREAD_CANCEL` 由配方命令行注入，缺省即原行为）。
5. **cda 链接需 CDDB 静态库**：`CDDBLIB='-L<src>/cddb_d -lcddb'`（`make.inc` 约定；
   探索初期覆盖为空导致 `CddbControl_*`/`CddbGetErrorString` 等未定义符号）。
6. **依赖图冲突**：motif/libxt pin `libx11/1.8.13`，libxext 自带 pin `libx11/6.4.0`
   → `self.requires("libx11/1.8.13", force=True)`（libXmu/1.3.1 既有组合先例）。

## 编译开关（配方 `build()` 实参）

```
-O2 -fPIC -I<src> -DUSE_TERMIOS -DHZ=100 -DHAVE_PTHREAD_CANCEL=0
-DHAS_ICONV_H -DHAS_NCURSES_H -D_REENTRANT
```

`XLIBS`/`CURSESLIB` 由依赖 `cpp_info` 展开（含 `-lXm -lXt -lXext -lX11 -lSM -lICE -lncursesw`），
`CDDBLIB` 指向源码内 `cddb_d`，`MATHLIB=-lm`，其余（`SOCKETLIB`/`ENCLIBS`/`AUDIOLIB`/`PTHREADLIB`）置空。

## 产物与验证（本地探索编译，2026-10-04）

- `xmcd_d/xmcd` = 940,480 B、`cda_d/cda` = 1,026,496 B、`util_d/gobrowser` = 35,200 B；`make rc=0`，
  无未定义符号。
- `llvm-objdump -p` NEEDED：`libXm.so.4 libXt.so.6 libXext.so.6 libX11.so.6 libSM.so.6 libICE.so.6 libc.so`
  （无 RPATH；运行时由 Conan RunEnv 解析）。
- 运行期（headless）：`cda -h` 打印 `cda 3.3.2 ...` 横幅与 `Usage:`；`xmcd -h` 进入显示初始化并报
  `Can't open display`（证明 Motif/Xt/X11/SM/ICE 依赖链加载成功）。

## 上游测试清点（R51）

源码树无 `tests/` 目录；`Makefile.std` 仅含 `std/sysv/gcc/sysv-gcc/Makefiles/all/install/clean/man`
目标，无 `check`/`test` → 上游无测试套件。本包提供鸿蒙特有消费者测试
（`test_package/test_xmcd_consumer.sh`，headless），N=1（上游 0 + 本包 1）。

## 包内容说明

投递 `bin/{xmcd,cda,gobrowser}` + `share/man/man1/*.man` + `share/X11/app-defaults/XMcd.ad` +
`licenses/COPYING`。上游 `install.sh` 部署期生成的 XMCDLIB 运行时支持树（docs/discog/help、
config.sh 等）不属于构建产物，未纳入包内（详见 conanfile.py `package()`）。
---

**编译结束**: 2026-10-04 13:53
**最终状态**: built
