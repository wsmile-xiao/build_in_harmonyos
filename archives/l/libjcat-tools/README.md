# libjcat-tools

## 简介

libjcat-tools 是 hughsie/libjcat 项目的命令行工具子包，交付 `jcat-tool`
——Jcat（JSON with digital signatures）文件查看/签名/验证 CLI，主要面向
fwupd 等固件更新工具链的签名数据检查。

## 主要功能

- `jcat-tool info`：查看 Jcat 文件信息
- `jcat-tool self-sign`：添加自签名
- `jcat-tool sign`：PKCS7 签名
- `jcat-tool import/export`：签名导入导出
- `jcat-tool verify`：验证签名（GPG/PKCS7/Ed25519 引擎）
- `jcat-tool add-alias/remove-alias`：别名管理

## 版本信息

- 当前编译版本：0.2.3
- 许可证：LGPL-2.1+

## 依赖

- glib/2.84.0.1（gio-2.0 / gio-unix-2.0）
- json-glib/1.10.6
- gpgme/1.24.0（GPG 引擎）
- gnutls/3.8.10（PKCS7 / Ed25519 引擎）

## 归档版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.2.3 | built | 2026-09-19 |

## 相关链接

- 源码：https://github.com/hughsie/libjcat
