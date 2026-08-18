# iftop 1.0_pre4 适配笔记

## 任务身份

| 身份 | 值 |
|------|----|
| 平台 | iftop 1.0_pre4（Issue #2196，分支 feat/iftop-1.0_pre4） |
| 上游 | iftop 1.0pre4（https://pdw.ex-parrot.com/iftop/，GPL-2.0-or-later） |
| 归档 | archives/i/iftop/1.0_pre4（Conan ref: iftop/1.0_pre4） |

> 版本映射：上游 tag `1.0pre4`（configure.ac AC_INIT）↔ 平台版本 `1.0_pre4`
> （下划线分隔，Conan 版本号）；归档目录与平台版本一致。

## 编译环境

- 设备: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 编译器: clang 15.0.4（Target: aarch64-unknown-linux-ohos）
- Conan: 2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64
- 依赖: ncurses/6.4 + libpcap/1.10.6（均来自 ohpcd 制品仓，静态包）

## 源码核验

- 官方 tarball: `iftop-1.0pre4.tar.gz`（204665 字节）
- SHA256: `f733eeea371a7577f8fe353d86dd88d16f5b2a2e702bd96f5ffb2c197d9b4f97`（实际下载验证）
- 语言: C；构建系统: autotools（configure + Makefile.am）
- 许可证: GPL-2.0（COPYING）
- 安装产物: sbin/iftop（autotools sbin_PROGRAMS）+ man8
- 上游测试: 无自动化测试套件（Makefile.am 无 TESTS/check_PROGRAMS 目标）

## 构建步骤（实测通过，全链路 EXIT=0）

1. `python3 scripts/ohc-run.py init-build iftop 1.0_pre4 --url=<官方URL>`
2. 应用 8 个补丁（config.guess/sub、pthread.c/iftop.c、ui_common.c/h、configure、config.h.in）
3. 依赖来自 Conan 图:
   ```
   CPPFLAGS="-I<ncurses>/include -I<pcap>/include" \
   LDFLAGS="-L<ncurses>/lib -L<pcap>/lib" \
   LIBS="-lncursesw -lpcap" \
   ./configure --prefix=/ --build=aarch64-unknown-linux-ohos \
     --sbindir=${prefix}/bin --with-libpcap=<pcap包目录>
   ```
4. `make -j1` → 生成 iftop 二进制
5. `make install DESTDIR=<staging>` → sbin/iftop + man8
6. 运行验证: `iftop -h` 输出 "iftop, version 1.0pre4"，EXIT=0

## 适配点与补丁说明（全部为平台可移植性修改）

| # | 补丁 | 问题 | 方案 |
|---|------|------|------|
| 1 | 0001-config.guess | config.guess 无法识别 HarmonyOS（E007） | 添加 HarmonyOS case 分支 |
| 2 | 0002-config.sub | config.sub 不支持 linux-ohos | OS 列表添加 linux-ohos* |
| 3 | 0003-config/pthread.c | musl/OHOS 无 pthread_cancel | 改用 flag + pthread_join |
| 4 | 0004-iftop.c | 同上（packet_loop 线程） | flag + pcap_breakloop + join |
| 5 | 0005-ui_common.c | 全局变量重复定义 | 定义移入 .c |
| 6 | 0006-ui_common.h | 头文件定义全局变量 | 改为 extern 声明 |
| 7 | 0007-configure | configure 临时目录 umask 077 在 HMDFS 不可写（E011/E214） | 077→022 |
| 8 | 0008-config.h.in | HAVE_PTHREAD_CANCEL 检测声明 | 添加 #undef，配合 #ifndef 守卫 |

- 守卫策略（AI review 修正）：`#ifndef HAVE_PTHREAD_CANCEL`，平台无该函数时走
  flag+join 路径；config.h 由 configure 生成，`/* #undef HAVE_PTHREAD_CANCEL */`。
- 未修改任何上游断言、测试数据、用例选择或 skip 条件（上游无测试）。

## 依赖说明

- ncurses/6.4: ohpcd 静态 wide-char 包（libncursesw.a）。系统存在
  libncursesw.so.6，R26 要求静态链接避免遮蔽系统库导致崩溃。
  该包不含 ncursesw.h，configure 的 curses 探测 `#include <ncursesw.h>`
  失败；conanfile.py build() 生成临时 wrapper（`#include <curses.h>`），
  仅构建作用域使用，不进包、不提交。
- libpcap/1.10.6: ohpcd 静态包；configure 用 `--with-libpcap=` 定位头文件。
- 最终二进制动态依赖仅 libc.so（ncurses/libpcap 均静态）。

## 验证结果

```bash
$ $TEST_PREFIX/.../sbin/iftop -h | tail
   -s num              print one single text output afer num seconds, then quit
   -L num              number of lines to print
iftop, version 1.0pre4
copyright (c) 2002 Paul Warren <pdw@ex-parrot.com> and contributors
```

- 上游测试: 0（无自动化测试套件，`make check` 无 TESTS 目标）
- 消费者测试: test_package/test.sh 真实执行 `iftop -h`，3 个 case 3 个断言
  （退出码 0 / synopsis 行 / 版本行 "iftop, version 1.0pre4"），实测 3/3 通过
- 编译状态: built（conan-verify 通过后由 finish 写入）
---

**编译结束**: 2026-08-16 20:09
**最终状态**: built
