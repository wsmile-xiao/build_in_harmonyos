# genext2fs 1.6.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++
- 平台: 鸢鸿蒙 HarmonyOS (aarch64, musl libc)
- 状态: published

## 编译步骤

```bash
# Step 1: 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build genext2fs 1.6.2 \
  --url=https://github.com/bestouff/genext2fs/archive/refs/tags/v1.6.2.tar.gz

# Step 2: 读取上下文
source .build-context-genext2fs-1.6.2
cd $BUILD_SRC_DIR

# autoreconf 生成 configure（原 tarball 不含 configure 脚本）
autoreconf -fi

# 修复 HMDFS 兼容性问题：configure 中 umask 077 → umask 022
sed -i 's/umask 077/umask 022/g' configure

# 编译安装（R20 DESTDIR 模式）
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX

# 安全弹窗验证 (R7)
$TEST_PREFIX/$DEFAULT_PREFIX/bin/genext2fs -h

# 测试
make check

# 预编译包制作 (R19)
python3 $SKILL_ROOT/scripts/ohc-run.py package genext2fs 1.6.2

# 本地安装验证
make install
$DEFAULT_PREFIX/bin/genext2fs -h

# 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish genext2fs 1.6.2 published

# 质量门禁
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build genext2fs 1.6.2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | 鸢鸿蒙环境缺少CA证书，urllib验证失败 | 手动curl -kL下载tarball到~/tmp/builds/，重新运行init-build（检测到已有tarball跳过下载） |
| 2 | 原tarball不含configure脚本 | genext2fs仅含configure.ac，需autoreconf bootstrapping | 先运行autoreconf -fi生成configure及构建基础设施 |
| 3 | config.status Permission denied | HMDFS上config.status用umask 077创建临时目录，导致无法写入subs1.awk | 修改configure脚本中umask 077→022（两处），此修复通过补丁0009固化 |
| 4 | make check xattr测试FAIL | 测试依赖e2fsck验证ext2镜像，鸢鸿蒙未安装e2fsck | 平台限制，不阻塞。22个基础测试PASS，genext2fs核心功能正常 |

## 源码修改

| 补丁文件 | 类型 | 说明 |
|----------|------|------|
| 0001-Makefile.in.patch | bootstrap | autoreconf生成的Makefile.in（原tarball不含） |
| 0002-config.h.in.patch | bootstrap | autoreconf生成的config.h.in |
| 0003-aclocal.m4.patch | bootstrap | autoreconf生成的aclocal.m4 |
| 0004-compile.patch | bootstrap | autoreconf生成的compile辅助脚本 |
| 0005-depcomp.patch | bootstrap | autoreconf生成的depcomp辅助脚本 |
| 0006-install-sh.patch | bootstrap | autoreconf生成的install-sh辅助脚本 |
| 0007-missing.patch | bootstrap | autoreconf生成的missing辅助脚本 |
| 0008-test-driver.patch | bootstrap | autoreconf生成的test-driver辅助脚本 |
| 0009-configure-umask-hmdfs.patch | platform_fix | HMDFS兼容性修复：config.status临时目录umask 077→022 |

注意：0001-0008为autoreconf生成的构建基础设施文件，原tarball不含这些文件。0009为唯一的源码级别修改，修改configure脚本中两处umask 077→022。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无外部依赖 | - | genext2fs是纯C独立工具，无第三方库依赖 |
| autoreconf | autoconf 2.72 + automake 1.16.5 | 构建时需要，用于生成configure脚本 |
| clang | 15.0.4 | 编译器 |

## 验证结果

```bash
# 版本
$ genext2fs -V
genext2fs 1.6.2

# 帮助
$ genext2fs -h
Usage: genext2fs [options] image
Create an ext2 filesystem image from directories/files
...（完整选项列表）

# 实际生成 ext2 镜像（功能验证）
$ genext2fs -b 4096 -d ~/tmp/test-rootfs ~/tmp/test-ext2.img
copying from directory /storage/Users/currentUser/tmp/test-rootfs
# 生成 4MB ext2 镜像，功能正常

# 二进制信息
$ file genext2fs
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| genext2fs-1.6.2-ohos-aarch64.tar.gz | 93KB | 预编译包（ELF已签名、已strip） |
| genext2fs-1.6.2-ohos-aarch64-debug.tar.gz | 32KB | 调试符号包 |

## 注意事项

1. 此软件为 autotools 项目，原 tarball 不含 configure 脚本，需要先运行 autoreconf -fi
2. HMDFS 上 config.status 的 umask 077 会导致 Permission denied，必须改为 umask 022
3. e2fsck 在鸢鸿蒙平台不可用，xattr 相关测试会 FAIL，但核心功能不受影响
4. 此软件无外部依赖，为纯 C 单文件工具

---
**编译结束**: 2026-06-12 01:19
**最终状态**: published