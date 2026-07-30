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

---

# Conan 配方补充（2026-07-30）

> 以上为 2026-04 手工编译路径的原始记录，**原样保留**。以下为本次新增的 Conan 配方说明。

# argp-standalone 1.5.0 —— Conan 配方补充说明

## 与上面 2026-04 手工路径的关系
前人的手工编译记录（含 4 条 knowledge_gained）**完整保留在上方**，本次是补 Conan 配方。
两条路径在"缺 intl 符号"上的解法不同，见下。

## 关键适配

### intl 符号：本配方用 `ac_cv_header_libintl_h=no`
OHOS musl 的 `libintl.h` 是空壳——**头在、符号不在**（无 `__dcgettext`）。
configure 探测到头就认为 gettext 可用，编译期报 int-conversion，链接期必然找不到符号。

- 前人手工路径的解法：`LIBS=-lintl`（依赖一个 gettext 移植）。
- 本配方的解法：`ac_cv_header_libintl_h=no`，直接告诉 configure 没这个头，
  从而**不引入 gettext 依赖**。

> 注意：这里**不能**用 `-Wno-int-conversion` 糊过去——那只压住编译警告，
> 链接期照样缺符号。

### noinst 静态库要手工安装
上游全是 `noinst_*` 目标，`make install` 什么都不装。
package() 里手工装 `argp.h` 与 `libargp.a`，`package_type = "static-library"`。

## 状态
built —— 真机 `conan create` 通过；test_package 真实调用 `argp_parse` 解析一组参数并断言结果。
