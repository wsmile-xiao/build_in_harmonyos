# ait 1.15 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-08-08
- 编译器: clang 15 (GnuToolchain 注入)
- 状态: built（本地 conan create 验证通过，制品未 upload）

## 编译步骤

1. `init-build` 下载官方源码包 https://ftp.netbsd.org/pub/NetBSD/misc/ktnb/ait-1.15.tar.gz（pkgsrc 维护者镜像）
2. 直接 `make` 编译（ait 为单 Makefile 项目，无需 configure）
3. 打补丁 `0001-makefile.patch`：CC/LD 改 `?=` 尊重 GnuToolchain 注入的编译器；链接改用 `$(CC)`（clang 驱动，自动带 sysroot/libc）
4. `conan create` 干净构建验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | makefile 硬编码 `CC = cc` | GnuToolchain 注入的 clang 被 makefile 覆盖 | 补丁改为 `CC ?= cc` / `LD ?= cc` |
| 2 | 链接报 libc 符号未定义 (free/strndup 等) | 链接规则用 `$(LD)` 直连 `ld.lld`，无 sysroot/libc 参数 | 链接改用 `$(CC)`（clang 驱动自动带 sysroot） |
| 3 | 本地运行二进制报 Operation not permitted | E077：鸿蒙 ELF 需 .codesign 签名 | 已知平台机制，CI `sign.sh` 签名后消除，非适配缺陷 |

## 源码修改

- `0001-makefile.patch`（+3/-3）：CC/LD `?=`；链接用 `$(CC)`。

## 依赖版本

无外部依赖（纯 C，termbox.h 为 header-only 内置实现）。

## 验证结果

```bash
conan create → G2 PASS（14 个目标文件编译+链接成功）
ait -v → "Ait 1.15, BSD 3-Clause, 2026, by Kevin Bloom"
W3 本地 CI 模拟（build_and_test.sh）→ PASS（L0-L5 全过）
```

## 注意事项

- 上游无测试套件（无 `make check` 目标），test_package 以 `ait -v` 二进制冒烟测试代替（R34）。
- 产物为命令行工具，已声明 `commands.json`（R38）。
---

**编译结束**: 2026-08-08 12:40
**最终状态**: built
