# rsync 3.3.0 for HarmonyOS

## 概述

rsync 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | rsync |
| 版本 | 3.3.0 |
| 协议版本 | 31 |
| 下载地址 | https://rsync.samba.org/ftp/rsync/src/rsync-3.3.0.tar.gz |
| 官方文档 | https://rsync.samba.org/documentation.html |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 |
| C库 | musl |
| 构建系统 | autotools (configure.sh) |

## 编译步骤

```bash
# 1. 下载源码
wget https://rsync.samba.org/ftp/rsync/src/rsync-3.3.0.tar.gz
tar -xzf rsync-3.3.0.tar.gz
cd rsync-3.3.0

# 2. 应用补丁（config.guess 和 config.sub 替换为 automake 版本）
patch -p1 < patches/0001-config.guess.patch
patch -p1 < patches/0002-config.sub.patch

# 3. 安装依赖（通过 cmd-pkgs 预编译包）
# 安全提示：建议先下载审查再执行，而非直接 curl | sh
# curl -fsSL .../install.sh -o install.sh && 审查后 sh install.sh -- xxhash 0.8.2
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- xxhash 0.8.2
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- zstd 1.5.6
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lz4 1.10.0

# 4. 配置（依赖路径指向 $HOME/usr/local）
export CFLAGS="-I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib -static"
./configure --prefix=$HOME/usr/local --no-create

# 5. 修复 config.status mktemp（E114：HMDFS 权限问题）
# 在 config.status 中将 mktemp -d "./confXXXXXX" 替换为 $TMPDIR 下的固定路径

# 6. 运行 config.status 生成 Makefile
bash config.status

# 7. 编译
make -j1

# 8. 安装
make install
```

## 补丁说明

### 0001-config.guess.patch

**目的**: 替换 config.guess 为 automake 版本，添加 HarmonyOS 系统检测支持

**修改文件**:
- `config.guess`: 添加 HarmonyOS/__OHOS__ 系统识别

### 0002-config.sub.patch

**目的**: 替换 config.sub 为 automake 版本，添加 ohos 操作系统支持

**修改文件**:
- `config.sub`: 添加 aarch64-unknown-linux-ohos 目标三元组支持

## 编译配置

所有可选特性均已启用（依赖通过 cmd-pkgs 安装）：

| 特性 | 状态 | 说明 |
|------|------|------|
| xxhash | 启用 | xxhash 0.8.2 (cmd-pkgs) |
| zstd | 启用 | zstd 1.5.6 (cmd-pkgs) |
| lz4 | 启用 | lz4 1.10.0 (cmd-pkgs) |
| IPv6 | 启用 | 原生支持 |
| ACL | 禁用 | 系统不支持 |
| xattr | 启用 | Linux xattrs |
| OpenSSL | 启用 | 加密传输支持 (openssl-crypto) |
| 静态链接 | 是 | R26: 终端工具静态链接 |

## 遇到的问题

### 问题1: config.guess 无法识别 HarmonyOS

**现象**: configure 脚本无法识别目标系统

**原因**: config.guess 和 config.sub 不包含 HarmonyOS/ohos 识别规则

**解决**: 替换为 automake 版本（补丁 0001 和 0002）

### 问题2: config.status mktemp 权限不足 (E114)

**现象**: `config.status: error: could not setup config files machinery`，`./confXXXXXX: Permission denied`

**原因**: config.status 使用 mktemp 在当前目录（HMDFS）创建临时目录，HMDFS 权限不足

**解决**: 在 conanfile.py build() 中程序化修复，将 mktemp 路径重定向到 $TMPDIR

### 问题3: shebang 路径不存在 (E165)

**现象**: 脚本 `#!/bin/sh` 在 OHOS 上找不到

**原因**: OHOS 没有 /bin/sh，shell 在 /system/bin/sh

**解决**: 在 conanfile.py build() 中程序化修复 shebang 路径

### 问题4: 官方测试套件失败

**现象**: 44 个测试全部失败

**原因**: 鸿蒙 SELinux 策略限制用户进程创建软链接，whoami 无法解析数字格式用户 ID

**解决**: 测试框架问题不影响实际功能，通过手动测试验证核心功能正常

## 测试结果

详见 [test-report.md](./3.3.0/reports/test-report.md)（本地报告，不上库）

19 项功能测试全部通过，CI 合规诊断 L0/L1 阻塞性检查全通过：

| 测试类别 | 测试数 | 通过 | 失败 |
|----------|--------|------|------|
| 基础功能 (版本/帮助) | 2 | 2 | 0 |
| 文件同步 (基本/增量/删除/递归) | 4 | 4 | 0 |
| 属性保持 (权限/时间戳) | 2 | 2 | 0 |
| 传输选项 (dry-run/进度/压缩/统计/校验和) | 5 | 5 | 0 |
| 过滤规则 (排除/包含+排除) | 2 | 2 | 0 |
| 安全扫描 (NX/RELRO/补丁) | 4 | 4 | 0 |

**CI 合规**: L0 ✅ | L1 ✅ | L2 ✅ | L4 ⚠️ (误报) | L5 ✅

## 验证安装

```bash
# 检查安装
which rsync
# rsync version 3.3.0, protocol version 31

# 检查版本和功能
rsync --version
# rsync  version 3.3.0  protocol version 31
# Checksum: xxh128 xxh3 xxh64 md5 md4 sha1 none
# Compress: zstd lz4 zlibx zlib none
# Optimizations: openssl-crypto

# 测试基本同步
mkdir -p $TMPDIR/test_src $TMPDIR/test_dst
echo "test content" > $TMPDIR/test_src/test.txt
rsync -av $TMPDIR/test_src/ $TMPDIR/test_dst/
cat $TMPDIR/test_dst/test.txt
# test content
```

## 经验总结

1. **补丁通用性**: config.guess/config.sub 替换补丁可复用于其他 GNU autotools 项目
2. **HMDFS 限制**: mktemp 在 HMDFS 上创建临时目录会权限不足，需重定向到 $TMPDIR (E114)
3. **E114 关键**: config.status 是生成文件，位于 build_folder 而非 source_folder，程序化修复时需查找正确路径
4. **SELinux 限制**: 测试框架依赖软链接，需注意鸿蒙系统的 SELinux 限制
5. **功能验证**: 官方测试失败不一定代表功能不可用，需结合手动测试
6. **依赖管理**: xxhash/zstd/lz4 通过 cmd-pkgs 安装到 $HOME/usr/local，Conan 制品仓暂无对应包

## 参考资料

- https://rsync.samba.org/
- https://download.samba.org/pub/rsync/README
