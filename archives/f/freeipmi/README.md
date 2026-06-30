# FreeIPMI

## 软件简介

FreeIPMI 是 GNU 项目提供的 IPMI（智能平台管理接口）完整实现，提供带内和带外 IPMI 软件功能。IPMI 是一种标准化接口，用于管理系统监控、日志记录、恢复控制和库存管理。

## 主要功能

### 核心库
- **libfreeipmi**: IPMI 协议核心实现库
- **libipmiconsole**: Serial Over LAN (SOL) 控制台库
- **libipmidetect**: IPMI 节点检测库
- **libipmimonitoring**: IPMI 传感器监控库

### 工具程序
- `bmc-info`: BMC 信息查询
- `ipmi-sensors`: 传感器数据读取
- `ipmi-fru`: FRU (Field Replaceable Unit) 信息查询
- `ipmi-locate`: IPMI 设备定位

## OHOS 适配要点

### 平台兼容性
- **构建系统**: 原 autotools 构建系统在 HMDFS 上失败（config.status 无法创建临时文件），需使用手动创建的 CMake 构建系统
- **平台识别**: 需更新 config.guess 和 config.sub 到 2023 版本以支持 HarmonyOS
- **编译器**: 使用 clang/clang++ 15.0.4

### 关键修改
1. 更新 config.guess/config.sub（平台识别）
2. 手动创建 CMakeLists.txt 构建系统
3. 配置 config.h.in（手动模拟 autoconf 检测结果）
4. 从 .h.in 模板手动生成头文件（ipmidetect.h, freeipmi.h, ipmiconsole.h, ipmi_monitoring.h）

### 已知限制
- 工具程序（bmc-info, ipmi-sensors 等）链接阶段未完成
- 预编译包仅包含库文件，不包含可执行程序
- autotools 构建系统不可用（HMDFS/SELinux 限制）

## 依赖关系

### 编译依赖
- **libgcrypt** >= 1.11.0（加密支持）
- **clang** >= 15.0
- **cmake** >= 3.28

### 运行依赖
- libgcrypt（运行时库）

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.6.10 | built | 2026-05-22 | 核心库编译成功，工具程序未完成 |

## 参考资料

- **官方主页**: https://www.gnu.org/software/freeipmi/
- **源码下载**: https://ftp.gnu.org/gnu/freeipmi/
- **文档**: https://www.gnu.org/software/freeipmi/manual/
- **Git 仓库**: https://github.com/chu11/freeipmi-mirror