# aconf-mod-dnsmasq 0.8.1 适配笔记

## 编译环境

- 构建系统: custom
- 编译日期: 2026-08-11
- 编译器: 主包无需编译；test_package 使用 Python 文件检查
- 状态: published

## 适配方式

`aconf-mod-dnsmasq` 是 aconf 的 Dnsmasq 配置模块，上游对应两个主要文件：

- `aconf/modules/dnsmasq.lua`
- `augeas/aconf_dnsmasq.aug`

本包无 C/C++ 主包编译过程，Conan 配方直接从 aconf 0.8.1 官方源码中提取上述文件。

Lua 模块安装至：

`usr/share/lua/5.4/aconf/modules/dnsmasq.lua`

Augeas lens 安装至：

`usr/share/aconf/augeas/aconf_dnsmasq.aug`

## 依赖版本

- aconf/0.8.1

`dnsmasq.lua` 通过 `require('aconf.model')` 使用 aconf 核心 Lua 模块。

## 源码修改

无源码补丁。

## 验证方式

test_package 共进行 3 项验证：

1. `dnsmasq.lua` 正确打包并存在；
2. `dnsmasq.lua` 包含对 `aconf.model` 的引用；
3. `aconf_dnsmasq.aug` 正确打包并存在。

## 注意事项

- 本包为纯 Lua/Augeas 配置模块，无 configure、cmake 或 make 编译过程。
- Lua 模块路径与现有 `aconf/0.8.1` 的 Lua 5.4 制品布局保持一致。
