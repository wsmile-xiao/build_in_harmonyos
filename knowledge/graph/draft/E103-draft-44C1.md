# E103: Go link 工具在 HMDFS 上 SELinux 权限限制

## 问题概述

**严重性**: 🔴 致命 (阻塞编译)

**触发工具**: Go link 工具

**影响阶段**: 链接阶段 (linking)

**影响范围**: 所有 Go 项目在 HMDFS 文件系统上的编译

## 错误特征

### 错误日志模式

```
link: mapping output file failed: permission denied
Go build failed: link tool permission denied
fork/exec .../link: permission denied
```

### 典型场景

- 尝试使用 `go build` 编译 Go 项目时
- Go link 工具尝试创建临时文件或映射输出文件时
- 即使 Go 工具链已通过 ELF 签名,仍然失败

## 根因分析

HMDFS(鸿蒙分布式文件系统)的 SELinux 强制访问控制(MAC)策略限制了 Go link 工具的某些操作:

1. **mmap 操作**: link 工具可能需要使用 mmap 来映射文件到内存
2. **临时文件创建**: link 工具需要创建临时文件来存储中间结果
3. **文件映射**: link 工具尝试映射输出文件到特定的内存地址

即使 Go 工具链二进制文件已通过 ELF 签名,SELinux 的系统级安全策略仍然会阻止这些操作。这不是传统的文件权限问题(chmod 无法解决),而是内核级的 SELinux 上下文限制。

## 受影响软件

- **pumba**: Docker 容器混沌测试工具
- **任何使用 `go build` 的 Go 项目**

## 解决方案

### 推荐方案 (优先级 1)

**方案类型**: 平台限制记录

**描述**: Go link 工具在 HMDFS 上遇到 SELinux 权限限制,无法正常工作。目前无即时解决方案,需等待鸿蒙系统更新 SELinux 策略或使用其他编译环境(非 HMDFS)。建议记录为平台限制,不阻塞其他软件编译流程。

**操作步骤**:
1. 记录为平台限制(类似 E046 问题)
2. 在其他环境(非 HMDFS)编译 Go 项目
3. 等待鸿蒙系统 SELinux 策略更新

**自动化**: 不可自动修复

### 回退方案 (优先级 2)

**方案类型**: 变通方案

**描述**: 尝试在 `/tmp` 或其他非 HMDFS 目录编译,但可能仍然无效(因为 link 工具本身受 SELinux 限制)

**命令**:
```bash
export TMPDIR=/storage/Users/currentUser/tmp
go build -v -o /storage/Users/currentUser/tmp/output ./cmd
```

**自动化**: 不可自动修复

## 验证方法

尝试编译任何 Go 项目(如 `go build -v ./cmd`),观察是否出现 "link: mapping output file failed: permission denied" 错误。

## 相关错误

- **E046**: chmod 不生效 SELinux 限制(类似的平台限制)

## 原则引用

- **R10**: 临时文件用 `$TMPDIR`(禁硬编码 `/tmp`)

## 元数据

- **创建日期**: 2026-06-04
- **贡献者**: 44C1
- **触发事件**: pumba 1.1.2 编译失败
- **状态**: 草稿(draft)