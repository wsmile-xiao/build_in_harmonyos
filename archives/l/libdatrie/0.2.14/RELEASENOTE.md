# libdatrie 0.2.14 Release Notes (OpenHarmony)

**发布日期**: 2026-04-22
**版本**: 0.2.14
**目标平台**: OpenHarmony (aarch64)

## 简介

libdatrie 是一个 Double-Array Trie（双数组 Trie）库，提供高效的 Trie 数据结构实现，用于字符串搜索和匹配。

## 变更摘要

- ✅ 首次在 OpenHarmony 平台上编译成功
- ✅ 添加 HarmonyOS 系统识别补丁（config.guess/config.sub）
- ✅ 所有 10 个单元测试通过
- ✅ trietool 命令行工具可用

## 安装说明

### 预编译包安装

```bash
# 下载预编译包
wget libdatrie-0.2.14-ohos-aarch64.tar.gz
wget install-libdatrie-0.2.14.sh

# 安装
sh install-libdatrie-0.2.14.sh

# 验证
trietool --version
```

### 从源码编译

```bash
tar -xf libdatrie-0.2.14.tar.xz
cd libdatrie-0.2.14

# 应用补丁（如果从归档目录下载）
patch -p1 < patches/0001-build-aux-config.guess.patch
patch -p1 < patches/0002-build-aux-config.sub.patch

# 编译
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make check
make install
```

## 已知限制

### HMDFS 临时目录问题

在 HMDFS 文件系统上编译 autotools 项目时，config.status 可能无法在当前目录创建临时文件。

**解决方案**: 设置 `TMPDIR` 环境变量，或在源码目录预创建临时目录。

## 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| libdatrie.so.1.4.1 | 43KB | 共享库 |
| libdatrie.a | 42KB | 静态库 |
| trietool | 30KB | 命令行工具 |
| 头文件 | 4 个 | datrie/*.h |
| pkgconfig | 1 个 | datrie-0.2.pc |

## 依赖

无外部依赖。

## 验证命令

```bash
# 检查库版本
pkg-config --modversion datrie-0.2

# 检查工具
trietool --version

# 运行测试
make check
```

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | ✅ PASS | |
| G2 功能可用性 | ✅ PASS | trietool 可执行 |
| G3 可移植性 | ✅ PASS | RPATH 正确 |
| G4 档案完整性 | ✅ PASS | |
| G0 干净构建 | ⚠️ SKIP | HMDFS 平台限制 |

---

**编译者**: OpenHarmony Compile Agent