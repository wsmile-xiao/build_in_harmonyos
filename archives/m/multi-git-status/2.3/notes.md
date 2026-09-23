# multi-git-status 2.3 — HarmonyOS PC（aarch64, os=OHOS）适配笔记

## 基本信息

- 上游软件：multi-git-status / mgitstatus 2.3
- 源码来源：Debian 官方存档 `https://deb.debian.org/debian/pool/main/m/mgitstatus/mgitstatus_2.3+dfsg.orig.tar.xz`
- sha256：`dfa5a7e4c9c2de25819643aa16e3492e16f9cba7cf89dfe12a6b8769dff3c3e4`
- 来源变更：GitHub 原仓库 `fboender/multi-git-status` 当前返回 404；Debian trixie/sid 收录同版本源码，因此采用 Debian 官方存档作为权威镜像。源码实测 `VERSION="2.3"`，`mgitstatus --version` 输出 `v2.3`。
- 类型：纯 POSIX shell 命令行工具，无编译系统依赖。

## Conan 适配

- `package_type="application"`，`package_id()` 使用 `self.info.clear()`。
- `build()` 仅执行 `apply_conandata_patches`。
- `package()` 显式安装 `mgitstatus`、`mgitstatus.1` 和 `LICENSE.txt`，不整目录拷贝；脚本显式 chmod 0755。
- `includedirs=[]`、`libdirs=[]`、`bindirs=["bin"]`。
- conandata 版本键使用引号 `"2.3"`，避免 YAML 将小数解析成浮点键。
- 软件级 `commands.json` 声明 `mgitstatus` 命令。
- 无 Conan 依赖。运行时依赖为系统命令：sh、git、find、ls、awk、sed、grep、sort、uniq、tr、cut、cat、printf、wc 等。

## 补丁

- `0001-portability.patch`：将 `#!/bin/sh` 改为 `#!/usr/bin/env sh`，并在 `id` 命令不存在时跳过 ownership 检查。HarmonyOS 沙箱实测没有 `/bin/bash`，同时本地 shell 环境中 `id` 命令不可用；有 `id` 时保持上游行为不变。该补丁不使用平台宏。
- 本地补丁应用验证通过。

## 测试

- 上游 `Makefile test` 依赖 shellcheck 静态检查；本适配未将 shellcheck 纳入 build，因为它是开发期检查工具而非运行时依赖。该事实和命令记录在 `test_package/MANIFEST.yml` 与 PR 正文。
- 新增 `test_mgitstatus.sh`：
  1. 执行 `mgitstatus --version`，断言输出为 `v2.3`；
  2. 创建真实 Git 仓库，提交基础文件后制造未提交修改，扫描并断言输出 `Uncommitted changes`。
- 测试脚本使用 `set -euo pipefail`，并使用进程级 `GIT_CONFIG_COUNT` 豁免测试仓库，未修改全局 Git 配置。

## W0

- `conan download --only-recipe multi-git-status/2.3 -r=ohpcd` 返回远端已知限制 `system acceleration policy not enabled`，未得到配方存在证据。
- `archives/m/multi-git-status/` 初始不存在，SUMMARY.md 无该库记录；结合智能任务平台正常认领，三证据支持未发布。

## 已知限制

- Debian 存档是 GitHub 原仓库不可访问时的权威同版本源码镜像。
- 上游 shellcheck 检查未在 Conan 构建阶段执行；适配测试覆盖打包命令版本和核心扫描行为。
- 运行 `git` 扫描需要系统提供 Git 命令。
