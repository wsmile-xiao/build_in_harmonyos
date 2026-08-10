# acorn-fdisk 3.0.6 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-08-09
- 编译器: clang（OHOS aarch64，Conan ohos-aarch64 profile）
- 状态: built

## 编译步骤

```bash
# 源码：Debian 官方源池 upstream orig tarball（与上游 arm-fdisk 3.0.6 字节一致）
#   URL:    https://deb.debian.org/debian/pool/main/a/acorn-fdisk/acorn-fdisk_3.0.6.orig.tar.gz
#   SHA256: f7fb9ccda5bbc353bfd9edfd34a5b8e7d1f6bfebc7a5a43ea7d23b9a10b29cb1

# 构建（conan create 内执行）：
#   make -j2 CC="<OHOS clang>" STRIP=: LDFLAGS=""
# 顶层 Makefile 默认 STRIP=strip、LDFLAGS=-N 在 OHOS 上不适用，显式覆盖为 no-op。
# 产物：fdisk（fdisk.o + lib/part.a lib/scheme.a lib/blkio.a lib/util.a）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 Makefile 默认 `STRIP=strip`、`LDFLAGS=-N` | 上游为 1998 年 ARM Linux 工具，链接/剥离选项面向旧工具链 | 构建命令覆盖 `STRIP=: LDFLAGS=""` |
| 2 | 上游 tarball 无 COPYING/LICENSE 文件 | 上游未随源码发布许可证文本 | 依据 Debian packaging copyright 元数据声明 GPL-1+，package() 内写入 licenses/COPYING 说明 |
| 3 | 上游产物名 `fdisk` 与系统 fdisk 混淆 | 上游 Makefile 输出名即 fdisk | 按 Debian 惯例安装为 bin/acorn-fdisk |

## 依赖版本

- 无外部依赖（仅 libc，preflight 通过）
- OHOS SDK: ohos-sdk_26.0.0.18（clang 15）

## 验证结果

```bash
# 消费者测试（test_package，3 个场景 5 条断言）：
#   1. --version → 输出 "arm-fdisk v3.0.6"，退出码 0
#   2. --help    → 输出 "Usage:"，退出码 0
#   3. 坏设备路径 → 非零退出
# 上游无测试套件（Makefile 仅 all/clean/tar 目标），upstream_tests=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/acorn-fdisk | 分区编辑器可执行文件 |
| share/doc/acorn-fdisk/README | 上游 README |
| share/doc/acorn-fdisk/ChangeLog | 上游变更日志 |
| licenses/COPYING | GPL-1+ 许可证说明（依据 Debian copyright） |

## 注意事项

- 运行时需要块设备访问权限（root），普通用户环境仅验证 --version/--help 与错误路径
- 平台版本 3.0.6 与上游版本 3.0.6 一致，无版本映射差异
---

**编译结束**: 2026-08-09 21:36
**最终状态**: built
