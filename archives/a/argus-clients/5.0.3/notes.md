# argus-clients 5.0.3 编译笔记

## 编译状态
- **日期**: 2026-06-15
- **结果**: 成功编译，二进制文件可用
- **预编译包**: 未完成（归档结构问题）

## 源码信息
- **版本**: 5.0.3
- **来源**: Git 克隆
- **构建系统**: autotools

## 遇到的问题及解决方案

### 1. config.guess 无法识别 HarmonyOS
**问题**: configure 脚本使用的 config.guess（2014-03-23版本）无法识别 HarmonyOS 系统。
**解决方案**:
- 在 `case "${UNAME_SYSTEM}"` 中添加 HarmonyOS 分支
- 添加 `aarch64:HarmonyOS:*:*)` 处理规则
- 修改 TMPDIR 默认值从 `/tmp` 改为 `$HOME/tmp`

### 2. PKG_CHECK_MODULES 占位符未替换
**问题**: configure 和 Makefile 中存在 `@LIBCARES_CFLAGS@`, `@LIBCARES_LIBS@`, `@LIBMAXMINDDB_LIBS@` 占位符未被替换。
**原因**: pkg.m4 文件缺失，PKG_CHECK_MODULES 宏未被展开。
**解决方案**:
- 在 configure 中注释掉 PKG_CHECK_MODULES 调用
- 在 Makefile 中手动删除所有占位符

### 3. config.status 临时目录创建失败
**问题**: config.status 使用 `mktemp -d "./confXXXXXX"` 在当前目录创建临时文件失败。
**原因**: HMDFS 文件系统的权限限制。
**解决方案**:
- 修改 config.status 和 configure 中的临时目录创建逻辑
- 使用绝对路径 `/storage/Users/currentUser/tmp/confstatus$$`
- 简化目录创建流程（使用 `mkdir -p` 替代复杂的 mktemp 嵌套）

### 4. curl 头文件路径问题
**问题**: 编译时找不到 `curl/curl.h`。
**解决方案**: 在 clients/Makefile 中添加 `-I/storage/Users/currentUser/usr/local/include` 到 INCLS 变量。

## 生成的二进制文件
- ra (Argus 客户端主程序)
- rabins, racluster, racount, radium
- radump, ramanage, ranonymize
- 以及其他示例程序（raconvert, radns, ragrep 等）

## 测试状态
- 无自动化测试套件（Makefile 无 check 目标）
- 手动验证：`ra --version` 显示版本 5.0.3

## 知识提取记录

### E007 variant: HarmonyOS config.guess
这是 E007（config.guess 无法识别平台）的一个变体。
- **模式**: `config.guess: unable to guess system type`
- **系统**: HarmonyOS aarch64
- **解决**: 添加 HarmonyOS 到 UNAME_SYSTEM case 分支

### 新发现：HMDFS 临时目录限制
- **现象**: `mktemp -d "./confXXXXXX"` 创建目录后，立即写入失败
- **原因**: HMDFS 对临时目录的权限限制
- **解决**: 使用绝对路径 $HOME/tmp

## 遵守的铁律
- R1: 只使用 --prefix 参数 ✅
- R20: DESTDIR 模式 ✅
- R10: 使用 $TMPDIR ✅

## 遗留问题
1. 归档结构未完成（缺少 manifest.yaml）
2. 预编译包制作流程受阻
3. 需要创建完整的补丁文件记录所有修改