# tegrarcm 1.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-13
- 编译器: clang/clang++ (OHOS SDK, profile ci/conan/profiles/ohos-aarch64)
- 状态: built (待真机 rule4 门禁)

## 源码信息
- 上游: https://github.com/NVIDIA/tegrarcm (tag v1.8, commit f6a46f1b342fe5ff531281e605b52b2a604a8aac)
- 包: https://github.com/NVIDIA/tegrarcm/archive/refs/tags/v1.8.tar.gz (457036 bytes)
- sha256: 08329ee0247499b28ec37b0cc639f35443792dfb9bc4a8a182eea63dae6f64ea
- 内容: 29 个成员, configure.ac + Makefile.am + src/*.c/*.cpp, 无生成的 configure, 无 tests/ 目录

## 编译步骤

1. 依赖先行 (W0 修订 2026-10-14): 预检同时启用 conancenter+ohpcd 时 cryptopp/8.9.0 解析到 conancenter CMake 版，其 tool_requires cmake/3.31.12 无 OHOS sources（KeyError OHOS）；且 libusb/1.0.29 在 ohpcd 仅 built 未 published，无可复用二进制。改 vendor 方案：conandata 内置 cryptopp+libusb 官方源码，Makefile/autotools 私有前缀构建，不进 requires 图，残留 tool_requires 仅 automake 系（ohpcd 已有）。
2. 工具链: 无 tool_requires，直调 HMBS PATH 内系统 clang/make（conancenter m4 的 configure 硬编码 /data/service/hnp/bin/bash 报 Error 127，故弃 autoreconf）。
3. 打补丁: apply_conandata_patches (0001-musl-error-h-compat)。
4. 自举: 无 configure 时 `autoreconf -fi` (conanbuild 环境)。
5. 兼容处理: 去掉 configure 中的 umask 077, 修 ac_pwd getcwd 回退。
6. 配置: AutotoolsToolchain `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`, PkgConfigDeps (libusb) + AutotoolsDeps (cryptopp)。
7. 构建: `make -j1`, `make check` (空默认目标, 0 用例, 仅留日志证据), `make install`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/main.c `#include <error.h>` 在 OHOS 上找不到头文件 | musl libc 无 glibc error.h | configure.ac 增加 AC_CHECK_HEADERS([error.h]), main.c 用 HAVE_ERROR_H 守卫, 缺失时提供静态 error() 回退 (fprintf + strerror + exit), 无平台宏 |
| 2 | tarball 无 configure, 直接 configure 失败 | GitHub tag 包是 git 快照, 自生成文件未入库 | build_requirements 声明 automake/autoconf/libtool, build() 中 autoreconf -fi |
| 3 | configure 探 pkg-config 失败风险 | PKG_CHECK_MODULES 需 pkg-config | tool_requires pkgconf/3.0.6, generate() 中 PkgConfigDeps |
| 4 | --help 退出码为 1, 易被误判为失败 | 上游 OPT_HELP 分支 exit(EXIT_FAILURE) | test_package 断言 --help rc!=0 + 非空 usage 横幅, 反而利用此特性识别 exit-0 桩 |
| 5 | 空输出对比可伪造通过 (toybox 教训) | 仅判退出码会漏检空 fixture | 4 个断言全部检查输出非空并 grep 关键字 (1.8/usage/BCT) |

## 源码修改

- patches/0001-musl-error-h-compat.patch: configure.ac 加 error.h 检测; src/main.c 加 config.h 前置包含与 HAVE_ERROR_H 双分支回退。POSIX 兼容, 无 __OHOS__ 宏。

## 依赖版本

- vendor libusb-1.0.29（官方 release tarball，私有前缀静态安装，netlink sockaddr_storage 守卫复用 libusb/1.0.29 同款修复）
- vendor cryptopp-8.9.0（官方 CRYPTOPP_8_9_0 tarball，make CXX 构建静态 libcryptopp.a，头文件 include/cryptopp/，同 archives/c/cryptopp/8.9.0 做法，无补丁）
- 构建工具: automake/1.18, autoconf/2.72, libtool/2.5.4.1, pkgconf/3.0.6

## 验证结果

```bash
# 上游: 无自动化测试 (make check 为空默认目标, 0 用例)
# test_package (真机待验证):
sh test_tegrarcm.sh <pkg>/bin/tegrarcm <workdir>
# 期望: RESULT: 4 passed, 0 failed
#   1. 二进制可执行
#   2. --version 输出 1.8
#   3. --help 非空 usage (rc=1)
#   4. 无参运行 BCT 校验失败 (rc!=0)
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/tegrarcm | 主二进制 (autotools install) |
| share/man/man1/tegrarcm.1 | 手册页 (sed VERSION 替换生成) |
| licenses/LICENSE | NVIDIA 源码 + miniloader 许可 |

## 注意事项

- miniloader 头文件 (src/miniloader/*) 为 NVIDIA 客户许可, 仅随二进制分发, 不单独处理。
- 无 USB 实机时仅验证 CLI 路径 (--version/--help/参数校验), 不做真实 RCM 下载。
- 本轮未提交, 待 HMBS 真机 rule4 门禁后由后端统一提交。
