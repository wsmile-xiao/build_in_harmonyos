# mpdecimal 2.5.1 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.69, 2016-10-02 版 config.guess/config.sub)
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OHOS SDK, /data/service/hnp/bin)
- 平台: aarch64-unknown-linux-ohos (HarmonyOS Kernel 1.12.0)
- conan profile: ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang 15, libcxx=libc++)
- 状态: published

## 上游信息
- 官方源: https://www.bytereef.org/mpdecimal/
- tarball: https://www.bytereef.org/software/mpdecimal/releases/mpdecimal-2.5.1.tar.gz
- sha256: 9f9cd4c041f99b5c49ffb7b59d9f12d95b683d88585608aa56a6307667b2b21f
- 许可: BSD-2-Clause
- 说明: 十进制浮点运算库（General Decimal Arithmetic Specification 参考实现，Python decimal 模块底层）
- 注意: 上游官方源是 bytereef.org（非 GitHub），不在 CI 镜像 fallback 白名单内；实测本机 curl 可直接下载。若 CI Worker 无法下载源码属 registry/网络类问题，非配方问题（R39 合规：URL 为官方正式源）

## 编译步骤

1. tarball 下载 + sha256 校验（bytereef.org 直连可达）
2. 解压到 $TMPDIR 本地盘构建（HMDFS 上 config.status 临时目录会失败，见问题 #2）
3. 打三个补丁：config.guess（HarmonyOS 识别）、config.sub（linux-ohos triplet）、configure（tmpdir umask）
4. CC=clang CXX=clang++ ./configure --prefix=... [--disable-shared --enable-static]
5. make -j4 → C 库 libmpdec.a/libmpdec.so.2.5.1 + C++ 库 libmpdec++.a/libmpdec++.so.2.5.1
6. make install DESTDIR=staging
7. 上游测试 make check（详见下节）
8. conan create（profile ohos-aarch64）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: 2016-10-02 老 GNU config.guess 不含 HarmonyOS 检测 | 0001 补丁添加 `*:HarmonyOS:*:*` 分支。**注意老版 config.guess 无 GUESS= 变量机制，必须用 `echo ${MACHINE}-unknown-linux-ohos; exit` 写法**（patch-autotools-ohos.pl 自动生成的 GUESS= 写法只适配新版，在 2016 版上不生效）|
| 2 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `umask 077 && mktemp -d` 创建的 drwx--S--- 目录内部无法再创建文件（写测试实证：077 失败/022 成功） | 0003 补丁改 `umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX"`（与 mpfr 4.2.2.1 的 0003-configure-tmpdir.patch 同源方案，autoconf 2.69 通用） |
| 3 | config.sub 拒绝 aarch64-unknown-linux-ohos | 老 config.sub 无 linux-ohos 模式 | 0002 补丁在 maybe_os 列表和 -linux-* os 模式两处加 linux-ohos* |
| 4 | configure 默认找不到编译器 | OHOS clang 不在 PATH（/data/service/hnp/bin） | conan profile 的 tools.build:compiler_executables 提供绝对路径；探索阶段 CC/CXX 环境变量 |
| 5 | C++ 测试 runtest 报 `Error relocating: libc++ symbols not found` | 动态链接 libc++_shared.so 但当时 LD_LIBRARY_PATH 未含 /system/lib64 | musl 默认搜索路径（/etc/ld-musl-aarch64.path）已含 /system/lib64，系统自带 libc++_shared.so；干净环境直接跑通。之前失败是测试时显式覆盖了 LD_LIBRARY_PATH 所致 |
| 6 | 测试程序用 mpd_maxcontext() 得到 NaN | maxcontext 的 prec=999999999999999999 导致运算分配失败 MPD_Malloc_error(0x200) | 测试用 mpd_init(&ctx, 28) 显式设置 28 位精度（与 Python decimal 默认一致） |
| 7 | conan build 里 make check 下载测试数据失败 | HarmonyOS wget 不支持 -nv 选项（4.0.1 notes 坑 #5 复现） | conanfile build() 里用 /usr/bin/curl 绝对路径预下载 dectest.zip 解压到 tests/testdata/（gettests.sh 检测到 add.decTest 存在即跳过 wget） |
| 8 | conan build 里 curl 下载报 SSL 证书错误 | conan buildenv 把 ~/usr/local/bin 前置到 PATH，其 curl（GNU 交叉编译版）找不到 OHOS CA bundle | 用系统 /usr/bin/curl 绝对路径（带系统 CA） |
| 9 | C++ runtest 报 libc++_shared.so symbols not found | **OHOS 加固 musl 加载器忽略非白名单 LD_LIBRARY_PATH**，且环境继承的 LD_LIBRARY_PATH 含空白畸形条目，一旦非空就不走默认路径 | make check 命令前缀 `LD_LIBRARY_PATH=`（置空等价 unset），musl 走默认搜索路径 /etc/ld-musl-aarch64.path → /system/lib64 找到 libc++_shared.so |
| 10 | conan build 报 No rule to make target 'basearith.c' | mpdecimal 手写 Makefile 无 VPATH 支持，不支持 out-of-source 构建 | build() 里用 self.run(cwd=self.source_folder) 在源码树内 configure/make |
| 11 | configure --enable-static 不识别 WARNING | mpdecimal configure 只支持 --enable-shared（默认 yes），无 --enable-static 选项 | generate() 只按需加 --disable-shared；AutotoolsToolchain 自动补的 --enable-static 仅 WARNING 无害 |

## 源码修改（补丁清单）
1. 0001-config.guess.patch: 添加 `*:HarmonyOS:*:*` 分支（echo+exit 老版写法），输出 aarch64-unknown-linux-ohos
2. 0002-config.sub.patch: maybe_os 列表 + os 模式列表两处添加 linux-ohos*
3. 0003-configure-tmpdir.patch: config.status 临时目录 umask 077→022 且使用 TMPDIR

三个补丁均为平台 portability 补丁，不含功能修改。

## 上游测试结果（make check）

官方测试数据从 speleotrove.com/decimal/dectest.zip 下载（144 个 .decTest 文件 + tests++ 16 个 topTest 附加）。

| 测试组 | 二进制 | 测试文件 | 结果 |
|--------|--------|----------|------|
| C 静态库 runtest | tests/runtest | official.decTest (133) + additional.decTest (15) | 148/148 PASS |
| C 共享库 runtest_shared | tests/runtest_shared | official.decTest + additional.decTest | 148/148 PASS |
| C++ 静态库 runtest | tests++/runtest | official.topTest (133) + additional.topTest (15) | 148/148 PASS |
| C++ 共享库 runtest_shared | tests++/runtest_shared | official.topTest + additional.topTest | 148/148 PASS |

合计 592/592 测试组通过，0 失败。（每个 .decTest 文件含数百到数千条断言，总计约 50 万条算例。）

历史对照：mpdecimal 4.0.1（本仓库已发布）报告 official 131 + additional 15——2.5.1 是 133 + 15，版本差异正常。

## conan 配方说明

- conanfile.py: autotools 构建，默认 static（fPIC=True），OHOS 下显式设置 AR/LD/RANLIB/NM/OBJDUMP/STRIP（llvm-* 前缀，参考 mpfr 4.2.2.1）
- 源码树内构建（self.run + cwd=source_folder）：mpdecimal 手写 Makefile 无 VPATH，不支持 conan 默认的 out-of-source
- build() 内 make check（can_run 时执行，L1c 上游测试验证）：先 /usr/bin/curl 预下载官方 decTest 数据（绕过 HarmonyOS wget 无 -nv 的坑），再 `LD_LIBRARY_PATH= make check`（绕过 OHOS musl 加固加载器对 LD_LIBRARY_PATH 的限制）
- package(): make install DESTDIR=package_folder（prefix=/ 由 toolchain 传入）
- package_info: libs=[mpdec, mpdec++]，system_libs=[m]，cmake_file_name=mpdecimal，pkg_config_name=mpdec
- test_package: test_mpdecimal.c 实际调用 mpd_qadd/mpd_qmul/mpd_qdiv/mpd_qabs/mpd_qsqrt/mpd_to_sci/mpd_set_string + 除零 status 验证，8 组断言

## 依赖
- 无 conan 依赖（纯 C/C++ 库，仅需系统 -lm）
- C++ 库运行时依赖系统 libc++_shared.so（musl 默认路径已含 /system/lib64，系统自带）

## 版本对照
- 4.0.1: 本仓库已发布（2026-06-03，旧 package 流程，无 conanfile）
- 2.5.1: 本次适配（conan 流程）；2.5.1 是 CPython 3.9-3.11 内置版本，众多三方库（如 gmpy2 老版、Python 扩展）按 libmpdec.so.3 ABI 依赖此版本

## 验证结果
- config.guess/config.sub 链路: aarch64-unknown-linux-ohos ✅
- configure/make/make install DESTDIR: 全通过 ✅
- make check（探索阶段全量，含 shared 变体）: 592/592 测试组 PASS ✅
- conan create（conan-verify G2，静态构建）: C 静态 148 + C++ 静态 148 = 296 decTest PASS，0 FAIL ✅
- test_package（mpd_qadd/qmul/qdiv/qabs/qsqrt/version/status 8 断言）: 编译运行全过 ✅
- conan-verify 8 道门禁（G0-G4 + L2/L4/L5）: 全部 PASS，status 可标 published ✅

---
**编译结束**: 2026-09-04
**最终状态**: published
---

**编译结束**: 2026-09-04 02:50
**最终状态**: published
