# gnuspool 1.8 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 configure，非 CMake）
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15（OHOS SDK，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 配方内实际执行（conan create，profile ci/conan/profiles/ohos-aarch64）
# 1) 源码复制到浅层目录（HMDFS 深层 conan 缓存目录下 config.status 不稳）
cp -r <source_folder> ~/tmp/uc2/gnuspool-build-1.8
# 2) configure 前：移除 configure 内 umask 077 包裹（E011/E114）、
#    替换 SysV shm/msgq 的致命 AC_TRY_RUN 分支为保守回退（--enable-using-mmap/flock）
# 3) configure：显式传 CCFLAGS/LDFLAGS（gnuspool 的 Makefile 只认 CCFLAGS，
#    且子目录链接规则无 LDFLAGS）
CC=clang CXX=clang++ \
CCFLAGS="-O -g -Wall -fno-stack-protector -D_GNU_SOURCE -DHAVE_TERMIO_H \
         -DSIGCLD=SIGCHLD -fcommon -I<ncurses>/include -L<scratch-lib> -L<ncurses>/lib" \
LDFLAGS="-L<scratch-lib> -L<ncurses>/lib" LIBS="-lcurses" \
sh configure --build=aarch64-unknown-linux-gnu --enable-using-mmap --enable-using-flock \
             --without-network --prefix=<package_folder>
# 4) 配方在 configure 前改写 10 个 Makefile.in：去掉对宿主 libtool 的依赖
#    （CI worker 的 PATH 里没有 libtool；详见下方问题 5 与配方级说明）
# 5) make -j1（同上 CCFLAGS/LDFLAGS）
# 6) 暂存产物：可执行文件 → bin/，*.so* → lib/（可执行文件 RUNPATH 指向 <prefix>/lib）
# 7) 打包：另拷 src/helpmsg/*.help → share/gnuspool/help/（否则工具报
#    "Cannot find help message file ... Maybe installation was not complete?"）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pmenu.c: fatal error: 'curses.h' file not found` | gnuspool 的 Makefile 把 include 目录拼进 **CCFLAGS**（不认 CPPFLAGS/LDFLAGS）；子目录链接规则亦只用 CCFLAGS | 同时给 configure 与 make 传 `CCFLAGS=-I<ncurses>/include -L<...>`（ncurses 包里 libncurses.a 需要别名为 libcurses.a 以配合 `-lcurses` 探测） |
| 2 | `gspasswd.c: l64a/getpass undeclared` → implicit int → 类型错误 | musl/OHOS libc 不提供 l64a（E213）与 getpass（E093） | 沿用源码内 `#ifdef OS_FREEBSD` 回退块并把守卫扩展到非 glibc；补 getpass 的 fgets 等价实现（patches/0001） |
| 3 | `helpparse: Unable to link src/gtk/xspq.menu to build/gtk/xspq.menu`（exit 27） | HMDFS 不支持硬链接（`link()` 返回 EPERM） | helpparse 的 link() 失败退化为文件复制（patches/0002） |
| 4 | 多个文件 `hostent` 不完整 / `in_addr_t` 未定义 | musl 不再由其他系统头传递引入 `<netdb.h>`/`<netinet/in.h>` 等 | 在 gnuspool 自己的可移植头 `src/hdrs/incl_unix.h` 显式包含（patches/0003，一处覆盖全部） |
| 5 | 设备上能构建、CI 却失败：`make[2]: libtool: No such file or directory`（Error 127） | 上游 Makefile 直接调用裸 `libtool`；设备 shell 的 PATH 含 `~/.harmonybrew/bin`（有 libtool），CI worker 的 PATH 不含 → 配方隐式依赖了手工安装的宿主工具 | 配方在 configure 前改写 10 个 Makefile.in：`$(CC) -fPIC -shared` 直接产出共享库（`-Wl,-soname`/`-Wl,-rpath` 补回 libtool 原本提供的 soname 与 rpath），并把上游引用的 libtool 专有产物路径（`.lo`、`.libs/libgnuspool_int.a`）改指真实产物；install 目标去掉 `libtool --mode=install` 前缀。构建系统级改写归配方，不进源码补丁集 |
| 6 | `setkey.c: fatal error: 'termio.h' not found`、`getpass`/`sgttyb`/`TIOCGETP` 未定义 | musl 无 `<termio.h>`/`<sgtty.h>`；源码用 `HAVE_TERMIO_H` 选择 termios 路径，musl 下该宏未定义而落入 BSD 老 API | 配方 CCFLAGS 加 `-DHAVE_TERMIO_H`；补丁把 `<termio.h>`/`<sgtty.h>` 分支重定向到 `termios.h` 并定义 `TCGETA→TCGETS`、`TCSETA→TCSETS`、`termio→termios`（patches/0004，10 个文件） |
| 7 | `spshed.c: use of undeclared identifier 'SIGCLD'` | musl 不提供 System V 别名 SIGCLD | CCFLAGS 加 `-DSIGCLD=SIGCHLD` |
| 8 | `ld.lld: error: undefined symbol: vportnum` | `sh_network.c` 整体在 `NETWORK_VERSION` 宏内，`--without-network` 下未编译，而 `sh_queue.c` 的 `js_viewport` 赋值未加保护 | 该赋值加 `#ifdef NETWORK_VERSION` 保护，否则记 0（patches/0005） |
| 9 | `undefined reference due to --no-allow-shlib-undefined: nomem` | 库成员引用的 `nomem()` 定义只在未参与本次构建的 `src/gtk`、`src/ins` 源文件中 | 在库成员 `src/lib/extdefs.c` 补库内定义（patches/0006） |
| 10 | `inline/jfmt_origh.c: use of undeclared identifier 'HT_ROAMUSER'` | 该片段未包含 `src/hdrs/network.h`；且 `HT_*` 标志定义在该头的 `NETWORK_VERSION` 守卫内 | 补 `#include "network.h"` 与同名回退定义（patches/0007） |
| 11 | `ld.lld: error: duplicate symbol: progname` | clang 15 默认 `-fno-common`，老代码的暂定定义冲突 | CCFLAGS 加 `-fcommon` |
| 12 | 运行随包工具报 `Error relocating gspl-pq: print_error: symbol not found` | 可执行文件 RUNPATH 指向 `<prefix>/lib`，而配方把 `.so` 暂存在 `bin/` | 打包改为 `*.so* → lib/`，`package_info.libdirs = ["lib"]`（conanrun 的 LD_LIBRARY_PATH 覆盖运行期查找） |
| 13 | 工具报 `Cannot find help message file .../share/gnuspool/help/spq.help` | 打包只含二进制，缺 help 数据 | package() 增拷 `src/helpmsg/*.help → share/gnuspool/help/` |

## 源码修改

| 补丁（refresh-patch 按文件生成） | 内容 |
|------|------|
| patches/0001-src-hdrs-incl_unix.h.patch | musl 网络头不再传递包含：公共头显式包含 sys/socket.h、netinet/in.h、arpa/inet.h、netdb.h |
| patches/0002-src-inline-jfmt_origh.c.patch | inline 片段补 network.h 与 HT_ROAMUSER 回退定义 |
| patches/0003-src-ins-netwcmd.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0004-src-lib-extdefs.c.patch | 库成员 extdefs.c 内补 nomem() 定义 |
| patches/0005-src-lib-getkey.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0006-src-lib-setkey.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0007-src-lpdint-sp.lpq.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0008-src-sd_bann.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0009-src-sd_fctrl.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0010-src-sd_initf.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0011-src-sdi_gram.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0012-src-sh_queue.c.patch | js_viewport 赋值加 NETWORK_VERSION 保护（--without-network 下 vportnum 未定义） |
| patches/0013-src-spd.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0014-src-spdinit.c.patch | musl 无 <termio.h>/<sgtty.h>：改用 termios.h 与 Linux 风格 ioctl 号（TCGETA→TCGETS、TCSETA→TCSETS、termio→termios） |
| patches/0015-util-gspasswd.c.patch | musl 缺 l64a/getpass（E213/E093）：扩展源码内 FreeBSD 回退块守卫并补 getpass 等价实现 |
| patches/0016-util-helpparse.c.patch | HMDFS 不支持硬链接：helpparse 的 link() 失败退化为文件复制（含 #include <fcntl.h>） |

（上游 Makefile.in 的构建系统改写——去宿主 libtool——属于配方级处理，见下）

配方级（非源码补丁）：configure 的 umask 077 移除、SysV shm/msgq 探测回退、
10 个 Makefile.in 去宿主 libtool 改写（configure 前）、源码浅层复制构建。

## 依赖版本

- ncurses/6.6（制品仓已发布，静态库；工具 spq/pmenu 等需要 curses）

## 验证结果

```bash
# 设备（真机）执行
export CONAN_HOME=~/tmp/ch/home-glm49-gnuspool
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 结果：构建 + 打包 + test_package 全部通过
# test_package：以使用者身份运行随包发布的 gspl-cjlist，断言用法输出并检查
#   help 数据可被工具找到（真实执行被测二进制）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/gspl-*、dosspwrite、spcgi 等 | — | 随包发布的命令行工具（约 25 个） |
| lib/libgnuspool_int.so*、libgnuspool_curs.so* | — | 运行期共享库（可执行文件 RUNPATH 指向该目录） |
| share/gnuspool/help/*.help | — | 工具运行期所需的帮助/消息数据 |

## 注意事项

- 本包按 `--without-network` 构建（网络复制/远程打印功能未启用），需网络能力的
  用例不适用于本适配；如后续需要，须先完成网络相关代码的 musl 适配。
- 构建必须在浅层可写目录进行（HMDFS 深层目录下 config.status 不稳定）。
- 工具为传统终端工具，不支持 `--version`；`--help`/无参数行为随工具而异
  （例如 gspl-cjlist 无参数打印用法并以 100 退出）。
## 对话记录

### 对话 #1（2026-09-17，GLM-49）

- 交接背景：接手 GLM-33/GLM-43 的【交接】半成品（conan-verify G2 FAIL：）。
- 处理要点：逐轮以第一条真实错误为线索推进，共 13 类问题（ncurses include 走 CCFLAGS、
  l64a/getpass、helpparse 硬链接、musl 网络头、libtool --tag、termio/sgtty、SIGCLD、vportnum、
  nomem、HT_ROAMUSER、-fcommon、.so 归 lib、打包 help 数据），落 7 个源码补丁。
- 编译结果： 构建 + 打包 + 消费者测试通过； G0–G4 全 PASS；
   成功（含 W3 本地 CI 模拟通过）。
- 遇到的问题与解决：见上文「遇到的问题与解决方案」表（13 行）与「源码修改」（7 个补丁）。
- 耗时：约 5 小时（含每轮约 8 分钟的构建迭代）。
### 对话 #2（2026-09-19，GLM-49）

- 背景：PR #10775 的 CI 在 `conan-build-test` 失败，报 `make[2]: libtool: No such file or directory`。
- 定位：不是缺少上游依赖（`ncurses/6.6` 解析、下载、安装均正常），而是 CI worker 的 PATH 里
  没有宿主 `libtool`；设备上因为有 `~/.harmonybrew/bin/libtool` 而看不出问题。
- 处置：把 libtool 改写做成配方级步骤（build() 内 configure 前改写 10 个 Makefile.in），
  彻底去掉对宿主 libtool 的依赖；源码补丁集交给 refresh-patch 按文件管理（16 个）。
- 验证：设备 `conan create` 全流程通过（构建 + 打包 40 个 ELF + 消费者测试 PASS）。
---

**编译结束**: 2026-09-19 01:51
**最终状态**: built
