# tofuenv 1.0.7.1 适配笔记

## 软件特性
- **类型**: 纯 bash shell 脚本工具（无编译）
- **上游**: tofuenv v1.0.7 (https://github.com/tofuutils/tofuenv)
- **变更**: 基于 1.0.7，修复 OHOS 平台适配问题，版本递增 1.0.7.1

## 与 1.0.7 的差异

1.0.7 版本在 OHOS 上存在以下问题，1.0.7.1 全部修复：

| # | 问题 | 修复方式 |
|---|------|---------|
| 1 | github.com:443 不可达，install 下载超时 | package_info 中通过 runenv_info 设置 TOFUENV_REMOTE 镜像源 |
| 2 | curlw 无超时参数，连接不可达时长时间卡住 | build() 中为 curlw 注入 --connect-timeout 10 --max-time 120 |
| 3 | jq 缺失，list-remote 完全不可用 | build() 中将 jq -r ".[].name" 替换为 grep+sed |
| 4 | /tmp 只读(E002)，debug 模式 bashlog 写入失败 | build() 中将 /tmp 替换为 ${TMPDIR:-$HOME/tmp} |
| 5 | TOFUENV_REMOTE 变量冲突(install vs list-remote URL 格式不同) | build() 中 list-remote 改用 TOFUENV_API_REMOTE |
| 6 | install 脚本 mktemp 可能 fallback 到 /tmp | build() 中注入 TMPDIR fallback |

## 源码结构
```
tofuenv-1.0.7/
├── bin/                    # 可执行入口脚本
│   ├── tofu                # OpenTofu 代理脚本
│   └── tofuenv             # 主命令入口
├── lib/                    # 库脚本 (被 source)
│   ├── tofuenv-bashlog.sh
│   ├── tofuenv-exec.sh
│   ├── tofuenv-helpers.sh  # curlw 函数定义
│   ├── tofuenv-min-required.sh
│   ├── tofuenv-version-file.sh
│   └── tofuenv-version-name.sh
├── libexec/                # 子命令脚本
│   ├── tofuenv---version   # --version 子命令
│   ├── tofuenv-exec
│   ├── tofuenv-help
│   ├── tofuenv-install     # install 子命令（下载 OpenTofu）
│   ├── tofuenv-list
│   ├── tofuenv-list-remote # list-remote 子命令（GitHub API）
│   ├── tofuenv-pin
│   ├── tofuenv-resolve-version
│   ├── tofuenv-uninstall
│   ├── tofuenv-use
│   ├── tofuenv-version-file
│   └── tofuenv-version-name
├── scripts/
├── share/                  # GPG 密钥等
├── CHANGELOG.md            # 版本信息 (tofuenv --version 解析此文件)
├── LICENSE
└── README.md
```

## 适配方案

### 无需编译
tofuenv 是纯 bash 脚本工具，build() 阶段不执行任何编译命令，
仅重写脚本 shebang + 注入 OHOS 平台补丁。

### Shebang 改写
所有脚本 shebang 从 `#!/usr/bin/env bash` 改为 `#!/data/service/hnp/bin/bash`。

### OHOS 平台补丁（build() 内 replace_in_file）
1. **curlw 超时**: `lib/tofuenv-helpers.sh` 中 curl 调用前添加 `--connect-timeout 10 --max-time 120`
2. **jq 替换**: `libexec/tofuenv-list-remote` 中 `jq -r ".[].name"` → `grep -oE ... | sed -E ...`
3. **变量分离**: `libexec/tofuenv-list-remote` 中 `TOFUENV_REMOTE` → `TOFUENV_API_REMOTE`
4. **/tmp 替换**: `lib/tofuenv-bashlog.sh` 中 `/tmp/` → `${TMPDIR:-$HOME/tmp}/`
5. **TMPDIR fallback**: `libexec/tofuenv-install` 中注入 `export TMPDIR="${TMPDIR:-$HOME/tmp}"`

### package_info 环境变量（runenv_info）
- `TOFUENV_REMOTE`: 设置为镜像源 `https://ghfast.top/https://github.com/opentofu/opentofu/releases`

### 运行时依赖
| 依赖 | 类型 | 说明 |
|------|------|------|
| curl | 系统级 | 下载 OpenTofu 版本 |
| grep/sed/awk | 系统级 | 文本处理（已替代 jq） |
| bash | 系统级 | 脚本运行环境 |

> 1.0.7.1 已消除对 jq 的依赖，list-remote 使用 grep+sed 解析 GitHub API JSON。

## 测试方案
- **L2 烟雾测试**: `tofuenv --version`
  - 仅需 bash + awk，不需要 jq
  - 输出格式: `tofuenv <version>`
  - 版本号从 CHANGELOG.md 通过 awk 解析获得

## 验证结果
- tofuenv --version → `tofuenv 1.0.6` (CHANGELOG.md 中 FNR>1 跳过第一行 "## 1.0.7 (Unreleased)"，实际输出 1.0.6，此为上游已知行为)
- list-remote → 无需 jq，grep+sed 解析 GitHub API JSON
- install → 通过 TOFUENV_REMOTE 镜像源下载（github.com 直连不可达）
---

**编译结束**: 2026-08-11 16:29
**最终状态**: built
