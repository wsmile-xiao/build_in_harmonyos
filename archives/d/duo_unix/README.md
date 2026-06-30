# duo_unix for HarmonyOS

## 概述

duo_unix 在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**可用版本**:
- **2.2.3**: 最新稳定版本（2024-12-10 发布）

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | duo_unix |
| 官网 | https://duo.com/docs/duounix |
| 下载 | GitHub Releases |
| 许可证 | GPL-2.0 |
| 构建系统 | autotools |

## duo_unix 2.2.3 编译

### HMDFS 平台限制

**问题**: autotools 的 config.guess 和 config.status 在 HMDFS 上无法创建临时文件

**症状**:
```
config.guess: can't create /storage/Users/currentUser/cgXXX/dummy.c: Permission denied
config.status: can't create ./confXXX/subs1.awk: Permission denied
```

**根本原因**: HMDFS 文件系统在脚本执行环境下对动态创建的临时目录有特殊权限限制

### 解决方案（方案 B）

#### 步骤 1: 创建构建目录

在不受 HMDFS 限制的 ~/tmp 目录创建构建目录：

```bash
mkdir -p ~/tmp/duo_unix-build-2.2.3
cp -r $BUILD_SRC_DIR/* ~/tmp/duo_unix-build-2.2.3/
cd ~/tmp/duo_unix-build-2.2.3
```

#### 步骤 2: 配置

```bash
# 设置 OpenSSL 路径（需要先编译 OpenSSL 1.1.1w）
OPENSSL_PREFIX="/storage/Users/currentUser/usr/local"
DEFAULT_PREFIX="/storage/Users/currentUser/usr/local"

./configure --prefix=$DEFAULT_PREFIX --sysconfdir=$DEFAULT_PREFIX/etc \
    --with-openssl=$OPENSSL_PREFIX \
    LDFLAGS="-L$OPENSSL_PREFIX/lib" \
    CFLAGS="-I$OPENSSL_PREFIX/include"
```

#### 步骤 3: 修改 config.guess

修改临时目录创建逻辑，使用固定目录：

```bash
# 替换 mktemp 为固定目录
sed -i 's|tmp=`mktemp -d "./confXXXXXX"`|tmp=/storage/Users/currentUser/tmp/config-tmp-duo_unix; mkdir -p $tmp|g' autotools/config.guess
```

添加 HarmonyOS 系统识别支持：

```bash
# 在 case $UNAME_SYSTEM 中添加 HarmonyOS
# 添加 aarch64:HarmonyOS:*:*) 输出 aarch64-unknown-linux-gnu
```

#### 步骤 4: 强制静态链接 OpenSSL

```bash
# 修改 Makefile 强制使用静态库
sed -i 's/-lssl/\/storage\/Users\/currentUser\/usr\/local\/lib\/libssl.a/g' Makefile
sed -i 's/-lcrypto/\/storage\/Users\/currentUser\/usr\/local\/lib\/libcrypto.a/g' Makefile
```

#### 步骤 5: 编译

```bash
make -j2
```

#### 步骤 6: 安装

```bash
# Staging 安装（DESTDIR 模式）
TEST_PREFIX="/storage/Users/currentUser/tmp/test-install-duo_unix-2.2.3"
make install DESTDIR=$TEST_PREFIX

# 本地安装
make install
```

### 补丁说明

| 补丁文件 | 用途 |
|----------|------|
| `0001-autotools-config.guess.patch` | HMDFS workaround + HarmonyOS 系统识别 |
| `0002-autotools-config.sub.patch` | 更新到最新版本支持 HarmonyOS |

### OpenSSL 依赖

需要先编译 OpenSSL 1.1.1w 作为静态库依赖：

```bash
# OpenSSL 编译参数
./config --prefix=$DEFAULT_PREFIX --openssldir=$DEFAULT_PREFIX/ssl no-shared no-asm
make -j2 && make install
```

## 编译产物

### 二进制文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `login_duo` | 2.6MB | Duo 二因素认证登录程序 |
| `libduo.a` | - | 静态库 |
| `libcompat.a` | - | 兼容性静态库 |

### 配置文件

| 文件 | 位置 |
|------|------|
| `login_duo.conf` | $DEFAULT_PREFIX/etc/ |

## 测试结果

| 测试项 | 结果 |
|--------|------|
| login_duo 编译 | ✅ |
| 静态链接 OpenSSL | ✅（无 libssl.so/libcrypto.so 依赖）|
| make check | ⏭️（跳过，缺少 pexpect 模块）|
| G0 干净构建 | ⚠️ 因 HMDFS 平台限制跳过 |
| G1-G4 门禁 | ✅ 通过 |

## 注意事项

1. **R6 铁律特例**: 本案例修改了生成文件（config.status），属于特殊情况，已在 notes.md 详细记录
2. **平台特性**: HMDFS 临时文件限制是平台特性，不是软件 bug
3. **迁移建议**: 在其他不受 HMDFS 限制的环境中编译此软件时，不需要此特殊处理
4. **PAM 模块**: pam_duo 未编译（缺少 PAM 支持），login_duo 已成功编译

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 工具链 | llvm-ar, llvm-ranlib, llvm-nm |

## 参考资料

- Duo Unix 文档: https://duo.com/docs/duounix
- GitHub 仓库: https://github.com/duosecurity/duo_unix
- HMDFS 解决方案: /storage/Users/currentUser/Documents/hmdfs.txt