# aqbanking 6.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 依赖链编译（顺序）

```
gmp → libgpg-error → libgcrypt → libtasn1 → nettle → gnutls → gwenhywfar → aqbanking
```

### aqbanking 编译命令

```bash
# 解压
tar xzf aqbanking-6.9.2.tar.gz
cd aqbanking-6.9.2

# 修复 config.guess/config.sub（E007）
curl -fsSL 'https://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.guess;hb=HEAD' > build-aux/config.guess
curl -fsSL 'https://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.sub;hb=HEAD' > build-aux/config.sub

# 修复 umask（E011）
sed -i 's/umask 077/umask 022/g' configure

# 配置
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export DEFAULT_PREFIX=/storage/Users/currentUser/usr/local
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
export CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
./configure --prefix=$DEFAULT_PREFIX --with-backends="aqhbci aqnone"

# 编译
make -j2

# 安装（staging）
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-aqbanking-6.9.2

# 安装（本地）
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gmp 需要重新编译 PIC | aqbanking 动态链接 gmp 需要 PIC 编译的静态库 | 使用 `CFLAGS="-fPIC" --enable-shared` 重新编译 gmp |
| 2 | gnutls 下载失败 | GNU FTP 上只有旧版本 3.1.5 | 从 gnupg.org 下载最新版 3.8.10 |
| 3 | gwenhywfar configure 超时 | PKG_CHECK_MODULES 宏未展开 | 手动替换 Makefile 中的变量占位符 |
| 4 | gwenhywfar 缺少 localcharset.h | 缺少 libiconv 依赖 | 安装 libiconv 预编译包 |
| 5 | aqbanking 缺少 xmlsec1 | EBICS 后端依赖 xmlsec1 | 使用 --with-backends 禁用 EBICS |
| 6 | HMDFS 硬链接失败 | 文件系统不支持硬链接 | 手动复制 .so 文件替代 libtool 硬链接 |
| 7 | gmp 无 pkg-config | gmp 不提供 pkg-config 文件 | 手动创建 gmp.pc |

## 源码修改

### 0001-fix-config-guess.patch

更新 build-aux/config.guess 和 build-aux/config.sub 到最新版本，支持 `aarch64-unknown-linux-ohos` 平台识别。

### 0002-fix-umask.patch

修改 configure 中的 `umask 077` 为 `umask 022`，解决 HMDFS 文件系统权限问题。

## 依赖版本

| 软件 | 版本 | 安装方式 |
|------|------|---------|
| gmp | 6.3.0 | 手动编译 PIC |
| libgpg-error | 1.55 | 手动编译 |
| libgcrypt | 1.11.0 | 手动编译 |
| libtasn1 | 4.21.0 | 预编译包 |
| nettle | 3.10.2 | 预编译包 |
| gnutls | 3.8.10 | 手动编译 |
| libiconv | 1.17 | 预编译包 |
| gwenhywfar | 5.14.1 | 手动编译 |

## 验证结果

```bash
$ pkg-config --modversion aqbanking
6.9.2

$ pkg-config --modversion gwenhywfar gnutls gmp libgcrypt
5.14.1
3.8.10
6.3.0
1.11.0

$ aqbanking-cli --version
aqbanking-cli v6.9.2.0stable

$ aqhbci-tool4 --version
aqhbci-tool4 v6.9.2.0stable
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aqbanking-6.9.2-ohos-aarch64.tar.gz | ~2.6MB | 预编译包 |

## 注意事项

1. **gmp 必须使用 PIC 编译**：否则 aqbanking 动态链接时会出现 R_AARCH64 重定位错误
2. **禁用 EBICS 后端**：避免 xmlsec1 依赖，使用 `--with-backends="aqhbci aqnone"`
3. **gmp pkg-config**：需要手动创建 gmp.pc 文件
4. **HMDFS 限制**：不支持硬链接，需手动复制共享库文件