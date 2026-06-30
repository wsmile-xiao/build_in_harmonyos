# freeipmi 1.6.10 适配笔记

## 编译环境
- 构建系统: CMake（手动创建）
- 编译日期: 2026-05-22
- 编译器: clang/clang++ (15.0.4)
- 状态: built（核心库成功）

## 编译历程

### 第一次尝试：autotools（失败）
使用 autotools 构建系统失败，原因是 config.status 无法在 HMDFS 上创建临时文件。

**核心问题**：config.status 在创建临时文件时遇到 HMDFS 或 SELinux 权限限制。
```
./config.status[1122]: can't create /storage/Users/currentUser/tmp/confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**：autotools 设计缺陷 + HMDFS/SELinux 安全限制，无法在 HarmonyOS 上正常运行。

### 第二次尝试：CMake（部分成功）
手动创建 CMakeLists.txt 构建系统，绕过 autotools 限制。

**成功编译的产物**：
- 4 个共享库（全部成功）
- 6 个静态库（全部成功）
- 工具程序未完成（链接问题）

## CMake 编译关键修复

| # | 问题 | 解决方案 | 结果 |
|---|------|----------|------|
| 1 | struct timeval 未定义 | config.h.in 添加 TIME_WITH_SYS_TIME=1 | ✅ |
| 2 | extern inline 与 static inline 冲突 | 禁用 __OPTIMIZE__ 块内的 inline | ✅ |
| 3 | PRINTF_STYLE/UNUSED 宏未定义 | 手动添加宏定义 | ✅ |
| 4 | sys_errlist 未定义 | 使用 strerror 替代 | ✅ |
| 5 | program_invocation_name 未定义 | 添加 extern 声明和实际定义 | ✅ |
| 6 | PIC 链接错误 | 所有静态库添加 POSITION_INDEPENDENT_CODE ON | ✅ |
| 7 | ipmidetect.h 等头文件缺失 | 从 .h.in 手动生成 | ✅ |
| 8 | libgcrypt 符号链接缺失 | 创建 libgcrypt.so 符号链接 | ✅ |
| 9 | config 路径宏未定义 | config.h.in 添加 LIBIPMICONSOLE_CONFIG_FILE_DEFAULT 等 | ✅ |

## 成功编译的产物

### 共享库（4个）
- libfreeipmi.so (5.4M) - IPMI 协议核心库
- libipmiconsole.so (214K) - Serial Over LAN 库
- libipmidetect.so (62K) - IPMI 检测库
- libipmimonitoring.so (94K) - IPMI 监控库

### 静态库（6个）
- libmiscutil.a (175K)
- libdebugutil.a (4.3K)
- libportability.a (48K)
- libparsecommon.a (13K)
- libtoolcommon.a (209K)
- libpingtool.a (23K)

### 工具程序
- bmc-info, ipmi-sensors 等：未完成（链接阶段失败）

## 预编译包

- **路径**: archives/f/freeipmi/1.6.10/packaging/freeipmi-1.6.10-ohos-aarch64.tar.gz
- **大小**: 6.4M
- **包含**: lib/（10个库） + include/（头文件）

## 源码修改

### 1. config/config.guess
添加 HarmonyOS 平台识别（更新到 2023 版本）

### 2. config/config.sub
添加 ohos 支持（更新到 2023 版本）

### 3. CMakeLists.txt（手动创建）
为整个项目创建完整的 CMake 构建系统：
- 根目录 CMakeLists.txt
- 各子模块 CMakeLists.txt（common/, libfreeipmi/, libipmidetect/ 等）
- config.h.in 配置模板

### 4. 头文件手动生成
从 .h.in 模板生成：
- ipmidetect.h
- freeipmi.h
- ipmiconsole.h
- ipmi_monitoring.h

## 补丁文件

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-config-config.guess.patch | platform-support | 更新到 2023 版本，添加 HarmonyOS 识别 |
| 0002-config-config.sub.patch | platform-support | 更新到 2023 版本，添加 ohos 支持 |
| 0003-cmake-toolcommon.patch | build-fix | CMake 工具库链接配置修复 |

## 依赖版本

- clang: 15.0.4
- cmake: 3.28
- make: GNU Make 4.4.1
- libgcrypt: 1.11.0（预编译包）

## 未完成工作

1. **工具程序链接**：bmc-info 等命令行工具链接失败，需要修复 CMakeLists.txt 中的库依赖配置
2. **完整功能测试**：仅有编译产物，未进行功能验证

## 质量修复记录（2026-05-22）

### 软件级归档文件创建
- ✅ 创建 manifest.yaml（软件级元数据 + 版本索引）
- ✅ 创建 README.md（软件描述、功能、OHOS 适配要点）

### ELF 签名修复
- ✅ 使用 ohc-run.py sign-elf 对预编译包中的库文件进行签名
- ✅ 重新打包 freeipmi-1.6.10-ohos-aarch64.tar.gz（已签名）
- 签名文件：libfreeipmi.so, libipmiconsole.so, libipmidetect.so, libipmimonitoring.so

### 补丁修复
- ✅ 删除错误的 0003-cmake-toolcommon.patch（内容为 git diff 帮助信息）
- 说明：CMakeLists.txt 是新增文件，非补丁修改，无法生成标准补丁格式

### 构建系统标记
- ✅ manifest.yaml 中标记 build.system: cmake-manual
- 说明：手动创建 CMake 构建系统，非 autotools 自动生成

### 平台限制记录
- autotools 构建系统不可用（HMDFS/SELinux 限制）
- config.status 无法在 HMDFS 上创建临时文件
- 必须使用手动创建的 CMake 构建系统

## 知识沉淀

### 平台兼容性发现
- **E007 补充**：autotools 的 config.status 无法在 HMDFS 上创建临时文件
- **根因**：HMDFS/SELinux 安全限制
- **影响范围**：所有使用 autotools 的软件
- **Workaround**：使用 CMake 或其他构建系统替代 autotools

### CMake 构建经验
- autotools 项目转换为 CMake 需手动创建大量配置
- 需要手动模拟 autoconf 检测结果（config.h.in）
- 静态库需要 POSITION_INDEPENDENT_CODE 才能链接到共享库

---
**编译结束**: 2026-05-22 12:12
**最终状态**: built
**构建方式**: CMake（手动创建）