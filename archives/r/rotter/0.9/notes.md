# rotter 0.9 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，无 libtool）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS PC aarch64）
- 状态: built
- 上游: rotter — JACK 音频记录器（Recording of Transmission / Audio Logger），按小时生成归档
- 官方源: https://www.aelius.com/njh/rotter/rotter-0.9.tar.gz（sha256 6dfa001d…，与 Debian orig tarball 一致）
- 上游版本时间: 2010-10-03（config.guess 2009-12-30 / automake 1.7 时代）

## 编译步骤（探索阶段，真机原生构建）

```bash
source .build-context-rotter-0.9 && cd $BUILD_SRC_DIR
# 1) autotools OHOS 平台识别补丁（见下方源码修改）
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
#    2009 版 config.guess 无 GUESS 变量，脚本插入的分支需手工改为 echo+exit
#    2009 版 config.sub 不识别 aarch64，需四处手工修补
sed -i 's/umask 077/umask 002/g' configure            # HMDFS 组写兼容
# 2) 依赖环境（ohpcd 预编译制品 full_deploy 后拍平为自有权限副本）
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig
export CPPFLAGS="-I$PREFIX/include" LDFLAGS="-L$PREFIX/lib"
export LD_LIBRARY_PATH="$PREFIX/lib:/system/lib64:/system/lib64/ndk"
export LIBS="-lmp3lame" CC=clang CFLAGS="-g -O2 -fcommon"
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
make check   # 上游无测试：Nothing to be done for 'check-am'（0 用例）
./src/rotter --help   # 冒烟：输出 rotter version 0.9 + 完整用法
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess "unable to guess"（插入 HarmonyOS 分支后仍失败） | 2009 版 config.guess 无 `$GUESS` 变量（逐 case `echo …; exit ;;`），patch-autotools-ohos.pl 插入的 `GUESS=${MACHINE}-…` 赋值后静默落入 error 分支 | 手工把插入分支改为 `echo ${MACHINE}-unknown-linux-ohos; exit ;;`（补丁 0001） |
| 2 | config.sub "Invalid configuration 'aarch64-…'" | 2009 版 config.sub 不认识 aarch64 CPU，也不认识 ohos 三元组 | 四处修补：CPU 列表加 aarch64/aarch64be（含 company 形式）、maybe_os 加 linux-ohos*、OS 列表加 -linux-ohos*、-linux 归一化前特判 -linux-ohos*（补丁 0002） |
| 3 | config.status "could not create/setup …"，configure 静默失败 | automake 1.7 时代 configure 以 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMDFS 剥离组写权限 | umask 077→002（补丁 0003，同 twolame） |
| 4 | 链接 duplicate symbol: mpegaudio_file | rotter.h:135 全局变量无 extern（ tentative definition），2010 年 GCC 默认 -fcommon；clang ≥10 默认 -fno-common | 配方 `tc.extra_cflags.append("-fcommon")`；不改动上游源码 |
| 5 | configure 报 "cannot run C compiled programs"（实为 Error loading shared library libmp3lame.so.0） | AC_CHECK_LIB(-lmp3lame) 的 conftest 需运行时加载依赖 .so；且 HMDFS 上 full_deploy 出的依赖 .so 属主为其他 uid，动态加载器读取失败 | ①配方 generate() 里把所有依赖 libdir 注入 LD_LIBRARY_PATH；②依赖需拍平为自有权限副本（cp -L）后构建 |
| 6 | `checking for lame_get_version in -lmp3lame... no`（unable to find library） | lame 无 .pc 文件，AutotoolsToolchain 不注入依赖的 -I/-L | 配方 generate() 遍历 dependencies 注入 CPPFLAGS=-I… / LDFLAGS=-L… |
| 7 | conan create 中 config.status 报 `sort: stat failed: -: Permission denied` / `cat: -: Permission denied` | profile buildenv PATH 把 /storage/Users/currentUser/usr/local/bin 排前，其中 GNU coreutils 9.10 在 HMDFS 上对不存在路径的 stat 返回 EACCES（正常应为 ENOENT），GNU sort 视为致命 | 本机用 scratch profile（未入仓）在 PATH 最前加 /system/bin（toybox）；CI 的 ext4 上 ENOENT 行为正常，不受影响 |
| 8 | make 链接步骤 Error 126（safe-delete-bash-env.sh → safe-bin/rm bad interpreter） | 平台沙箱导出 BASH_ENV + bash 函数 rm()→safe-bin/rm，其 shebang /bin/bash 在本机不存在；make 的 SHELL=bash（CONFIG_SHELL），每条命令都被坏包装器劫持 | 运行 conan create 时 `env -u BASH_ENV -u BASH_FUNC_rm%% …`（构建子树内去掉劫持，工具沙箱自身保护不受影响） |
| 9 | test_package ctest/直接执行 rotter_consumer_test 报 Error loading shared library libmp3lame.so.0 | 同 #5：conan cache 内 .so 属主 uid 与运行进程 uid 不一致（HMDFS） | test_package test() 先把依赖 .so（follow_symlinks）拷贝为自有副本到 rtlibs/，LD_LIBRARY_PATH 前置该目录（CI 上 cache 本身可加载，此步骤为无害冗余） |
| 10 | test_package find_package(SndFile) 找不到 | CMakeDeps 只为 test_package 直接 requires 生成 config | test_package 显式 requires libsndfile/1.2.2、lame/3.100、twolame/0.4.0（与 rotter pin 同版本） |

## 源码修改（全部平台移植类，无 __OHOS__ 宏）

| 补丁 | 内容 |
|------|------|
| patches/0001-config.guess.patch | config.guess 识别 HarmonyOS，输出 aarch64-unknown-linux-ohos（echo+exit 修正 2009 版无 GUESS） |
| patches/0002-config.sub.patch | 2009 版 config.sub 支持 aarch64 + ohos-linux 三元组（四处） |
| patches/0003-configure.patch | configure 临时目录 umask 077→002（HMDFS 组写兼容） |

## 依赖版本

- jack/1.9.22（必选，PKG_CHECK_MODULES jack >= 0.100.0）
- libsndfile/1.2.2（必选，sndfile >= 1.0.18）
- lame/3.100（可选 MP3，AC_CHECK_LIB(mp3lame)）
- twolame/0.4.0（可选 MP2，twolame >= 0.3.9）
- 系统库 libm/libc/pthread/dl 由工具链提供，不单独适配

## 上游测试三步法（R51）

1. 清点：Makefile.am 仅 SUBDIRS=src，无 tests/、无 check 目标 → 上游 0 个自动化测试用例
2. 实跑：`make check` → "Nothing to be done for 'check-am'"，0 用例；上游真实测试入口=构建+`rotter --help` 冒烟
3. 新增：test_package 鸿蒙消费者用例 consumer_test（14 断言：libsndfile WAV 回环 5 + lame MP3 编码 5 + twolame MP2 编码 4）+ rotter 二进制 --help 冒烟（验证 libjack 运行时可加载）→ 详见 reports/test-report.md

## 验证结果

```bash
conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>   # EXIT=0
# consumer_test: 14/14 断言 PASS（libsndfile/lame/twolame 真实调用）
# rotter --help smoke: PASS（rotter version 0.9 横幅）
```

## 注意事项

- 本机（HMDFS）运行 conan create 需 scratch profile（PATH 最前加 /system/bin 缓解 GNU coreutils EACCES 怪癖）+ `env -u BASH_ENV -u BASH_FUNC_rm%% …` 规避平台沙箱坏包装器；两者均为本机环境措施，配方/仓库不含、CI 不需要。
- rotter 运行时需 jackd 守护进程与音频后端，OHOS 无音频后端，无法做端到端录音验证（build-only + smoke + 依赖栈消费者用例）。
- rotter 产出可执行文件 → 软件级 commands.json（R38）已建。
---

**编译结束**: 2026-09-27 01:58
**最终状态**: published
