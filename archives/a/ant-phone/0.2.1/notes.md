# ant-phone 0.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS SDK, target aarch64-linux-ohos)
- 状态: built
- profile: ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang 15, libc++)

## 编译步骤

1. `conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
2. 源码: saveannah.nongnu.org ant-phone-0.2.1.tar.gz (sha256 已核验)
3. configure 关键参数：
   - `--build=aarch64-linux-gnu --host=aarch64-linux-ohos`（老 config.guess 不识别 OHOS）
   - `--disable-threads`（gettext intl 的 lock.h 探测 pthread_cancel，OHOS libc 无此符号）
   - `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes`（交叉编译 rpl_malloc 误判）
   - `-fcommon`（isdn_lloc/callerid_lloc 多编译单元共定义全局，clang 默认 -fno-common）
4. 编译: `make -j1`（R9 单 job）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | 2007 版 config.guess 不识别 aarch64-linux-ohos | --build/--host 显式传三元组 + autotools-dev 覆盖 config.sub |
| 2 | patch stream incomplete | 手写补丁无 context 行 | 在 patchwork 目录用 git diff 真实生成带 context 补丁 |
| 3 | configure 编译 conftest 找不到 -lsndfile | 只生成了 PkgConfigDeps，未注入 -L/-l | AutotoolsDeps(self).generate() |
| 4 | configure 找不到 -l 库、conftest 运行缺共享库 | OHOS loader 无 conan 缓存默认搜索路径 | 配方注入 LD_LIBRARY_PATH 兜底 |
| 5 | config.status: ./confBoelMf/out: Permission denied | OHOS HMDFS 下 umask 077 的 0700 临时目录不可写 | _patch_configure_tmpdir() 改为 ${TMPDIR:-.} + umask 000 |
| 6 | intl/bindtextdom.c: pthread_cancel undeclared | OHOS libc 无 pthread_cancel（gettext lock.h weak 探测） | --disable-threads |
| 7 | ant-phone.c: mcheck.h 找不到 | mcheck.h 是 glibc 私有头，OHOS musl 无 | patches/0001：仅 DEBUG 下包含 |
| 8 | duplicate symbol: isdn_lloc/callerid_lloc | lexer.c/parser.c 共定义 common 符号，clang 1 5 默认 -fno-common | extra_cflags -fcommon |
| 9 | undefined symbol: rpl_malloc | 交叉编译 AC_FUNC_MALLOC 探测默认 no | ac_cv_func_malloc_0_nonnull=yes |
| 10 | test_package: gtk_init 需显示环境 | GUI 应用 --version 在 gtk_init 后才处理 | patches/0002：--version 提前到 gtk_init 前处理 |

## 源码修改

- `patches/0001-mcheck.h-debug-guard.patch`：`#include <mcheck.h>` 包进 `#ifdef DEBUG`
- `patches/0002-version-before-gtk-init.patch`：main() 在 gtk_init() 前先处理 `--version`/`-v`，无头可冒烟

## 依赖版本

- gtk2/2.24.33（他人 PR #9854 合入，本地构建验证可消费）
- libcapi20/3.27（他人 PR #10233 合入，制品仓已发布）
- libsndfile/1.2.2、alsa-lib/1.2.16.1

## 验证结果

```bash
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# Package 'b42c7c6f0953ff9ce853d474f0d11d51b98fc787' created
# [test] ant-phone --version
# OK: --version returns ANT 0.2.1
```

## 注意事项

- 该 GNU Savannah 项目（2008 年发布）为 GTK2 ISDN 电话 GUI 应用，无上游自动化测试
  （无 make check/TESTS/check_PROGRAM/test 目录）；test_package 以 --version 无头冒烟
  作为消费者用例。
- 真机 ISDN 通话/ALSA 录音需 CAPI 硬件与显示环境，无法在 CI 验证（平台限制如实声明）。
- 依赖 gtk2/2.24.33 制品仓未发布（配方已合入 main），本地由他人配方创建缓存验证；
  若 CI 需消费请先发布 gtk2 制品或保证该包可从源码构建。
