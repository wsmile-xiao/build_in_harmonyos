# clex 4.6.patch8 适配笔记

## 编译环境
- 构建系统: autotools（发行包自带 autoconf 2.69 生成的 configure，无需 autoreconf）
- 编译日期: 2026-09-09
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built

## 编译步骤

1. 原生探索构建（harmonybrew ncursesw 头与库可用）：
   - `./configure --prefix=$DEFAULT_PREFIX CPPFLAGS="-I.../include/ncursesw -I.../include" LDFLAGS="-L.../lib"`（E011：先 sed `umask 077→022`）
   - `make -j2 && make install DESTDIR=$TEST_PREFIX && make check`（无 TESTS 注册，空跑 exit 0；上游另有需 TTY 的 `kbd-test` 工具）
2. Conan 配方（conanfile.py build()）：
   - 依赖 `ncurses/6.5`（AC_SEARCH_LIBS addwstr 硬性探测；extra_cflags/extra_ldflags 指向包目录，alpine/2.26 同款接线）
   - E011 umask 修复内置配方（OHOS 与 CI worker 同为 HMDFS 类环境）
   - 发行包 configure 无 AC_CANONICAL_HOST、无 config.guess/config.sub，无需三元组补丁

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "can't create ./conf*/subs1.awk: Permission denied" | E011/E114：HMDFS mktemp 临时目录 umask 077+setgid 不可写（configure 为 autoconf 2.69 生成，umask 077 型；无 ac_tmp 模式） | 配方 build() 内 sed `umask 077→022`（E011 方法 2，探索构建与配方同法） |
| 2 | 探索阶段 configure 报 "no acceptable C compiler found" | 老版 AC_PROG_CC 只搜 gcc/cc/cl.exe，设备 PATH 无 cc 且 autoconf 不搜 clang | 探索阶段 `export CC=clang`；配方中 toolchain 显式提供编译器 |
| 3 | 上游站 clex.sk HTTPS 证书主机名不匹配且 /download/ 已下线 | 站点 stub 化（只剩 GitHub 链接），GitHub 仓库无 4.6.patch8 tag | 源码取自 archive.ubuntu.com pristine orig.tar.gz，与 Debian clex_4.6.patch8-1.dsc Checksums-Sha256 逐字节一致（决策链记录于 conandata.yml 注释） |

## 源码修改

无源码补丁（patches/ 为空）。E011 修复作用于 configure 的构建期 sed，非源码树变更。

## 依赖版本

- 运行依赖：ncurses/6.5（宽字符 curses，制品仓已发布，conan download 核实）
- 构建工具依赖：无（发行包自带 configure，CI 无需 automake/libtool）

## 验证结果

上游测试（设备原生 automake harness）：

```text
make check: exit 0；"Nothing to be done for 'check-am'"
上游静态测试数 = 1：`src/kbd-test.c` 是上游交付的独立交互式键盘排障测试工具（ChangeLog 明确说明其用途）。
上游自动化注册/执行数 = 0/0：Makefile.am/src/Makefile.am 无 TESTS 注册，`make check` 为空跑；`kbd-test` 需要真实 TTY 和双 Ctrl-C，故在无头 CI 中跳过 1 项。
```

说明：上游没有 automake 自动化测试，但存在 1 个需终端交互的上游测试工具；消费者测试
test_package（test.c）1 个：cfg-clex 迁移正路径（rc=0 + 配置文件迁移断言）+ clex
headless 真实启动（ncurses 加载 + EOF 正常退出，rc=0）。`kbd-test` 不在消费者测试中
强行模拟，避免把交互程序的静态存在误报成已执行。

## 注意事项

- 上游为交互式 curses 全屏程序：headless 环境下按 EOF 正常退出（实测 rc=0），断言以此为准；交互功能路径无法在 CI 无终端环境运行（如实列明，非掩饰）。
- cfg-clex 为包交付的 /bin/sh 脚本（dist_bin_SCRIPTS），其迁移正路径是包功能的一部分，作为消费者测试断言对象。
- R38：tool 类型，软件级 commands.json 已声明 clex/kbd-test/cfg-clex。
---

**编译结束**: 2026-09-10 23:31
**最终状态**: built
