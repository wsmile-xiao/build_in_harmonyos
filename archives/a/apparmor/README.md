# AppArmor

AppArmor 是一个 Linux 安全模块（LSM）的用户空间工具集，用于强制访问控制（MAC）。

## 软件简介

AppArmor 通过将进程限制在预定义的配置文件中来保护系统，同时允许进程共享文件、行使权限和与其他进程通信。它是 Linux 内核 LSM 框架的一部分。

## 编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 4.1.0 | built | 2026-06-18 | 核心组件编译成功 |

## 组件结构

AppArmor 是一个多组件项目，按以下顺序构建：

1. **libapparmor** - 核心库（LGPL）
2. **binutils** - 基本工具（GPL）
3. **parser** - 策略解析器（GPL）
4. **utils** - Python 工具（GPL）
5. **profiles** - 配置文件

## 鸿蒙平台适配

### 已完成组件

- ✅ libapparmor（核心库）
- ✅ binutils（aa-enabled, aa-exec, aa-features-abi, aa-load, aa-status）

### 待完成组件

- ⏳ parser（策略解析器）
- ⏳ utils（Python 工具）
- ⏳ profiles（配置文件）

### 平台限制

由于 AppArmor 与 Linux 内核 LSM 深度绑定，以下功能在鸿蒙平台可能受限：
- AppArmor 内核模块检查（aa_is_enabled）
- change_hat/change_profile syscall
- /sys/kernel/security/apparmor 接口

## 编译产物

### 库文件

- `libapparmor.so.1.24.2` - 共享库
- `libapparmor.a` - 静态库

### 命令行工具

- `aa-enabled` - 检查 AppArmor 是否启用
- `aa-exec` - 在 AppArmor 约束下执行程序
- `aa-features-abi` - 特性 ABI 工具
- `aa-load` - 加载策略工具
- `aa-status` - 状态查询工具

## 详细信息

参见各版本的 `notes.md` 和 `reports/test-report.md`。

## 许可证

- libapparmor: LGPL-2.0+
- 其他组件: GPL-2.0+