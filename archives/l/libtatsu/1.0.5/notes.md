# libtatsu 1.0.5 适配笔记

## 真实 HarmonyOS 验证证据（ohos-aarch64-local profile，本机即 OHOS PC AArch64）

- 编译器：clang-15.0.4（OHOS 工具链，--target=aarch64-linux-ohos，
  见 ci/conan/profiles/ohos-aarch64 的 buildenv）
- 包产物：libtatsu.a（静态库，ar 归档，成员 ELF64 LSB **AArch64** REL）
- test_package / test_cpp：ELF64 LSB **AArch64** PIE executable，
  interpreter **/lib/ld-musl-aarch64.so.1**（OHOS musl）
- NEEDED：libcurl.so、libc.so（无 RUNPATH 泄漏，conanrun 环境注入依赖路径）
- 安装完整性：include/libtatsu/{tatsu.h,tss.h}、lib/libtatsu.a、
  lib/pkgconfig/libtatsu-1.0.pc（Requires: libplist-2.0 >= 2.3.0）
- scoped CI（JUNK_PR_DIFF 限定 libtatsu 范围）：G0/G0e/KC/JC/L0/L1/L2/L4/L5
  全部 pass；test_package 62 项 + test_cpp 6 项断言全部 PASS，0 FAIL

## 上游测试盘点结论

上游未提供正式测试套件：tarball 无 test/tests 目录、无 check_PROGRAMS、
无 TESTS、无 CTest/Meson test、无 CI 测试入口；`make check` 仅执行
automake 默认空目标（Total 0 / Pass 0 / Fail 0 / Skip 0）。

## 编译环境
- 平台: HarmonyOS (OpenHarmony) PC, aarch64
- 编译器: clang 15 (target aarch64-linux-ohos)
- 构建系统: autotools
- 状态: built

## 软件信息
- 上游: https://github.com/libimobiledevice/libtatsu
- Release tarball: https://github.com/libimobiledevice/libtatsu/releases/download/1.0.5/libtatsu-1.0.5.tar.bz2
- SHA256: 536fa228b14f156258e801a7f4d25a3a9dd91bb936bf6344e23171403c57e440
- License: LGPL-2.1+ (COPYING + 头文件声明)
- 语言: C (无 C++ 代码；公共头文件带 extern "C"，C++ 消费者可直接包含)

## 上游依赖
- libplist >= 2.6.0 (configure.ac 要求；仓库制品仅有 2.3.0)
- libcurl >= 7.0 (仓库使用 libcurl/8.5.0)

## 上游测试
上游 1.0.5 tarball 无 test/ 目录、无 check_PROGRAMS/TESTS、无 CTest/Meson test
入口 —— 上游未提供正式测试套件（仅 CI workflow 做构建冒烟）。测试覆盖由
本仓库 test_package 承担（离线 mock TSS 服务验证请求/响应契约）。

## libplist 版本差异与 compat patch
libtatsu 1.0.5 的 src/tss.c 使用 7 个 libplist 2.6.0 新增的 dict 辅助 API
（plist_dict_get_bool/get_uint、plist_dict_copy_item/_bool/_uint/_string/_data，
共 192 处调用），而制品仓仅有 libplist/2.3.0。由于：

- libplist 公共头不导出任何版本宏，无法在编译期 feature-test；
- 2.3.0 已具备全部所需原语（plist_get_bool_val/uint_val/string_ptr/data_ptr、
  plist_new_bool/uint/data/string、PLIST_IS_STRING/PLIST_IS_DATA、plist_err_t）；
- tss.c 还用到 PLIST_OPT_NONE（同样 2.6.0 新增，值为 0）。

因此 patches/0001 做了最小兼容：

1. configure（预生成脚本）的 `LIBPLIST_VERSION=2.6.0` 字面量改为 `2.3.0`，
   并在 libplist 检测成功后追加一段纯 shell 探测（pkg-config
   --atleast-version=2.6.0），旧版本时向 CPPFLAGS 追加
   `-DLIBPLIST_LT_2_6=1`；
2. src/tss.c 在 LIBPLIST_LT_2_6 生效时包含 src/plist_dict_compat.h，否则
   仅补定义 PLIST_OPT_NONE 为 0；
3. src/plist_dict_compat.h：上述 7 个 helper 按 libplist 2.6.0 上游实现逐字
   backport（static inline，LGPL-2.1+，同族项目同许可证），另含
   PLIST_OPT_NONE 定义；
4. src/libtatsu-1.0.pc.in 的 Requires 模板降为 2.3.0。

注意：patch 刻意不触碰 configure.ac —— 本机 autotools 缺 pkg.m4，
且 configure.ac 比 configure 新会触发 make 的 maintainer rebuild 规则，
用损坏的 autoreconf 输出覆盖可用脚本。在 libplist >= 2.6.0 的环境下
LIBPLIST_LT_2_6 不定义、backport 不参与编译，行为与上游完全一致。

## OHOS 适配要点（与 libimobiledevice-glue 1.3.0 同族）
1. mktemp wrapper：autoconf AS_TMPDIR 的 `umask 077 && mktemp -d` 在 HMDFS
   上产生 drwx--S--- 目录，config.status 写 subs*.awk 失败；伪造一个恒
   失败的 mktemp 迫使其走 mkdir 回退（E114）。
2. config.guess 不识别 OHOS，configure 强制 --build=aarch64-unknown-linux-gnu。
3. AutotoolsDeps + PkgConfigDeps 喂入 libplist/libcurl 的 -I/-L/-l 与 .pc
   （configure 的 LIBPLIST_LT_2_6 探测即读取此处生成的 libplist-2.0.pc）。
4. LD_LIBRARY_PATH：OHOS loader 无默认搜索路径，configure conftest 需指向
   conan 缓存的共享库目录。
5. make -j1：并行 make 触发 HMDFS jobserver fifo EPERM（R9）。
6. configure 不执行目标平台程序探测：交叉模式下 AC_CHECK_FUNCS 等仅做
   链接探测，无需 target runtime probe（tss.c 无此问题）。

## 交叉编译参数
build=aarch64-unknown-linux-gnu（强制）、host 由 conan profile 推导为
aarch64-linux-ohos；CC/AR/RANLIB/STRIP 由 AutotoolsToolchain 从
tools.build:compiler_executables 与 llvm 工具链推导注入；PKG_CONFIG_PATH
由 PkgConfigDeps 生成的 generators 目录注入。

## shared/static
上游 autotools/libtool 原生支持 --enable-static/--disable-shared 与
--enable-shared/--disable-static 两种 variant；本配方默认 static（R26），
shared 未在 OHOS 上验证（OHOS 共享库需 codesign 签名流程），故仅声明默认
static 并如实记录。

## 验证
```bash
pkg-config --modversion libtatsu-1.0
# 输出: 1.0.5
```

## 关键发现
- libplist 2.6.0 dict helpers 可在 2.3.0 原语上无损 backport（static inline）
- tss_request_send 的 endpoint 可由调用者注入（server_url_string 参数），
  这是离线 mock 测试的入口
