# tofuenv 1.0.7 适配笔记

## 软件特性
- **类型**: 纯 bash shell 脚本工具（无编译）
- **功能**: OpenTofu 版本管理器，支持安装/切换/列出/卸载 OpenTofu 版本
- **构建系统**: 无（custom，直接复制脚本）
- **编译日期**: 2026-07-15

## 源码结构
```
tofuenv-1.0.7/
├── bin/                    # 可执行入口脚本
│   ├── tofu                # OpenTofu 代理脚本
│   └── tofuenv             # 主命令入口
├── lib/                    # 库脚本 (被 source)
│   ├── tofuenv-bashlog.sh
│   ├── tofuenv-exec.sh
│   ├── tofuenv-helpers.sh
│   ├── tofuenv-min-required.sh
│   ├── tofuenv-version-file.sh
│   └── tofuenv-version-name.sh
├── libexec/                # 子命令脚本
│   ├── tofuenv---version   # --version 子命令
│   ├── tofuenv-exec
│   ├── tofuenv-help
│   ├── tofuenv-install
│   ├── tofuenv-list
│   ├── tofuenv-list-remote
│   ├── tofuenv-min-required
│   ├── tofuenv-pin
│   ├── tofuenv-resolve-version
│   ├── tofuenv-uninstall
│   ├── tofuenv-use
│   ├── tofuenv-version-file
│   ├── tofuenv-version-name
│   └── releases            # 预编译版本列表数据 (652KB)
├── scripts/
├── share/                  # GPG 密钥等
├── CHANGELOG.md            # 版本信息 (tofuenv --version 解析此文件)
├── LICENSE
└── README.md
```

## 适配方案

### 无需编译
tofuenv 是纯 bash 脚本工具，build() 阶段不执行任何编译命令，
仅重写脚本 shebang。

### Shebang 改写
所有脚本原始 shebang: `#!/usr/bin/env bash`
OHOS 平台 bash 路径: `/data/service/hnp/bin/bash`
build() 阶段遍历 bin/, libexec/, lib/, scripts/ 目录，
将 shebang 替换为 `#!/data/service/hnp/bin/bash`。

### 打包结构
package() 复制完整目录结构到 package_folder:
- bin/ → 可执行脚本 (chmod 755)
- lib/ → 库脚本
- libexec/ → 子命令脚本 (chmod 755)
- scripts/ → 辅助脚本
- share/ → GPG 密钥等资源
- CHANGELOG.md → 版本信息（tofuenv --version 依赖）
- LICENSE, README.md

### 运行时依赖
| 依赖 | 类型 | 说明 |
|------|------|------|
| jq | 系统级 | JSON 解析，tofuenv 核心功能必需 |
| curl | 系统级 | 下载 OpenTofu 版本 |
| grep/sed/awk | 系统级 | 文本处理 |
| bash | 系统级 | 脚本运行环境 |

jq 在制品仓中为 partial 状态（无 conanfile.py），不声明为 Conan requires()。

## 测试方案
- **L2 烟雾测试**: `tofuenv --version`
  - 仅需 bash + awk，不需要 jq
  - 输出格式: `tofuenv <version>`
  - 版本号从 CHANGELOG.md 通过 awk 解析获得

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 脚本无法执行 | OHOS 无 /usr/bin/env | 重写 shebang 为 /data/service/hnp/bin/bash |
| 2 | --version 失败 | 缺少 CHANGELOG.md | package() 必须打包 CHANGELOG.md |
| 3 | jq 不可用 | jq 非 Conan 包 | 不声明为 requires，标注为系统级依赖 |

## 验证结果
- tofuenv --version → `tofuenv 1.0.6` (CHANGELOG.md 中 FNR>1 跳过第一行 "## 1.0.7 (Unreleased)"，实际输出 1.0.6，此为上游已知行为)
