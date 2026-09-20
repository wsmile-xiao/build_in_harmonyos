# nyancat 1.5.2 编译笔记

## 软件简介
nyancat（Terminal Nyancat）在终端里渲染经典的"彩虹猫"动画帧，支持
standalone 模式（`nyancat`）与 inetd 风格 telnet 服务端模式（`nyancat -t`，
fd 0 上解析 telnet 协议）。纯 POSIX C99，零外部依赖。

## 编译过程

### 源码获取
- 来源: GitHub klange/nyancat（上游 README/版权头的 canonical 地址）
- URL: https://github.com/klange/nyancat/archive/refs/tags/1.5.2.tar.gz
- SHA256: 88cdcaa9c7134503dd0364a97fa860da3381a09cb555c3aae9918360827c2032
  （本地 tarball 实测值，与首次适配记录的 .tarball-sha256 一致）
- tarball 共 14 项：Makefile、src/{Makefile,nyancat.c,animation.c,telnet.h}、
  nyancat.1、systemd/{nyancat.socket,nyancat@.service}、README.md、CHANGELOG、.gitignore

### 构建系统
- **类型**: 两级手写 Makefile（非 autotools/cmake/meson），无 configure 脚本
- 顶层 Makefile 仅做 `cd src && make $@` 转发；真实构建在 src/Makefile
- 全部变量用 `?=` 声明（CC/CFLAGS/CPPFLAGS/LDFLAGS），命令行可覆盖 → **零补丁**
- 上游默认 CFLAGS：`-g -Wall -Wextra -std=c99 -pedantic -Wwrite-strings`，
  OHOS clang 下全部通过，未做改动（保留上游语义）
- 源码规模：nyancat.c 913 行 + animation.c 818 行（纯字符串帧数据）+ telnet.h 82 行（纯宏）

### 依赖处理
- **零外部依赖**。src/nyancat.c 全部 include 逐项清点：
  ctype/stdio/stdint/string/stdlib/unistd/signal/time/setjmp/getopt/sys/ioctl/termios
  —— 全部 libc；telnet 模式纯 stdio（无 socket 调用）；上游注释明确拒绝
  libm（"I refuse to include libm to keep this low"，src/nyancat.c:140）
- L0i 依赖检查：依赖清单为空，天然通过，无前置依赖 PR

### HarmonyOS 适配点（均为配方层，无源码补丁）
| 项 | 处理 | 根因 |
|----|------|------|
| CC | `make CC=<conan conf clang>`（R33） | CI worker 的 shell 环境 CC/CFLAGS 为空，必须从 Conan conf 取 |
| 并行度 | `make -j1`（R9） | HMDFS 上 make jobserver 管道对象可能不可用；单 C 文件，-j1 无性能损失 |
| make clean | build() 起始执行 | tarball 虽不含 .o（14 项清点确认），但保留 clean 保证重构建可复现 |
| telnet.h ECHO 宏 | 不处理 | 与 stdio ECHO 标志冲突，上游已在 include termios.h 后 `#undef ECHO`，OHOS 无需修复 |
| TIOCGWINSZ ioctl | 不处理 | OHOS musl 支持；无 TTY 时 ioctl 失败走默认宽度 80 的优雅降级路径 |
| systemd 单元 | 不打包 | OHOS PC 无 systemd；install target 硬编码 /usr（无 DESTDIR），package() 手动 copy（netris 先例） |
| HMDFS /tmp | 无影响 | Makefile 不写临时文件；无 configure → 无 E0111 umask-077 生成脚本问题 |

### 测试
- 上游无测试套件：src/Makefile 的 `check:` 目标 = `all` + `@echo "*** ALL TESTS PASSED ***"`
  （注释 "Unit tests go here. None currently."），真实可运行用例 0 个
- 条件编译清点：全源码 #if/#ifdef 仅 3 处（TIOCGWINSZ 头回退、ECHO undef、头文件 guard），
  无 win32/平台专属测试分支
- PR 声明口径：upstream_tests = 0；test_package 补 3 条冒烟断言（见 test_package/MANIFEST.yml）
- 本地实测：`nyancat -e -f 1` 无 TTY 管道运行 exit 0，stdout 含帧字符与计数行
