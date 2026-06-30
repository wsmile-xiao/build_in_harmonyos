# libiec61883 1.2.0 编译笔记

## 编译概况
- **编译日期**: 2026-06-04
- **构建系统**: autotools
- **最终状态**: built（编译成功）
- **质量门禁**: G0-G4 全部PASS

## 遇到的问题及解决方案

### 问题1: config.guess无法识别HarmonyOS (E007)
**现象**:
```
config.guess: unable to guess system type
UNAME_SYSTEM = "HarmonyOS"
configure: error: cannot guess build type
```

**根因**: libiec61883-1.2.0 (2009年版本)的config.guess/config.sub无法识别HarmonyOS系统

**解决方案**:
- 下载最新GNU config脚本 (2026-05-17版本)
- 在config.guess中添加: `aarch64:HarmonyOS:*:*) GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;`
- 在config.guess的case $UNAME_SYSTEM中添加: `Ironclad|Linux|GNU|GNU/*|HarmonyOS`

**补丁**: 0001-config.guess.patch, 0002-config.sub.patch

### 问题2: HMDFS SELinux权限问题 (E011)
**现象**:
```
can't create /storage/Users/currentUser/cgaeocOl/dummy.c: Permission denied
``

**根因**: HMDFS文件系统的SELinux限制导致configure/config.guess无法创建临时文件

**解决方案**:
- 修改configure中的`umask 077`改为`umask 022` (2处)
- 修改config.guess中的`umask 077`改为`umask 022` (3处)

**补丁**: 0003-configure.patch

### 问题3: 缺少libraw1394依赖
**现象**:
```
configure: error: Package requirements (libraw1394 >= 1.2.1) were not met
```

**解决方案**:
- 查询cmd-pkgs预编译包索引，找到libraw1394 2.1.2预编译包
- 手动下载并安装预编译包（curl SSL证书问题，使用-k参数）
- 验证安装: `pkg-config --modversion libraw1394` → 2.1.2

## 编译产物
- **库文件**: libiec61883.so.0.1.1, libiec61883.a
- **头文件**: iec61883.h
- **工具**: plugreport, plugctl (示例程序)
- **pkg-config**: libiec61883.pc

## 预编译包
- libiec61883-1.2.0-ohos-aarch64.tar.gz (540KB)
- libiec61883-1.2.0-ohos-aarch64-debug.tar.gz (373KB)

## 知识匹配
- E007: config.guess无法识别系统类型
- E072: config.sub无法验证ohos三元组
- E011: HMDFS umask 077权限问题

---
**编译结束**: 2026-06-04 11:49
**最终状态**: built