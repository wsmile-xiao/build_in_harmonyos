# todo-txt

## 简介

todo-txt 是一个用纯 Bash 编写的命令行 todo.txt 管理工具，用纯文本文件记录待办事项，支持项目、上下文、优先级、完成和归档等操作。

## 主要特点

- 纯脚本实现，适合轻量级命令行任务管理
- 使用 `todo.txt` / `done.txt` / `report.txt` 明文文件保存数据
- 支持 `+project`、`@context`、优先级和日期字段
- 内置 Bash completion 配置文件

## 编译版本

- **2.13.0** (2026-07-14) — Conan application 配方，打包 `todo.sh`、默认配置和 Bash completion

## 编译信息

- 构建系统: script（无需编译）
- 编译器: 不适用
- 平台: HarmonyOS PC / OHOS aarch64

## OHOS 适配要点

- 上游 `todo.sh` 已使用 `#!/usr/bin/env bash`，无需 shebang 补丁
- 配方打包 `etc/todo/config` 并通过 `TODOTXT_GLOBAL_CFG_FILE` 暴露默认配置路径
- `test_package` 使用独立临时配置执行 `add/list/done/archive`，验证真实 CLI 行为

## 安装产物

- `bin/todo.sh`
- `etc/todo/config`
- `share/bash-completion/completions/todo_completion`

## 使用示例

```bash
todo.sh -d ~/.todo.cfg add "port todo-txt +ohos @build"
todo.sh -d ~/.todo.cfg list
todo.sh -d ~/.todo.cfg do 1
todo.sh -d ~/.todo.cfg archive
```

## 相关链接

- 官网: http://todotxt.org/
- 源码: https://github.com/todotxt/todo.txt-cli
- Release: https://github.com/todotxt/todo.txt-cli/releases/tag/v2.13.0
