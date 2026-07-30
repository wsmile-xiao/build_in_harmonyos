# cyan 1.4.4 适配笔记

## 软件概述
cyan (pyzule-rw) 是一个 iOS 应用注入和修改工具，纯 Python 实现，无 C 扩展。

## 适配要点

### 平台检查问题
- `cyan/tbhtypes/executable.py` 在**类定义时**调用 `tbhutils.get_tools_dir()`，该函数检查 `platform.system()` + `platform.machine()` 是否为已支持平台 (iOS/macOS)
- 在 HarmonyOS aarch64 上 `get_tools_dir()` 会 `sys.exit()`，导致无法导入模块
- **修复**: 补丁 `0001-defer-platform-check.patch` 将 `get_tools_dir()` 调用从类级别移到 `__init__` 中，使模块可在非 iOS 平台导入
- 效果: `cyan --help` 和 `cyan --version` 正常工作；实际 iOS 应用修改功能在非 iOS 平台不可用（预期行为）

### 构建方式
- pyzule-rw 是纯 Python 包，无 C 扩展
- 由于 conanrun 虚拟环境无 pip/setuptools，采用手动复制模块 + 生成 launcher 脚本的方式打包
- 创建 `bin/cyan` 和 `bin/cgen` 作为 console_scripts 入口

### 源码下载
- 官方源: https://github.com/asdfzxcvbn/pyzule-rw/archive/refs/tags/v1.4.4.tar.gz
- CI 环境可正常下载；本地开发环境可能需要镜像加速
---

**编译结束**: 2026-07-28 10:19
**最终状态**: built

## 适配完整性说明 (R40)

cyan (pyzule-rw) 是 iOS 应用注入和修改工具，核心功能依赖 iOS/macOS 平台工具链
(install_name_tool, ldid, lipo, otool, insert_dylib)。补丁 0001 将 get_tools_dir()
延迟到实例化时调用，使模块可在 HarmonyOS 上导入。

### 可用功能
- `cyan --help`: 显示帮助信息 ✅
- `cyan --version`: 显示版本号 ✅
- argparse 参数解析和验证 ✅

### 不可用功能 (预期行为)
- iOS 应用注入/修改/签名: 依赖 iOS 平台工具，HarmonyOS 上不可用
- Executable 类实例化: 会触发 get_tools_dir() 平台检查退出

### 适配合理性
作为命令行工具库收录，提供 HarmonyOS 上的 CLI 帮助和版本查询能力。
实际 iOS 应用操作功能在非 iOS 平台不可用是工具本身的设计约束。
