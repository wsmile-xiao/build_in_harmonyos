# brag

**版本**: 1.4.3
**语言**: Tcl
**许可证**: GPL-2.0
**主页**: https://brag.sourceforge.net/

## 简介

Brag 是一个用于从 NNTP 新闻组收集和组装多部分二进制附件的命令行工具。支持 uuencode、MIME base64 和 yenc 编码，可配置多连接并行下载。

## HarmonyOS PC 适配

- 纯 Tcl 脚本，无需编译（noarch）
- 依赖：tcl/8.6.14（提供 tclsh8.6 运行时）
- Shebang 修复：`exec tclsh` → `exec tclsh8.6`

## 适配版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.4.3 | built | 2026-08-12 |
