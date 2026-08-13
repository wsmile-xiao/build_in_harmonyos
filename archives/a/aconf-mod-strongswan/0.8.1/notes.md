# aconf-mod-strongswan 0.8.1 适配笔记

## 编译环境

- 构建系统: custom
- 编译日期: 2026-08-11
- 编译器: 主包无需编译；test_package 使用 Python 文件检查
- 状态: published

## 适配方式

`aconf-mod-strongswan` 是 aconf 的 strongSwan 配置模块，上游源码位于：

`aconf/modules/strongswan.lua`

本包为纯 Lua 模块，无 C/C++ 主包编译过程。

Conan 配方从 aconf 0.8.1 官方源码中提取 `strongswan.lua`，并安装至：

`usr/share/lua/5.4/aconf/modules/strongswan.lua`

## 依赖版本

- aconf/0.8.1

源码中包含：

- `require('aconf.model')`
- `require('aconf.util')`

两项均由 `aconf/0.8.1` 提供，因此无需额外第三方依赖。

## 源码修改

无源码补丁。

## 验证方式

test_package 使用 Python 直接检查最终 Conan 制品，共进行 3 项验证：

1. `strongswan.lua` 是否正确打包并存在；
2. 是否引用 `aconf.model`；
3. 是否引用 `aconf.util`。

## 注意事项

- 本包为纯 Lua 配置模块，无 configure、cmake 或 make 编译过程。
- 不额外编译 C 测试程序，避免依赖 CI 中的 clang/lld 链接环境。
- Lua 模块路径与现有 `aconf/0.8.1` 的 Lua 5.4 制品布局保持一致。
