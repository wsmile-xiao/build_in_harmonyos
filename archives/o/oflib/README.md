# oflib

oflib 是一个用于在用户空间读取 Open Firmware 设备树的轻量级 C 库，提供节点查找、属性读取和大端整数解码接口。

## 功能概述

- 按名称、类型、路径或 phandle 查找设备树节点。
- 读取节点属性并解析 32 位、64 位大端整数。
- 遍历同类型设备并管理节点生命周期。

## HarmonyOS PC 适配

- 使用 HarmonyOS PC 的 Clang 工具链构建 AArch64 共享库。
- 修复旧源码在现代编译器下的重复全局定义，并补齐 `PATH_MAX` 声明。
- 避开上游 Makefile 中硬编码的 `/usr/local` 安装路径和不安全软链接操作。

## 依赖关系

无第三方编译或运行依赖。

## 参考资料

- 上游仓库：http://git.sipsolutions.net/?p=of-lib.git
- 权威源码归档：https://archive.ubuntu.com/ubuntu/pool/universe/o/oflib/
