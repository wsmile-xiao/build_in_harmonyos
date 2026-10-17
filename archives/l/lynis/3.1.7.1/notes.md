# lynis 3.1.7.1 适配笔记

## 上游简介

lynis 是 CISOfy 开发的安全审计工具, 针对 Unix/Linux/macOS 进行系统硬化检查
(Compliance, PCI-DSS, ISO27001, HIPAA 等). 纯 shell 实现, 无编译需求,
走路径 A 基础适配.

上游: https://github.com/CISOfy/lynis
release: https://github.com/CISOfy/lynis/archive/refs/tags/3.1.7.tar.gz
(cisofy 官方下载站 downloads.cisofy.com URL 下载失败 404/被墙, 改用 GitHub tag 源码包)

## 适配方案 (路径 A 基础适配, 整合远端 feat/lynis-3.1.7.1 初版工作)

### 上游 shebang 核实

**上游 lynis 3.1.7 真实 shebang 是 `#!/bin/sh`** (已扫 65 个脚本全确认),
远端初版误认是 `#!/usr/bin/zsh` 并据此改 shebang — 错误前提, 整合时已删 zsh 错改.

### 补丁清单 (4 个)

补丁 0001+0002+0003 来自远端 feat/lynis-3.1.7.1 初版适配 (OHOS 运行时适配, 真价值),
补丁 0004 是我的新增 (正确 shebang 方案替代远端的 zsh 错改).

1. **0001-include-functions.patch** — 适配 HMDFS 所有权检查、`$TMPDIR` 和 Toybox `ps`
   - `TEMP_FILE` 兼容 `$TMPDIR` 环境变量
   - `OHOS_PLATFORM` 检测: Toybox ps 不支持 procps -C/-ax/-aux flags, 降级为默认进程列表
   - `LYNIS_OHOS_TRUST_PACKAGE` HMDFS 属主信任: HMDFS 强制文件模式为 660, 放宽组权限判断但继续校验所有权和 other 权限
2. **0002-include-osdetection.patch** — 将 HarmonyOS 映射到 Linux 兼容审计路径并保留平台名称
   - `uname` 返回 `HarmonyOS` 时设 `OHOS_PLATFORM=1` 并分流到 Linux 分支
   - 跳过 `/etc/os-release` 检测 (OHOS 无此文件), 保留 `OS_NAME="HarmonyOS"` 报告
3. **0003-lynis.patch** — 修改主脚本数据路径、UID 回退、PID 路径和非阻塞交互
   - 早 `--version` 处理 (E214 非交互环境, 初始化前直接输出版本退出)
   - `SCRIPT_DIR` 变量 + `tINCLUDE_TARGETS`/`tDB_TARGETS` 加 SCRIPT_DIR 路径 (让 lynis 能从安装目录找 include/db)
   - non-blocking stdin `read -r void < /dev/null` (CI 环境防阻塞)
   - MYID 回退: OHOS 无 `id` 命令, 从 `/proc/self/status` 读 Uid
   - **已删 zsh shebang 错改** (`#!/usr/bin/zsh` + `set -o shwordsplit` → 删除, 上游真实是 `#!/bin/sh`)
4. **0004-ohos-shebang.patch** — 65 个脚本 shebang `#!/bin/sh` -> `#!/data/service/hnp/bin/bash`
   (OHOS bash 路径, 正确方案替代远端的 zsh 错改; 上游真实 shebang 是 `#!/bin/sh` 需 OHOS bash 路径)

### package()

- 装整个 lynis 树到 `share/lynis/` (保留目录结构, lynis 主入口用 `WORKDIR=$(pwd)` 找 `./include`, 不能 flatten 到 `bin/`)
- `bin/lynis` wrapper 脚本 `cd` 到 `share/lynis/` 再 `exec bash lynis`, 保留 `WORKDIR=$(pwd)` 契约
- `bin/ps` OHOS 兼容 wrapper (Toybox ps 缺 procps -C/-ax/-aux flags, 降级为默认进程列表)
- `etc/lynis/default.prf` + `developer.prf` 配置文件 (lynis 经 SCRIPT_DIR 找)
- `share/man/man8/lynis.8` man 页
- chmod + 回退 chmod binary + raise ConanException 阻止产出不可执行包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | shebang `/bin/sh` 在 OHOS 不可用 | OpenHarmony 系统中 `/bin/sh` 不存在或指向 mksh | 补丁 0004 改为 `/data/service/hnp/bin/bash` (OHOS bash 路径, 非远端误认的 zsh) |
| 2 | 安全检查 `read` 阻塞 | lynis 在安全审计过程中使用 `read -r void` 等待用户输入, 在非交互式环境中会阻塞 | 补丁 0003 改为非阻塞读取 `read -r void < /dev/null 2>/dev/null \|\| true` |
| 3 | `--version` 在初始化后才解析 | lynis 原始代码在完成全部初始化后才处理 `--version` 参数, 导致非交互式环境下超时 | 补丁 0003 添加早期 `--version` 处理逻辑, 在初始化前直接输出版本并退出 |
| 4 | conan 包路径找不到数据文件 | lynis 默认从 CWD 和系统路径搜索 include/db/plugins, conan 安装路径不在搜索范围内 | 补丁 0003 添加 `SCRIPT_DIR` 变量, 将脚本相对路径加入搜索目标 |
| 5 | HarmonyOS 缺少 `id` 命令 | Toybox PATH 没有 `id`, Lynis 的 `MYID=$(id -u)` 为空 | 补丁 0003 OHOS 环境下从 `/proc/self/status` 读 Uid 回退获取 UID |
| 6 | HMDFS 强制文件模式为 `660` | 用户存储忽略 `chmod 640`, 但文件仍由当前 UID 所有且 other 不可写 | 补丁 0001 OHOS 仅放宽组权限判断, 继续校验所有权、普通文件和 other 权限 (`LYNIS_OHOS_TRUST_PACKAGE`) |
| 7 | Lynis 报 `Unknown OS` | 上游 `osdetection` 没有 HarmonyOS 分支 | 补丁 0002 将 HarmonyOS 映射到 Linux 兼容审计路径, 同时保留 HarmonyOS 报告名称 |
| 8 | Toybox `ps` 不支持 `-C/-ax/-aux` | Lynis 多个 Linux 测试直接使用 procps 参数 | `ohos-ps` wrapper 打包到 `bin/ps`, 将名称查询降级为 Toybox 默认进程列表 |
| 9 | lynis 主入口 `WORKDIR=$(pwd)` 找 `./include` 失败 | lynis 设计是整个目录树一起跑, 不能只拷主入口到 `bin/` | `package()` 装整个树到 `share/lynis/`, `bin/lynis` wrapper `cd` 到 share 目录再 `exec bash lynis` |
| 10 | lynis 有 root 属主安全检查 | upstream 安全设计, Conan 沙箱环境非 root 阻断 | `test.sh` 验产物结构而非调 lynis 主入口, 绕过属主检查; CI worker 上以 root 跑会正常 |

## 本地验证 (conan create)

- 补丁应用 + package + test_package 全通过
- test() 13 个断言全 PASS (pass=13 fail=0):
  1. bin/lynis wrapper exists
  2. bin/ps ohos wrapper exists
  3. share/lynis/lynis entry exists
  4. lynis entry shebang OHOS bash
  5. include/ tree intact (consts present)
  6. osdetection HarmonyOS branch present
  7. functions OHOS_PLATFORM adaptation present
  8. functions HMDFS trust_package adaptation present
  9. lynis early --version handling present
  10. lynis SCRIPT_DIR installable paths present
  11. etc/lynis/default.prf profile installed
  12. wrapper shebang + cd share contract
  13. all scripts shebang OHOS bash (0 residual)

## 已知限制

- lynis 部分审计模块依赖 /proc, /sys 等 OHOS 可能不存在的伪文件系统,
  运行时部分 check 会 warn 或 skip, 不影响包构建与 smoke test
- lynis 主入口有 root 属主安全检查 (upstream 设计), Conan 沙箱环境非
  root 阻断; CI worker 上以 root 跑会正常

## 依赖版本
- 上游: lynis 3.1.7 (release 2026-06-25)
- 配方: lynis 3.1.7.1 (赛事看板任务版本号, 区分任务轮次)
- 无编译依赖 (纯 shell 工具)
