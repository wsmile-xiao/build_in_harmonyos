# fnt homebrew 适配笔记

## 编译环境
- 构建系统: custom（shell 脚本，无需编译）
- 编译日期: 2026-07-17
- 编译器: 无（shell 脚本项目）
- 状态: built

## 编译步骤
```bash
# 无需编译，直接复制 shell 脚本
# 1. 修复 shebang
# 2. 添加 HarmonyOS 平台检测
# 3. 复制到 bin/ 目录
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /usr/bin/env bash 不存在 | E165: OHOS 无 /usr/bin/env | 改 shebang 为 /data/service/hnp/bin/bash |
| 2 | HMDFS chmod 失败 | HMDFS 安全策略 | 使用 os.system 作为 fallback |
| 3 | GitHub 源码下载超时 | Worker 网络受限 | 使用 CI 镜像 fallback（R39） |

## 源码修改
- `0001-fnt.patch` — 修复 shebang + 添加 HarmonyOS 平台检测

## 依赖版本
- 无外部依赖

## 验证结果
```bash
$ fnt help
Apt for fonts, the missing font manager for macOS/linux
```

## 注意事项
1. fnt 是 shell 脚本项目，无需编译，直接复制脚本文件
2. shebang 已改为 `/data/service/hnp/bin/bash`
3. 添加了 HarmonyOS 平台检测支持