# prettyping

prettyping is a Bash wrapper around the standard `ping` tool. It replaces each ping response line with a compact, colorful character-based visualization and summary statistics.

## 功能概述
- 封装系统 `ping`，输出更紧凑、更易读。
- 支持彩色/Unicode/多色输出开关。
- 支持全局统计和最近 N 次 ping 统计。
- 支持通过 `--awkbin` 与 `--pingbin` 覆盖运行时工具。

## OHOS 适配
- 项目是纯 Bash 脚本，无 C/C++ 编译步骤。
- 上游脚本已使用 `#!/usr/bin/env bash`，适配无 `/bin/bash` 的环境。
- 打包时直接复制 `prettyping` 到 Conan package `bin/`。
- 消费者测试使用 mock ping，避免依赖外网/ICMP 权限，同时真实执行安装后的 `prettyping`。

## 依赖关系
- 编译依赖：无。
- Conan 依赖：无。
- 运行时依赖：Bash、awk、ping。

## 参考资料
- Homepage: https://github.com/denilsonsa/prettyping
- Release: https://github.com/denilsonsa/prettyping/releases/tag/v1.1.0
- Source: https://codeload.github.com/denilsonsa/prettyping/tar.gz/refs/tags/v1.1.0
