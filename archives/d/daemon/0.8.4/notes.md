# daemon 0.8.4 适配笔记

## 概述
daemon（https://libslack.org/daemon）是 raf 编写的命令行工具，将其他进程转换为 Unix 守护进程
（处理 setsid、pidfile、respawn、信号、pty、syslog 重定向等细节），便于用 shell/Java 等非 C 语言
编写守护进程。内部链接内置的 libslack 静态库。许可证 GPL-2.0-or-later。

## 构建系统
- raf 自定义 Makefile + `./configure` 平台探测脚本（非 autotools、非 cmake）。
- `./configure` 通过 `uname` 识别平台并调用 `conf/<platform>`（用 `perl -pi` 改写
  Makefile / macros.mk / config.h）；`--platform=Linux` 可跳过 uname 直接走 Linux 分支。
- `make` 默认目标构建 `libslack/libslack.a` 与 `./daemon` 可执行文件。
- 链接关系：`$(CC) -o daemon daemon.o -Llibslack -lslack -lpthread -lutil`。

## 平台适配要点

| # | 要点 | 处理 |
|---|------|------|
| 1 | Makefile 用 `CC := gcc` / `AR := ar` / `RANLIB := ranlib`（`:=` 立即赋值，忽略环境） | 在 `make` **命令行**传 `CC/AR/RANLIB` 覆盖（命令行变量覆盖 `:=`）；取值来自 Conan conf（R33），OHOS worker 无 `cc/gcc/ar` 符号链接 |
| 2 | 链接 daemon 可执行文件时 OHOS SDK 默认 lld 依赖 `libxml2.so.16`（系统缺失，E120/E132） | `LDFLAGS=-fuse-ld=/data/service/hnp/bin/ld` 改用 GNU ld |
| 3 | HarmonyOS 执行二进制需 ELF 签名（E082），否则 test_package 运行报权限错误 | package() 阶段 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool ... -selfSign 1` |
| 4 | musl 提供 `libutil.so`（packaging.md 明确列出），`-lutil`（openpty 等）可正常链接 | 无需补丁 |
| 5 | 0.8.4 已内置 musl 支持（`<sys/ttydefaults.h>` 提供 CEOF，Baruch Siach 贡献） | 无需补丁 |
| 6 | `make install` 依赖 pod2man 生成 man 页且会 strip 二进制 | 改为 package() 手动拷贝 `daemon` 二进制，规避 pod2man/strip 依赖 |

## 实际构建命令
```
sh ./configure --platform=Linux --disable-logind --disable-mail-test
make -j1 CC=/data/service/hnp/bin/clang \
        AR=/data/service/hnp/bin/llvm-ar \
        RANLIB=/data/service/hnp/bin/llvm-ranlib \
        LDFLAGS=-fuse-ld=/data/service/hnp/bin/ld
```
- `--disable-logind`：OHOS 无 systemd-logind，禁用 `--bind` 选项依赖。
- `--disable-mail-test`：排除上游测试中的发信逻辑。

## 上游测试
- `test/` 下 test1–test70 为**人工观察型**集成测试。`test/README` 明确指出：这些测试不自检行为，
  多数向 syslog 发消息需人工查看，部分需 root 或交互终端（pty 窗口缩放等），无自动化 pass/fail 机制。
- `make check` / `make test` 触发的是 `test-slack`（编译并运行 libslack 单元测试二进制），与 daemon 工具本身无关。
- 本配方 build() **不**跑 `make check`（避免人工/平台相关的集成测试在 CI 抖动），
  改由 test_package 以**执行 daemon 二进制**的方式做真实验证（满足 R34）。

## test_package 验证内容
- `daemon --version`：验证二进制可执行、ELF 已签名、链接 libc/pthread/util 正常。
- `daemon --noconfig --unsafe --foreground -- sh -c 'echo ... > marker'`：
  以**前台模式**同步启动一个客户端进程并写标记文件，验证 daemon 的核心客户端派生与 stdout 透传能力
  （`--foreground` 下客户端输出透传到 daemon 的 stdout/stderr，见 daemon.c 文档第 579 行）。

## 依赖
- 无外部 Conan 依赖；pthread/util 由 musl 提供，libslack 为源码内置静态库。

## 风险与未决项
- 本机无鸿蒙构建环境，以上为基于源码分析与知识库（E081/E082/E120/E132）的配方推断，交由 CI 真实鸿蒙
  worker 验证。重点关注：lld/libutil 是否如预期、`llvm-ar`/`llvm-ranlib`/`ld` 路径在 worker 上是否一致、
  `/bin/sh` 是否可用于前台客户端测试。若有偏差，按 CI 日志在下一轮调整。
