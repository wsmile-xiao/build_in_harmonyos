# libjcat

## 简介

libjcat 是一个 JSON 文件签名验证库，主要用于 fwupd 等固件更新工具，用于验证 JSON 文件的完整性和真实性。

## 主要功能

- JSON 文件签名验证
- 支持多种签名算法（GPG、GnuTLS）
- 提供 jcat-tool CLI 工具

## 版本信息

- 当前编译版本：0.2.6
- 许可证：LGPL-2.1+

## 依赖

- GLib 2.84.0
- json-glib 1.5.1（Meson subproject fallback）

## 编译选项

- `-Dgpg=false`：禁用 GPG 支持
- `-Dgnutls_pkcs7=false`：禁用 GnuTLS PKCS7
- `-Dgnutls_ed25519=false`：禁用 GnuTLS Ed25519
- `-Dintrospection=false`：禁用 GObject introspection
- `-Dtests=false`：禁用测试

## 归档版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.2.6 | published | 2026-06-04 |

## 相关链接

- 源码：https://github.com/hughsie/libjcat