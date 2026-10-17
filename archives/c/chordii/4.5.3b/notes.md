# chordii 4.5.3b — OpenHarmony 编译记录

## 基本信息
- 软件: chordii
- 版本: 4.5.3b
- 构建系统: autotools（automake 递归 Makefile，AC_INIT [Chordii] [4.5.3b]）
- 目标: ohos-aarch64 (os=OHOS, arch=armv8, clang 15)
- 上游: https://downloads.sourceforge.net/project/chordii/chordii/4.5/chordii-4.5.3b.tar.gz
  （SourceForge 官方项目 chordii 的官方 CDN；文件位于 4.5 目录下，
  上传时间 2020-02-02，大小 174.2 kB 与目录列表一致）
- SHA256: edb19be9de456366e592a75a5ce1c0a75352a55d5b4e5f282c953c7e7f2d87b5
- License: GPL-3.0-or-later（COPYING 随包打入 licenses/）

## 编译指导
- E011（平台知识，已验证）: HMDFS 无法写入 configure 中 `umask 077` 创建的
  临时目录（confXXXX/subs1.awk Permission denied），patch 0001-configure.patch
  将两处 `umask 077` 改为 `umask 022`。补丁由 refresh-patch --auto 基于
  track-edit 记录生成。
- E163 族问题: src/chordii.h 在头文件中定义全局变量 dummy_kcs 与
  dummy_chord_struct（tentative definition），被 6 个翻译单元包含；clang>=10
  默认 -fno-common，链接 chordii 时报 ld.lld duplicate symbol。解决方式为
  conanfile.py generate() 中 `tc.extra_cflags.append("-fcommon")`（与 alex4
  1.1、arpalert 2.0.12 配方先例一致），无源码补丁。注意 make 不因 CFLAGS
  变化自动重编 .o，探索时需 make clean 后重建。
- 现代 automake 支持 DESTDIR，package() 使用 autotools.install() 正常 staging
  （bin/chordii、bin/a2crd、man1 帮页）。
- 无交叉三元组需求：设备原生 configure 通过，无需 --host/--build。

## 上游测试统计（口径）
- 上游源码静态声明：src/Makefile.am `TESTS = test/above.sh test/below.sh
  test/passthrough.sh`，共 3 个测试脚本（automake test harness，
  test-driver 随包）。每个脚本对 a2crd 的输出做 diff 断言。
- 实际执行：`make check` 输出 Testsuite summary：TOTAL: 3, PASS: 3,
  FAIL: 0, SKIP: 0（设备探索构建与 conan create 各执行一次，均通过）。
  与静态声明 3/3 一致，无跳过、无未注册用例。

## 补丁清单
- 0001-configure.patch：E011 HMDFS umask 077→022（仅 configure 临时目录
  权限位；platform_only）。

## 已知限制
无。

## 功能验证
- make check: 上游 3 项测试全部通过。
- test_package（消费者测试，1 个脚本 4 项检查）:
  1. chordii --version 输出 4.5.3b；
  2. chordii 将 fixture（res/test.cho）格式化为 PostScript，输出以 %!PS
     头开始；
  3. 输出包含歌名 "Test Song" 与歌词 "line of lyrics"；
  4. a2crd 转换 fixture 保留和弦指令（"Test [C]song"）。
---

**编译结束**: 2026-09-09 01:21
**最终状态**: built
