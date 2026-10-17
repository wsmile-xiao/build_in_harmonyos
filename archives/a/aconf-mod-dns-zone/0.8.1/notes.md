# aconf-mod-dns-zone 0.8.1 适配笔记

## 编译环境

- 构建系统: custom
- 编译日期: 2026-08-11
- 编译器: 主包无需编译；test_package 使用 clang
- 状态: published

## 适配方式

`aconf-mod-dns-zone` 是 aconf 的 DNS zone 配置模块，上游源码位于：

`aconf/modules/dns-zone.lua`

本包无 C/C++ 主包编译过程，Conan 配方直接从 aconf 0.8.1 官方源码中提取并打包 `dns-zone.lua`。

模块安装至：

`usr/share/lua/5.4/aconf/modules/dns-zone.lua`

## 依赖版本

- aconf/0.8.1

`dns-zone.lua` 通过 `require('aconf.model')` 使用 aconf 核心 Lua 模块。

## 源码修改

无源码补丁。

## 验证方式

test_package 共进行 2 项验证：

1. `dns-zone.lua` 正确打包并存在；
2. `dns-zone.lua` 包含对 `aconf.model` 的引用。

## 注意事项

- 本包为纯 Lua 配置模块，无 configure、cmake 或 make 编译过程。
- Lua 模块路径与现有 `aconf/0.8.1` 的 Lua 5.4 制品布局保持一致。
