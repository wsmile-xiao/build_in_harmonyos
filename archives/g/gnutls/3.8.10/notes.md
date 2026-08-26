# gnutls 3.8.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 解压（从 gnupg.org 下载）
cd ~/tmp
curl -LO "https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-3.8.10.tar.xz"
tar xJf gnutls-3.8.10.tar.xz
cd gnutls-3.8.10

# 修复 config.guess/config.sub（E007）
curl -fsSL config.guess 最新版本 > build-aux/config.guess
curl -fsSL config.sub 最新版本 > build-aux/config.sub

# 配置
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export DEFAULT_PREFIX=~/usr/local
./configure --prefix=$DEFAULT_PREFIX

# 编译
make -j2

# 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GNU FTP 版本过旧 | GNU FTP 只有 3.1.5 | 从 gnupg.org 下载最新版 3.8.10 |
| 2 | psktool 编译失败 | 缺少 libintl_bindtextdomain | 跳过 psktool，主库已安装 |
| 3 | 平台识别失败 | config.guess 不识别 OHOS | 更新 config.guess/config.sub |

## 验证结果
```bash
$ gnutls-cli --version
gnutls-cli 3.8.10

$ pkg-config --modversion gnutls
3.8.10
```

## 交付物
- gnutls-3.8.10-ohos-aarch64.tar.gz (~3.5MB)
- 包含：certtool, gnutls-cli, ocsptool, libgnutls.so.30.40.4

## 注意事项
- psktool 未编译成功，但不影响 gnutls 主库使用
- 需要链接 libintl 库
---

**编译结束**: 2026-08-25 02:55
**最终状态**: built
