# rlwrap 0.47.1 编译笔记

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 架构: aarch64
- 编译器: clang
- 依赖: readline 8.2, ncurses 6.4

## 关键问题及解决

### 1. config.guess 不识别 HarmonyOS
- **问题**: autotools 的 config.guess 无法识别 HarmonyOS 系统
- **解决**: 修改 tools/config.guess，添加 HarmonyOS 检测逻辑，返回 `aarch64-unknown-linux-musl`
- **知识图谱**: E007 平台识别问题

### 2. HMDFS 文件系统权限限制
- **问题**: config.status 无法在当前目录创建临时文件（HMDFS 特殊限制）
- **解决**: 手动创建 config.h 和 Makefile，绕过 autotools 的临时文件机制
- **平台限制**: HMDFS 不支持在某些位置创建临时目录

### 3. 缺少 libptytty
- **问题**: configure 报错缺少 libptytty 库
- **解决**: 使用 `--without-libptytty` 参数，使用内置的 ptytty.c 代码

### 4. 缺少宏定义
- **问题**: 编译时缺少 DATADIR 等宏定义
- **解决**: 在 config.h 中添加必要的宏定义

## 编译参数
- configure: `--prefix=/storage/Users/currentUser/usr/local --without-libptytty`
- CFLAGS: `-I/storage/Users/currentUser/usr/local/include -Wall -O2`
- LDFLAGS: `-L/storage/Users/currentUser/usr/local/lib -Wl,-rpath,/storage/Users/currentUser/usr/local/lib`
- LIBS: `-lutil -lreadline -ltinfo`

## 验证结果
- 版本: rlwrap 0.47
- 功能: readline wrapper，为交互式命令添加 readline 支持
- 测试: `rlwrap --version` 正常输出

---
**编译开始**: 2026-05-21 23:02
**编译结束**: 2026-05-21 23:17
**最终状态**: built（手动绕过 autotools 限制成功）
