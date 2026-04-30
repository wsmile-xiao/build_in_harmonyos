# argp-standalone 1.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-21
- 编译器: clang/clang++
- 状态: partial（编译完成，部分打包步骤可能未走完）

## 编译步骤
1. autoreconf -fi 生成 configure 脚本
2. 应用补丁 0001-configure.patch（修复 umask 和平台兼容性问题）
3. `./configure --prefix=$HOME/usr/local LIBS=-lintl`
4. `make`
5. 手动安装 argp.h, argp-fmtstream.h, libargp.a

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 tarball 无 configure | 上游未包含 | autoreconf -fi 生成 |
| 2 | configure 中 umask 077 | HMDFS 不兼容 | 补丁改为 umask 022 |
| 3 | 链接时缺少 intl 符号 | 依赖 gettext | 传 LIBS=-lintl |
| 4 | noinst 静态库无法 make install | 上游设计 | 手动安装头文件和库文件 |

## 源码修改
- `configure` — umask 077 → 022 (0001-configure.patch)

## 验证结果
- 质量门禁 verify-build: PASS
- 交付物: argp-standalone-latest-ohos-aarch64.tar.gz (179.5KB)

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| argp-standalone-latest-ohos-aarch64.tar.gz | 179.5KB | 预编译安装包 |

## 注意事项
- 是 noinst 静态库，仅提供 libargp.a + 头文件
- 补丁类型为平台适配（auto, platform_only）
---

**编译结束**: 2026-04-30 02:47
**最终状态**: built
