# aconf-mod-openssh 0.8.1 适配笔记

## 编译环境

- 构建系统: custom
- 编译日期: 2026-08-11
- 编译器: 无需编译（纯 Lua 模块）
- 状态: published

## 适配方式

`aconf-mod-openssh` 是 aconf 的 OpenSSH 配置模块，上游源码位于：

`aconf/modules/openssh.lua`

该软件无 C/C++ 编译过程，Conan 配方直接从 aconf 0.8.1 官方源码包中提取 `openssh.lua`，并安装到：

`usr/share/lua/5.4/aconf/modules/openssh.lua`

## 依赖版本

- aconf/0.8.1

`openssh.lua` 通过 `require('aconf.model')` 使用 aconf 核心模块。

## 源码修改

无源码补丁。

## 验证方式

test_package 验证：

1. `openssh.lua` 已正确安装到 Lua 5.4 模块目录。
2. `openssh.lua` 中包含对 `aconf.model` 的引用。

## 注意事项

- 本包为纯 Lua 模块，不需要 configure、cmake 或 make 编译。
- 上游源码与 aconf/0.8.1 使用同一个官方源码包。
- 制品仓 aconf/0.8.1 使用 Lua 5.4 路径，因此本模块同样安装到 lua/5.4。
