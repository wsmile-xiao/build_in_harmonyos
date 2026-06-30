# AqBanking

## 简介

AqBanking 是一个用于在线银行功能和金融数据导入/导出的库。它提供了多种银行协议的后端支持（如 HBCI、EBICS 等），以及多种数据格式的导入/导出器（如 SWIFT、SEPA、CSV 等）。

## 功能概述

- **银行协议后端**：AQHBCI（德国 Home Banking Computer Interface）、AQEBICS（EBICS 协议）、AQOFXCONNECT（OFX 协议）
- **数据导入/导出**：SWIFT（MT940/MT942）、SEPA（XML）、CSV、CAMT、CTXFILE
- **银行信息查询**：德国银行信息数据库
- **命令行工具**：aqbanking-cli、aqhbci-tool4

## OHOS 适配

### 依赖链

```
gmp → libgpg-error → libgcrypt → libtasn1 → nettle → gnutls → gwenhywfar → aqbanking
```

### 关键适配点

1. **gmp 必须使用 PIC 编译**：aqbanking 需要动态链接 gmp，静态库必须使用 `-fPIC` 编译
2. **修复 E007 平台识别**：更新 config.guess/config.sub 到最新版本
3. **选择后端**：使用 `--with-backends="aqhbci aqnone"` 禁用 EBICS，避免 xmlsec1 依赖
4. **umask 修复**：configure 中 `umask 077` 改为 `umask 022` 解决 HMDFS 权限问题

### 已知问题

- EBICS 后端需要 xmlsec1，当前未编译该依赖
- 部分测试用例可能需要网络连接

## 依赖

### 编译依赖

| 软件 | 版本 | 说明 |
|------|------|------|
| gwenhywfar | >= 5.14.0 | 核心依赖库 |
| gmp | >= 2.9.8 | GNU 多精度算术库（需 PIC） |
| gnutls | >= 2.9.8 | TLS 加密库 |
| libgcrypt | >= 1.11.0 | 加密库 |
| libgpg-error | >= 1.55 | 错误处理库 |

### 运行依赖

编译依赖即运行依赖，无额外依赖。

## 功能验证

```bash
# 验证安装
aqbanking-cli --version
aqhbci-tool4 --version

# pkg-config 验证
pkg-config --modversion aqbanking
```

## 参考

- 官网：https://www.aquamaniac.de/rdm/projects/aqbanking
- 源码：https://www.aquamaniac.de/rdm/projects/aqbanking/files