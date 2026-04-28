# dwarfutils - DWARF 调试信息工具集

## 软件简介

dwarfutils (libdwarf) 是用于读取和生成 DWARF 调试信息的工具库。DWARF 是 ELF 可执行文件中广泛使用的调试数据格式，被 GCC、Clang 等编译器采用。

**主要组件**:
- **dwarfdump**: 命令行工具，用于查看和分析 ELF 文件中的 DWARF 调试信息
- **libdwarf**: C 库，提供 DWARF 数据访问 API

## 已编译版本

| 版本 | 状态 | 构建系统 | 补丁数 | 日期 |
|------|------|----------|--------|------|
| 2.3.1 | ✅ success | cmake | 2 | 2026-04-28 |

## 快速安装

```bash
# 下载预编译包
tar xzf dwarfutils-2.3.1-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/dwarfutils-2.3.1-ohos-aarch64
sh install-dwarfutils-2.3.1.sh
```

## 使用示例

### 查看版本
```bash
dwarfdump --version
# 输出: dwarfdump [libdwarf 2.3.1 dwarfdump 2.3.1]
```

### 解析 DWARF 信息
```bash
# 查看 ELF 文件的 DWARF 调试信息
dwarfdump -a your_program

# 仅查看 .debug_info section
dwarfdump -i your_program

# 查看 .debug_line section
dwarfdump -l your_program
```

### 使用 libdwarf 库
```bash
# 编译时链接
gcc -o mytool mytool.c -ldwarf

# 包含头文件
#include <libdwarf.h>
#include <dwarf.h>
```

## 编译指导

### 构建系统说明

**注意**: 本软件在 HarmonyOS 上使用 CMake 构建，因为 autotools 在 HMDFS 文件系统上存在限制。

```bash
# CMake 构建
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
cmake --build build -j$(nproc)
cmake --install build --prefix=$HOME/usr/local
```

### 补丁应用

需要应用以下补丁以支持 HarmonyOS:

1. **config.guess 补丁**: 添加 HarmonyOS 系统识别
2. **config.sub 补丁**: 添加 ohos-linux 三元组支持

## 补丁清单

### 0001-config.guess.patch
- **类型**: 平台适配
- **内容**: 添加 HarmonyOS 系统检测分支
- **影响**: autotools 构建时正确识别系统

### 0002-config.sub.patch
- **类型**: 平台适配
- **内容**: 添加 ohos-linux 三元组验证
- **影响**: 支持 aarch64-unknown-linux-ohos 三元组

## 已知限制

### 1. 配置文件路径
运行时可能输出警告：
```
ERROR: dwarfdump found no dwarfdump.conf file in any of the standard places
```

**解决方案**: 配置文件位于 `share/dwarfdump/dwarfdump.conf`，不影响核心 DWARF 解析功能。

### 2. autotools 限制
HMDFS 文件系统不支持 autotools 的临时文件创建机制，需要使用 CMake 构建。

## 功能验证

```bash
# 验证 dwarfdump 功能
dwarfdump --version          # 检查版本
dwarfdump --help             # 查看帮助
dwarfdump -a $(which dwarfdump)  # 解析自身 DWARF 信息
```

## 依赖关系

- **运行依赖**: musl libc (已预装)
- **编译依赖**: 无额外依赖
- **可选依赖**: zlib, zstd (用于压缩 DWARF 数据)

## 参考资料

- 官方网站: https://www.prevanders.net/dwarf.html
- DWARF 标准: https://dwarfstd.org/
- 源码下载: https://www.prevanders.net/libdwarf-2.3.1.tar.xz