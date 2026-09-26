# igtf-policy-bundle 1.144 — 适配笔记

## 软件简介

IGTF (Interoperable Global Trust Federation) Policy Bundle 是网格计算和科研基础设施
信任锚（CA 证书）的官方分发捆绑包。包含经 IGTF 认证的 CA 证书及关联元数据
（CRL URL、signing_policy、namespaces、info）。

## 适配方式

- **类型**: 纯数据包（无 C/C++ 编译）
- **构建系统**: custom（仅解压并安装证书文件）
- **依赖**: 无（纯数据包）
- **补丁**: 无

## 包内容

- 83 个受信任的 CA 证书（PEM 格式）
- 83 CRL URL 文件
- 83 signing_policy 文件
- 79 namespaces 文件
- 92 info 元数据文件（含 9 个 policy 级 info）
- 1 个 unaccredited CA

## 许可证

CC-BY-3.0 / MPL 1.1
---

**编译结束**: 2026-09-20 19:34
**最终状态**: built
