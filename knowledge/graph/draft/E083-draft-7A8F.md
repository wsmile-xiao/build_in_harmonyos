# E083: HMDFS 文件系统 autotools config.status 失败

## 问题描述

在 HarmonyOS HMDFS 文件系统挂载的目录中，使用 autotools 构建系统编译软件时，`config.status` 脚本无法正常创建配置文件，导致编译流程中断。

## 错误特征

```
config.status:1204: error: could not setup config files machinery
```

或者：

```
mktemp: cannot create temporary directory './confXXXXXX': Permission denied
```

## 根本原因

1. **HMDFS 文件系统限制**: HarmonyOS 使用 HMDFS（HarmonyOS Mobile Distributed File System）作为用户目录的挂载文件系统
2. **SELinux/HMMAC 机制**: HMDFS 实现了特殊的 SELinux 和 HMMAC (HarmonyOS Mandatory Access Control) 权限控制
3. **临时文件创建限制**: autotools 的 `config.status` 使用 `mktemp -d "./confXXXXXX"` 在当前目录创建临时目录，HMDFS 禁止此操作

## 受影响的软件

**所有使用 autotools 构建系统的软件**（在 HMDFS 目录中编译）：
- libmicrohttpd（典型案例）
- 其他 GNU autotools 项目

**不受影响的软件**：
- 使用 Meson/CMake 构建的项目（如 libzim, pugixml）
- Header-only 库

## 解决方案

### 方案 1: 使用非 HMDFS 目录（推荐）

但目前已知可用的非 HMDFS 目录大多需要特殊权限：
- `/data/local/tmp` - 需要特殊权限
- `/dev/shm` - 需要特殊权限
- `/tmp` - 只读

### 方案 2: 使用 Meson/CMake 替代构建

如果软件支持 Meson 或 CMake，优先使用：
```bash
meson setup build --prefix=$DEFAULT_PREFIX
# 或
cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
```

### 方案 3: 等待平台更新

HMDFS 可能在未来版本中修复此限制。

### 方案 4: 使用预编译包

查询 cmd-pkgs 是否有该软件的预编译包：
```bash
curl -s https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/README.md | grep <软件名>
```

## 禁止操作

**不要使用 --build/--host 参数绕过 config.guess 问题**：
- 这会导致 configure 误判为交叉编译
- AC_RUN_IFELSE 等运行时检测全部跳过
- 生成的 config.h 与实际平台不匹配

## 相关问题

- E007: config.guess 无法识别 HarmonyOS
- E046: chmod 权限问题
- E082: HMDFS 临时文件权限

## 案例：libmicrohttpd 编译失败

libmicrohttpd 是 libkiwix 的硬依赖，使用 autotools 构建。在 HMDFS 目录中编译时：

1. `./configure` 成功（应用 E007 补丁后）
2. `config.status` 失败（无法创建配置文件）
3. `Makefile` 未生成
4. 编译流程中断

libkiwix 编译被阻塞，因为 libmicrohttpd 无法在 meson.build 中禁用。

## 建议

对于 libkiwix 等依赖 autotools 库的项目：
1. 先编译 Meson/CMake 构建的依赖（如 libzim）
2. 记录 autotools 库的编译失败状态
3. 等待 HMDFS 问题解决或预编译包可用