# sysnews 0.9-ds.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-30
- 编译器: NDK clang (aarch64-unknown-linux-ohos)
- 状态: built
- 语言预检: `detect_language` = c（build_system=make，源文件 2 个 c:2，主体 100%），与任务语言 cpp 同属 C/C++ 兼容族，预检放行
- 源码: Debian `sysnews_0.9+ds.1.orig.tar.gz`（顶层目录 `sysnews-0.9+repack/`，sha256 `8d438a2e…0733`）。README 记载的原站 link.xs4all.nl 本次探测无响应，Debian orig 包是可获取的权威分发源；版本号沿用任务书 `0.9-ds.1`

## 编译步骤

1. `make CC=<ohos clang> CFLAGS='-Wall -O2'` 直接构建 `news` 与 `news.1`（CC 由 conan `tools.build:compiler_executables` 取得，不依赖 shell 变量）。
2. 上游 `make install` 用 `install -o bin -g bin`（需要 root）且无 DESTDIR，配方 `package()` 直接复制 `news`→`bin/`、`news.1`→`share/man/man1/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 上 `news -a` / `-d` 段错误，而编译仅有 implicit-function-declaration 告警 | news.c 未包含 `<time.h>`，`ctime`/`gmtime`/`time`/`strftime` 被隐式声明为返回 `int`，LP64 上指针被截断 | 补丁 `0001-news.c.patch` 增加 `#include <time.h>`（无平台宏） |
| 2 | 静态重链验证时 `duplicate symbol: opterr` | 上游自带 getopt.c 与 musl libc.a 的 getopt 冲突 | 仅影响本机 qemu 验证：重链加 `-Wl,-z,muldefs`；动态链接交付物不受影响，无需改源码 |

## 源码修改

- `patches/0001-news.c.patch`：news.c 增加 `#include <time.h>`（portability，非平台专属）。

## 上游测试清点（R51）

上游仅 Makefile + 3 个 C 源文件 + README + man，无 `check`/`test` 目标、无 tests 目录、无 ctest/pytest 注册：上游测试 N=0，N′=0。补充由 `test_package` 提供真实功能测试（见下）。

## 已知上游缺陷（不修，未改变行为）

- `SYSNEWSFLAGS` 环境变量路径：`read_sysnews(argc, argv)` 用原始 argv 与合并后的 optind 取 `argv[optind]`，越界读取；test_package 不覆盖该路径。
- `-P` 不在 getopt 短选项串中（`--pager=` 长选项可用）；`-p` 通过 popen 调用 `/bin/sh`，OHOS 上 `/bin/sh` 是否存在未验证，test_package 不覆盖。
- `do_expire` 里 `.noexpire` 的 `continue` 只作用于内层循环，排除列表实际不生效。

## 验证结果

- 本机 qemu-aarch64（E544：同源 `.o` 用 `-static-pie -Wl,-z,muldefs` 重链，PIE 才会复现指针截断）：
  - 无补丁：`test_package/test.sh` 在 `[4] -d` 段错误（`qemu: uncaught target signal 11`），rc=1
  - 有补丁：`ALL PASS`，rc=0（14 项断言 + C 校验器）
- 这是同源 `.o` 静态重链副本的实跑，**不等于**交付的动态产物已在 OHOS 上实跑；动态产物由 CI `conan create` 的 test_package 执行。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/news | news 命令 |
| share/man/man1/news.1 | man 手册（已按 NEWSDIR/NEWSTIME 替换） |

## 注意事项

- 默认新闻目录 `/var/sysnews`（编译期 `NEWSDIR`），运行时可用 `-f DIR` 指定。
- 源 URL 为 Debian orig 包（PF7 已知命中项，登记于 PR 正文）。
