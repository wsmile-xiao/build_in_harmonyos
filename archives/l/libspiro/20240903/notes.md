# libspiro 20240903 编译笔记

## 编译环境
- HarmonyOS Kernel 1.12.0
- clang 15.0.4
- llvm-ar, llvm-ranlib, llvm-nm

## 关键问题

### 问题 1: config.guess 无法识别 HarmonyOS
**症状**: `./config.guess: unable to guess system type`

**原因**: config.guess 脚本不识别 HarmonyOS 系统（UNAME_SYSTEM="HarmonyOS"）

**解决方案**: 
1. 修改 config.guess line 153: `Linux|GNU|GNU/*|HarmonyOS)`
2. 添加 aarch64:HarmonyOS:*:*) 规则

### 问题 2: HMDFS 文件系统权限问题
**症状**: 
- `cat: -: Permission denied`
- `./config.status: can't create ./conf*/subs1.awk: Permission denied`
- `sort: stat failed: -: Permission denied`

**原因**: HMDFS 文件系统对管道操作和临时文件创建有特殊限制，configure/config.status 无法正常运行

**解决方案**: 手动编译
1. 从 spiro-config.h.in 创建 spiro-config.h
2. 直接使用 clang 编译源文件
3. 使用 llvm-ar 创建静态库

## 编译产物
- libspiro.a (24KB)
- libspiro.so (35KB)
- 头文件: spiro.h, spiro-config.h, bezctx.h, bezctx_intf.h, spiro_intf.h, spiroentrypoints.h
- pkg-config: libspiro.pc

## 验证结果
- pkg-config --modversion libspiro: 20240903 ✓
- 测试程序编译并运行成功 ✓

## 知识提取

### E007: config.guess 不识别平台
- 平台真理，需修改 config.guess 添加 HarmonyOS 支持

### 新问题: HMDFS 管道权限问题
- 现象: cat -, sort -, config.status 临时文件创建失败
- 影响: autotools configure 无法正常运行
- workaround: 手动编译或使用非 HMDFS 目录

