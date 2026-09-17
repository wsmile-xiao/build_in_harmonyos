# unixcw 3.6.1 适配笔记

## 编译环境
- 构建系统: autotools（non-recursive automake，自带生成的 configure，无需 autoreconf）
- 编译日期: 2026-09-13
- 编译器: clang/clang++ (15.0.4 OHOS toolchain, target aarch64-unknown-linux-ohos)
- 状态: built

## 适配背景
unixcw 是摩尔斯电码（CW）核心库，产出 libcw.so + libcw.pc，是 cwdaemon 0.10.2 的唯一强制依赖（pkg-config 检查 libcw >= 5）。本适配按路径 A（基础适配）进行，属于"开源鸿蒙PC专项积分赛-依赖"任务。

## 编译步骤

1. 下载上游源码包 unixcw_3.6.1.orig.tar.gz（Debian 官方 orig 包，SHA256 见 manifest）
2. 应用 4 个 OHOS 适配补丁（见"源码修改"）
3. configure（关键参数）:
   ```
   ./configure --disable-xcwcp --disable-cwcp --disable-pulseaudio \
     --disable-oss --disable-console --disable-silent-rules
   ```
4. make -j1
5. make check（上游官方测试，层 1 测试；OHOS 上用 LOG_COMPILER + 超时 launcher 解决 E228）
6. make install + 制品收尾（移除 .la、pkg-config 相对化 prefix）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | unixcw 自带 2016 版 config.guess，无 OHOS 分支 | 0001 补丁：libc 检测加 `__OHOS__ -> ohos`，主 case 加 `*:HarmonyOS:*:* -> aarch64-unknown-linux-ohos` |
| 2 | config.sub 拒绝 linux-ohos triplet | 2016 版 config.sub 的 maybe_os / os 列表无 ohos | 0002 补丁：maybe_os 加 `linux-ohos*`、os 列表加 `-ohos*`/`-linux-ohos*`/`-linux-ohos` 分支 |
| 3 | libtool 版本化输出在 OHOS 上不可靠 | OHOS/HMDFS 对 .so -> .so.N 符号链接链不友好 | 0003 补丁：版本标志拆为可覆盖变量 `LIBCW_LIBTOOL_VERSION_FLAGS`；OHOS shared 构建时传 `-avoid-version`，产出无版本号 libcw.so（与 alsa-lib 在 OHOS 上的做法一致） |
| 4 | configure 对 textdomain 硬失败 | OHOS musl libc 无 textdomain/bindtextdomain，libintl shim 也不导出裸 textdomain 符号 | 0004 补丁：`AC_MSG_ERROR` 改为 `AC_MSG_WARN`；i18n.c 有 `HAVE_LIBINTL_H` 保护，无 libintl.h 时 `_(STR)` 退化为原样返回，功能不受影响 |
| 5 | autoconf 临时目录 umask 077 失败 | E002/HMDFS 权限语义 | conanfile build() 中 replace configure 内 `umask 077` -> `umask 022` |
| 6 | 无扩展名 libtool 测试 wrapper 无法在 HMDFS 执行 | E228 | make check 传 `LOG_COMPILER=/system/bin/sh` + 自写 launcher（超时包装脚本/ELF） |

## 源码修改

| 补丁 | 修改文件 | 内容 |
|------|---------|------|
| 0001-config-guess-ohos.patch | config.guess | OHOS libc 检测 + HarmonyOS triplet 输出 |
| 0002-config-sub-ohos.patch | config.sub | linux-ohos/-ohos 识别 |
| 0003-libtool-version-override.patch | src/libcw/Makefile.am, src/libcw/Makefile.in | 版本标志变量化（libcw.la / libcw_test.la） |
| 0004-textdomain-optional.patch | configure, configure.ac | textdomain 检查非致命化 |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| alsa-lib | 1.2.16.1 | ALSA 音频后端（唯一保留的音频输出） |
| libm / libpthread / libdl | OHOS libc 内置 | 强制系统库 |

禁用：xcwcp（Qt5）、cwcp（ncurses/curses）、pulseaudio、oss、console。

## 验证结果

（conan create 完成后回填：上游 make check 各套件通过数 + test_package 消费者用例结果）

## 注意事项

- OHOS 上 libcw.so 为无版本号输出（-avoid-version），但 libcw.pc 的 `Version: 8.0.0` 为硬编码字段，仍满足 cwdaemon 的 `libcw >= 5` pkg-config 检查。
- 构建发生在 OHOS 设备本机（os=OHOS），未使用交叉 --host 参数，依赖 config.guess 补丁自识别。
- cwdaemon 适配时直接 `requires("unixcw/3.6.1")` 即可，无需额外依赖。
---

**编译结束**: 2026-09-13 18:19
**最终状态**: built
