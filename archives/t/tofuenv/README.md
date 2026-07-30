# tofuenv

OpenTofu version manager inspired by [tfenv](https://github.com/tfutils/tfenv).

## 概述

tofuenv 是一个纯 bash shell 脚本工具，用于管理多个 OpenTofu 版本。
支持安装、切换、列出和卸载不同版本的 OpenTofu。

## 运行时依赖

- **jq**（必需）：JSON 解析
- **curl**：下载 OpenTofu 版本
- **grep / sed / awk**：文本处理
- **bash**：脚本运行环境

## OHOS 适配说明

- 所有脚本 shebang 已从 `#!/usr/bin/env bash` 改写为 `#!/data/service/hnp/bin/bash`
- 无需编译，package() 阶段直接复制脚本文件并设置可执行权限
- `tofuenv --version` 通过 awk 解析 CHANGELOG.md 获取版本号
