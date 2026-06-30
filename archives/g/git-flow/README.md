# Git Flow (AVH Edition)

## 软件说明

Git Flow 是一组 Git 扩展，为 Vincent Driessen 的分支模型提供高级仓库操作。AVH Edition 是原始 git-flow 的增强版本，包含更多功能和改进。

## 功能概述

- **分支管理**：自动创建和管理 feature、release、hotfix、support 分支
- **版本控制**：简化版本发布和标签管理
- **工作流自动化**：提供标准化的开发工作流程
- **Hook 支持**：支持自定义 hook 脚本扩展功能

## OHOS 适配

### 关键问题

1. **E098 - install 命令缺失**：
   - 鸿蒙系统 toybox 不包含 install 命令
   - 解决方案：使用 `cp + chmod` 手动替代
   - git-flow 是纯脚本，install 命令的本质是 cp + chmod

2. **权限设置**：
   - git-flow 主脚本需要 755（可执行）
   - 子脚本需要 644（被 git-flow source 调用）
   - Hook 文件需要 644

3. **DESTDIR 不支持**：
   - Makefile 不支持 DESTDIR 变量
   - 需要手动构造路径：prefix=$TEST_PREFIX$DEFAULT_PREFIX

### 与 Linux 的差异

- **无编译步骤**：纯 Shell 脚本，直接安装
- **无 ELF 二进制**：无需签名、RPATH、strip
- **跨平台兼容**：#!/bin/sh shebang，适配所有 Unix 系统

## 依赖关系

### 编译依赖
- 无（纯脚本）

### 运行依赖
- **git**：必须，git-flow 是 git 的扩展
- **sh**：#!/bin/sh，系统自带

## 参考资料

- 官方仓库：https://github.com/petervanderdoes/gitflow-avh
- 分支模型：https://nvie.com/posts/a-successful-git-branching-model/
- 文档：https://github.com/petervanderdoes/gitflow-avh/wiki