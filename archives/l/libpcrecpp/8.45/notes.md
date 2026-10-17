# libpcrecpp 8.45 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built (conan-verify G0-G4 全部通过)

## 概述

libpcrecpp 无独立上游源码仓库，是 PCRE (PCRE1, legacy) 库的 C++ 封装组件。源码位于
pcre-8.45 官方源码包根目录（pcrecpp.cc / pcrecpp.h / pcre_scanner.* / pcre_stringpiece.* /
pcrecpparg.h.in）。本包策略：
1. 下载 pcre-8.45 官方 tarball 作为源码
2. 运行完整 autotools configure（生成 config.h/pcre.h/pcre_stringpiece.h/pcrecpparg.h）
3. 只 make libpcrecpp.la（其 LIBADD 会连带构建 libpcre，但只打包 pcrecpp 产物）
4. requires("pcre/8.45") 复用 ohpcd 已发布的 libpcre 预编译包（R36 依赖已发布）

## 编译步骤

```bash
./configure --prefix=/storage/Users/currentUser/tmp/pcrecpp-prefix \
  --enable-static --disable-shared
make -j2            # 完整编译（含测试程序）
make check          # 5/5 全部通过
make install DESTDIR=...  # staging 验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 创建临时目录 Permission denied | E011: HMDFS umask 077 不兼容 | config.guess + configure 中 umask 077 → 022（0001/0003 补丁） |
| 2 | config.guess 无法识别 OHOS | E007: 缺少 HarmonyOS 检测分支 | config.guess 增加 aarch64-unknown-linux-ohos case（0001 补丁） |
| 3 | config.sub 拒绝 linux-ohos 组合 | E007: kernel-os 验证缺 ohos | config.sub 增加 ohos* / linux-ohos*（0002 补丁） |
| 4 | G2 conan create 中 pcre.h not found（test_package） | pcrecpp.h `#include <pcre.h>` 但 pcre 包 CMakeDeps 未导出 include | pcrecpp 包同时打包 pcre.h（与 pcre/8.45 同版本），test_package 显式 find_package(pcre) |
| 5 | pcre_scanner.h 打包缺失 | 该头文件是源码自带（非 configure 生成），与生成的 pcre_stringpiece.h 位置不同 | package() 分别从 source_folder / build_folder 复制 |
| 6 | finish 补丁编号漂移 | refresh-patch 重新编号 0001/0002/0003，conandata.yml 仍引用旧名 | 同步 conandata.yml 补丁声明 |

## 源码修改（补丁）

- 0001-config.guess.patch: OHOS 平台检测 + umask 077→022（config.guess）
- 0002-config.sub.patch: ohos-linux triplet / ohos* OS / linux-ohos* kernel 验证
- 0003-configure.patch: configure 中 umask 077→022（E011）

## 依赖版本

- pcre/8.45（ohpcd 预编译，含 libpcre.a + pcre.h）

## 验证结果

```bash
# 上游测试（make check）5/5 PASS
pcrecpp_unittest          PASS
pcre_scanner_unittest     PASS
pcre_stringpiece_unittest PASS
RunTest                   PASS
RunGrepTest               PASS

# conan create + test_package
test_pcrecpp              PASS (FullMatch/PartialMatch/FindAndConsume/error/options)
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libpcrecpp.a | pcrecpp 静态库（C++ wrapper） |
| include/pcre.h | PCRE 核心头（与 pcre/8.45 同版本，供 pcrecpp.h include） |
| include/pcrecpp.h | pcrecpp 主头文件 |
| include/pcre_scanner.h | Scanner 类头文件 |
| include/pcre_stringpiece.h | StringPiece 头文件 |
| include/pcrecpparg.h | Arg 模板头文件 |

## 注意事项

- 版本号 8.45 与 pcre/8.45 保持一致（同源同版本）
- pcrecpp.h 内部 include <pcre.h>，因此本包同时提供 pcre.h 保证消费者编译完整性
---

**编译结束**: 2026-09-16 23:38
**最终状态**: built
