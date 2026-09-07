# plowshare

> 文件分享站点命令行工具与引擎（多线程下载/上传/删除/网盘列表/链接探测/模块管理）

## 简介

plowshare 是一套用 **Bash** 编写（无任何 C/C++ 源码）的命令行工具集，用于管理主流文件分享站点：
- **plowdown** — 从分享站点批量下载文件
- **plowup** — 上传文件到分享站点
- **plowdel** — 删除已上传的文件
- **plowlist** — 列出网盘目录/下载链接列表
- **plowprobe** — 检查链接类型、文件名与大小等元数据
- **plowmod** — 模块仓库安装/更新/状态管理

所有工具共享 `core.sh` 核心函数库（curl 封装、重试、日志、临时文件等）。

## TIP: 版本与模块的现状

- 上游 **2.1.7 之后已停止维护**（最后 push 2021-06）。
- **2.1.7 起 upstream 不再随包分发 host 模块**（`src/modules/` 仅含 1 个 `config` 占位文件）。
  全部网盘模块移入独立仓库 `mcrapet/plowshare-modules-legacy`，由 `plowmod --install` 在运行时拉取到
  `~/.config/plowshare/modules.d/`。因此**离线/无外部模块时，plowdown/plowup 等真实下载上传不可用**，
  但 6 个 CLI 与 plowmod 模块管理机制本身可正常安装与运行。

## OHOS 适配

- 纯 Bash 脚本，无编译、无 ELF 签名/strip/RPATH 需求。
- 打包为脚本型工具（参考 `prettyping` 模式）：`src/*.sh` 直接复制到 Conan package `bin/`，
  脚本通过 `source "$LIBDIR/core.sh"` 且 `LIBDIR` 取脚本自身目录，因此 `core.sh` 必须与工具脚本同目录。
- 版本信息通过替换 `declare -r VERSION='GIT-snapshot'` 注入 `2.1.7`，`--version` 输出可验证。
- 脚本 shebang 为 `#!/usr/bin/env bash`（上游原样），运行时 bash 由系统 PATH 提供
  （HarmonyOS 上为 `/data/service/hnp/bin/bash`），不声明为 Conan 依赖（同 prettyping 先例）。
- 运行时需 `curl`（SSL），由 Conan 依赖 `curl/8.15.0` 提供；`recode`/`perl` 编码转换与 JS 解释器为可选（多模块需）依赖。

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| bash (>=4.1) | 系统运行时 | PATH 提供（/data/service/hnp/bin/bash），非 Conan 依赖 |
| curl (>=7.24, SSL) | Conan 运行时 | curl/8.15.0 已收录 |
| openssl | Conan override | 3.5.6.1.1（override=True 锁定传递依赖链，CI 已编译通过） |
| coreutils / sed / grep / make | 系统（构建机） | 仅在打包期使用，Makefile 需 GNU make |
| recode 或 perl+HTML::Entities | 可选 | 文件名编码转换 |
| spidermonkey / rhino | 可选 | 部分模块需 JS 解释器 |

## 参考文献

- 上游源码: https://github.com/mcrapet/plowshare
- Release tarball: https://codeload.github.com/mcrapet/plowshare/tar.gz/refs/tags/v2.1.7
- 模块仓库: https://github.com/mcrapet/plowshare-modules-legacy