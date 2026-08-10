# pinentry 1.3.2 编译笔记

## 编译环境
- **构建系统**: autotools
- **编译日期**: 2026-08-08
- **编译器**: clang/clang++
- **状态**: built（Conan配方验证通过）

## 源码信息
- **源码版本**: pinentry-1.3.2
- **源码格式**: tar.bz2
- **下载地址**: https://gnupg.org/ftp/gcrypt/pinentry/pinentry-1.3.2.tar.bz2
- **SHA256**: 8e986ed88561b4da6e9efe0c54fa4ca8923035c99264df0b0464497c5fb94e9e

## 依赖
- libgpg-error/1.55 (Conan管理)
- libassuan/3.0.2 (Conan管理)
- ncurses/6.6 (Conan管理)

## 平台适配（补丁）

### 补丁1: build-aux/config.guess
- 添加 HarmonyOS 系统检测分支（`uname -s` 返回 "HarmonyOS"）
- 输出 `aarch64-unknown-linux-gnu` 作为构建类型

### 补丁2: build-aux/config.sub
- 添加 `ohos*` 到基本OS列表
- 添加 `linux-ohos*` 到kernel-os验证

### 构建时修复: configure (umask fix)
- 将 `umask 077` 改为 `umask 022`（在 conanfile.py build() 方法中使用 replace_in_file）
- 原因: HarmonyOS HMDFS对umask 077创建的目录写入文件时Permission denied
- 不使用补丁: configure是autotools生成的文件，refresh-patch无法正确处理

## 关键适配点

### 1. /bin/sh 问题
HarmonyOS的 /bin/sh 是 toybox sh，不支持 gpgrt-config 使用的 `eval` 等高级特性。
解决方案: 在conanfile.py的build()方法中修复gpgrt-config和libassuan-config的shebang为 /data/service/hnp/bin/bash。

### 2. config脚本路径问题
pinentry的configure使用 AM_PATH_GPG_ERROR 和 AM_PATH_LIBASSUAN 宏检测依赖，
这些宏通过 -config 脚本（gpgrt-config, libassuan-config）而非pkg-config检测。
解决方案: 在conanfile.py的build环境中设置 GPG_ERROR_CONFIG 和 LIBASSUAN_CONFIG 环境变量，
并将依赖bin目录添加到PATH。

### 3. libgpg-error符号缺失问题（已解决）
之前的编译（2026-05-28）遇到libgpg-error符号缺失导致运行时失败。
根因: 平台预编译的libgpg-error未正确链接libintl。
解决方案: 使用Conan管理的libgpg-error/1.55（从制品仓下载预编译包），运行时正常。

## 验证结果

### 编译产物
- pinentry-curses: 主程序（curses界面）
- pinentry-tty: TTY界面程序
- pinentry: 软链接指向pinentry-curses

### 运行验证
```bash
pinentry-curses --version
# pinentry-curses (pinentry) 1.3.2

pinentry-tty --version
# pinentry-tty (pinentry) 1.3.2
```

### Conan验证
- G0: PASS (预构建风险评估)
- G1: PASS (配方完整性)
- G2: PASS (conan create 干净构建)
- G3: PASS (系统同名库隔离)
- G4: PASS (产物完整性)

## 构建: 2026-08-08
最终状态: built
---

**编译结束**: 2026-08-08 01:12
**最终状态**: built
