# mpegdemux 0.1.5 适配笔记

## 编译环境
- 构建系统: autotools (上游自带预生成 configure, autoconf 2.71)
- 编译日期: 2026-08-31
- 编译器: clang/clang++
- 状态: built
- 产物: 单一 CLI 二进制 mpegdemux (无库文件)

## 上游核实

| 项 | 值 |
|----|-----|
| 官方主页 | http://www.hampa.ch/mpegdemux/index.html |
| 上游版本 | 0.1.5 (version 文件: `mpegdemux 0 1 5 0.1.5`) |
| 发布日期 | 2023-09-20 |
| tarball | mpegdemux-0.1.5.tar.gz (75220 bytes) |
| MD5 (官方 MD5SUMS) | 85d38eb9d62936e4d55b9120d914b814 |
| SHA256 | 05015755d45e50cbd3018baeaa8abcedc003b1162fa28237a72ab25c1bc00023 |
| License | GPL-2.0 (COPYING = GNU GPL v2) |

SHA256 与 Debian/Ubuntu launchpad 镜像一致，版本真实性已核实。

## 上游测试情况

**上游无正式测试套件**，证据：
- 源码树 38 个文件，无 tests/ regress/ fixture 文件
- Makefile.in 全部目标: `all clean distclean man install dist dist-dist dist-contrib dist-extra`
- 无 `check:` / `test:` 目标，无 TESTS / check_PROGRAMS
- configure.ac 仅 AC_CHECK_HEADERS(inttypes.h)，无测试相关宏
- Debian 打包仅添加 superficial autopkgtest (`echo Check output from mpegdemux --help`)

因此 test_package 承担唯一真实功能验证。

## 编译步骤

```bash
# 1. 零依赖，上游自带 configure
./configure --prefix=$HOME/usr/local

# 2. 编译 (零 patch)
make -j$(nproc)

# 3. 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无 | mpegdemux 零依赖纯 C 程序，musl 兼容性良好 | 零 patch 构建 |

## 源码修改

无。零 patch 构建，未修改任何上游源码。

## 依赖版本

无外部依赖。

## 验证结果

```bash
$ mpegdemux -V
mpegdemux 0.1.5

$ file $(which mpegdemux)
ELF 64-bit LSB executable, ARM aarch64, dynamically linked,
interpreter /lib/ld-musl-aarch64.so.1
```

test_package 真实执行四种 demux 模式 (scan/list/demux/remux)，
使用程序化生成的 MPEG fixture，检查输出文件大小/结构/确定性，
并含负向测试 (空文件输入必须非零退出)。

Conan verification: ALL PASS (G0-G4, L2/L4/L5)
W3 Local CI simulation: PASS

---

**编译结束**: 2026-08-31
**最终状态**: built
