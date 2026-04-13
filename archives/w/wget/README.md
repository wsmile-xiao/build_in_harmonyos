# GNU Wget 1.19.1 鸿蒙系统编译指南

## 概述

本文档记录了 GNU Wget 1.19.1 在鸿蒙系统上的编译适配过程。GNU Wget 是一个非交互式网络下载工具，支持 HTTP、HTTPS 和 FTP 协议，支持断点续传、递归下载、镜像网站等功能。相比鸿蒙系统自带的 toybox wget，GNU Wget 提供了更完整的功能支持（如 `-q` 静默模式、`-c` 断点续传、`-r` 递归下载、`-m` 镜像模式等）。

## 软件信息

- **软件名称**: GNU Wget
- **版本**: 1.19.1
- **构建系统**: Autotools (configure)
- **下载地址**: https://ftp.gnu.org/gnu/wget/wget-1.19.1.tar.xz
- **类别**: 网络工具

## 鸿蒙编译环境

- **系统**: HarmonyOS (OpenHarmony)
- **内核**: HongMeng Kernel 1.11.0
- **架构**: aarch64
- **C 库**: musl libc
- **编译器**: Clang 15.0.4 (LLVM)
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)
- **目标三元组**: aarch64-unknown-linux-ohos
- **安装前缀**: `$HOME/usr/local`

## 编译步骤

### 1. 下载并解压源码

```bash
curl -L -o wget-1.19.1.tar.xz https://ftp.gnu.org/gnu/wget/wget-1.19.1.tar.xz
tar -xf wget-1.19.1.tar.xz
cd wget-1.19.1
```

### 2. 应用补丁

```bash
patch -p1 < 0001-config-guess-harmonyos.patch
patch -p1 < 0002-config-sub-harmonyos.patch
```

### 3. 配置

```bash
./configure \
    --prefix=$HOME/usr/local \
    --with-ssl=openssl \
    --without-libpsl
```

**配置选项说明**：
- `--with-ssl=openssl`: 使用 OpenSSL 提供 HTTPS 支持
- `--without-libpsl`: 禁用 PSL（Public Suffix List）支持，鸿蒙系统上可能缺少该库

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

### 0001-config-guess-harmonyos.patch

**修改文件**: `config.guess`

**修改原因**: GNU config 的 config.guess 不识别 HarmonyOS 系统，需要添加系统检测和目标三元组输出。

**修改内容**:

1. 在 `UNAME_SYSTEM` 的 case 分支中添加 `HarmonyOS` 检测，设置 `LIBC=musl`（鸿蒙使用 musl libc）：

```diff
+HarmonyOS)
+	# HarmonyOS uses musl libc
+	LIBC=musl
+	;;
 Linux|GNU|GNU/*)
```

2. 在目标三元组输出中添加 `aarch64:HarmonyOS` 的识别：

```diff
+aarch64:HarmonyOS:*:*)
+	echo aarch64-unknown-linux-ohos
+	exit ;;
+
 aarch64:Linux:*:*)
```

### 0002-config-sub-harmonyos.patch

**修改文件**: `config.sub`

**修改原因**: config.sub 用于验证目标三元组的合法性，需要添加 `ohos` 和 `linux-ohos` 作为有效的操作系统标识。

**修改内容**:

1. 在 `maybe_os` 快速匹配列表中添加 `linux-ohos*` 和 `ohos-linux*`：

```diff
 nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
-  linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \
+  linux-musl* | linux-uclibc* | linux-ohos* | ohos-linux* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \
```

2. 在有效操作系统列表中添加 `linux-ohos*` 和 `ohos*`：

```diff
 	      | -linux-newlib* | -linux-musl* | -linux-uclibc* \
+	      | -linux-ohos* | -ohos* \
```

## 编译特性

GNU Wget 1.19.1 在鸿蒙系统上成功启用了以下特性：

| 特性 | 支持状态 |
|------|----------|
| SSL/TLS (HTTPS) | ✓ 支持 (OpenSSL) |
| zlib 压缩 | ✓ 支持 |
| IPv6 | ✓ 支持 |
| HTTPS 协议 | ✓ 支持 |
| 摘要认证 | ✓ 支持 |
| NTLM 认证 | ✓ 支持 |
| 大文件支持 | ✓ 支持 |
| PSL (Public Suffix List) | ✗ 禁用 |

## 遇到的问题及解决方案

### 问题 1: SSL 证书验证失败

**问题描述**: 鸿蒙系统缺少系统 CA 证书包，导致 HTTPS 下载时证书验证失败。

**解决方案**: 使用 `--no-check-certificate` 参数跳过证书验证：

```bash
wget --no-check-certificate https://example.com/file.zip
```

> ⚠️ **安全提示**: 跳过证书验证会降低安全性，建议仅在可信网络环境中使用，或自行安装 CA 证书包。

### 问题 2: 文档编译失败

**问题描述**: 编译过程中 `texi2pod.pl` 存在权限问题，导致文档编译失败。

**解决方案**: 文档编译失败不影响二进制文件的生成和使用，手动安装编译好的二进制文件即可。

### 问题 3: 测试框架依赖

**问题描述**: 初始测试通过率仅为 16%（约 6/39），大量测试因缺少 Perl 模块而失败。

**解决方案**: 安装 HTTP::Daemon、HTTP::Message、URI 等 Perl 模块后，测试通过率从 16% 提升到 87%（34/39）。

## 测试验证结果

GNU Wget 1.19.1 的测试结果：

```
测试总数: 39
通过:     34
失败:     5
通过率:   87.2%
```

**失败测试说明**: 失败的 5 个测试为 HTTPS 公钥固定（Public Key Pinning）相关功能测试，原因是测试环境缺少完整的 SSL/TLS 证书配置。这些失败的测试不影响核心下载功能的使用。

### 功能验证

```bash
# 版本检查
$ $HOME/usr/local/bin/wget --version
GNU Wget 1.19.1 ...

# HTTP 下载
$ wget http://example.com/file.txt

# HTTPS 下载（跳过证书验证）
$ wget --no-check-certificate https://example.com/file.txt

# 静默模式下载
$ wget -q https://example.com/file.txt

# 断点续传
$ wget -c https://example.com/large-file.zip

# 递归下载
$ wget -r -np https://example.com/directory/

# 镜像网站
$ wget -m https://example.com/
```

## 安装产物

| 类型 | 路径 |
|------|------|
| 可执行文件 | `$HOME/usr/local/bin/wget` |

## 依赖说明

编译 GNU Wget 1.19.1 需要以下依赖：

- **编译工具**: clang, make, pkg-config
- **加密库**: OpenSSL（用于 HTTPS 支持）
- **压缩库**: zlib（可选，用于内容压缩传输）

## 注意事项

1. **HTTPS 需跳过证书验证**: 鸿蒙系统缺少 CA 证书包，HTTPS 下载需加 `--no-check-certificate`
2. **已替换系统 toybox wget**: 安装后 GNU Wget 的功能比 toybox wget 更完整
3. **测试通过率**: 34/39 测试通过，失败的 5 个为 SSL 公钥固定相关测试，非核心功能问题
4. **PATH 设置**: 确保 `$HOME/usr/local/bin` 在 PATH 中优先于系统路径

## 与 toybox wget 的功能对比

| 功能 | toybox wget | GNU Wget 1.19.1 |
|------|-------------|------------------|
| HTTP 下载 | ✓ 支持 | ✓ 支持 |
| HTTPS 下载 | ⚠️ 功能有限 | ✓ 支持（需跳过证书验证） |
| FTP 下载 | ✗ 不支持 | ✓ 支持 |
| 静默模式 `-q` | ✗ 不支持 | ✓ 支持 |
| 断点续传 `-c` | ✗ 不支持 | ✓ 支持 |
| 递归下载 `-r` | ✗ 不支持 | ✓ 支持 |
| 镜像模式 `-m` | ✗ 不支持 | ✓ 支持 |
| 后台下载 `-b` | ✗ 不支持 | ✓ 支持 |
| 限速 `--limit-rate` | ✗ 不支持 | ✓ 支持 |

## 参考资料

- GNU Wget 官方网站: https://www.gnu.org/software/wget/
- GNU Wget 下载: https://ftp.gnu.org/gnu/wget/
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-23: 初始版本，完成 GNU Wget 1.19.1 鸿蒙适配，34/39 测试通过
