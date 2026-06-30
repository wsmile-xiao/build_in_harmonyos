# Gwenhywfar

## 简介

Gwenhywfar 是一个多功能基础库，提供文件处理、网络通信、数据库访问等功能。是 AqBanking 等软件的核心依赖。

## 功能概述

- **文件处理**：虚拟文件系统、配置文件解析
- **网络通信**：HTTP/HTTPS 客户端、套接字抽象
- **数据库**：数据库抽象层
- **GUI 工具**：图形界面辅助库（可选）
- **命令行工具**：typemaker2、xmlmerge、gcttool

## OHOS 适配

### 依赖链
```
gmp → libgpg-error → libgcrypt → gnutls → gwenhywfar
```

### 关键适配点
1. **修复 PKG_CHECK_MODULES**：Makefile 中变量未展开，需手动替换
2. **禁用 GUI**：使用 --disable-gtk3 避免 GTK3 依赖
3. **libiconv 依赖**：需要安装 libiconv 预编译包
4. **手动复制 .so**：HMDFS 不支持硬链接

### 已知问题
- qt5 GUI 未编译（缺少 Qt5）
- gtk3 GUI 已禁用

## 依赖

### 编译依赖
| 软件 | 版本 | 说明 |
|------|------|------|
| gnutls | >= 2.9.8 | TLS 加密库 |
| libiconv | >= 1.17 | 字符编码转换 |
| gmp | >= 6.3.0 | 多精度算术库 |

## 功能验证
```bash
pkg-config --modversion gwenhywfar
typemaker2 --version
```

## 参考
- 官网：https://www.aquamaniac.de/rdm/projects/gwenhywfar