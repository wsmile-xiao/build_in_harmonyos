# dwarfutils 2.3.1 — OpenHarmony 编译记录

**编译日期**: 2026-04-28
**状态**: ✅ 成功

## 基本信息
- **软件**: dwarfutils
- **版本**: 2.3.1
- **构建系统**: cmake (autotools 在 HMDFS 上失败)
- **目标平台**: ohos-aarch64 (aarch64-unknown-linux-ohos)
- **编译器**: clang 15.0.4

## 编译产物
- **bin/dwarfdump**: 1.33MB ELF 可执行文件
- **lib/libdwarf.a**: 1.24MB 静态库
- **include/dwarf.h**: DWARF 定义头文件
- **include/libdwarf.h**: libdwarf API 头文件

## 编译指导

### 构建系统选择
⚠️ **重要**: autotools 构建系统在 HMDFS 文件系统上会失败，必须使用 CMake。

```bash
# 正确的构建方式 (CMake)
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
cmake --build build -j$(nproc)
cmake --install build --prefix=$HOME/usr/local
```

### autotools 失败原因
config.status 脚本在 HMDFS 上创建临时文件时权限被拒绝：
```
./config.status[1078]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

## 补丁清单

### 0001-config.guess.patch
- **类型**: 平台适配
- **作用**: 添加 HarmonyOS 系统识别
- **修改**: 添加 HarmonyOS case 分支，输出 aarch64-unknown-linux-ohos
- **guard**: `__OHOS__` 定义检测

### 0002-config.sub.patch
- **类型**: 平台适配
- **作用**: 支持 ohos-linux 三元组
- **修改**: 
  - 添加 `ohos-linux` 三元组处理
  - 在 OS 列表中添加 `ohos*`
  - 在内核列表中添加 `linux-ohos*`

## 已知限制

### 1. autotools 在 HMDFS 上不可用
HMDFS 文件系统不支持 autotools config.status 的临时文件机制。
**解决方案**: 使用 CMake 构建。

### 2. 配置文件路径警告
运行时可能输出警告:
```
ERROR: dwarfdump found no dwarfdump.conf file in any of the standard places
```
**解决方案**: 配置文件位于 `share/dwarfdump/dwarfdump.conf`，使用默认配置不影响功能。

## 功能验证

```bash
# 验证安装
dwarfdump --version
# 输出: dwarfdump [Apr 28 2026 ... (libdwarf 2.3.1 dwarfdump 2.3.1)]

# 解析 ELF 文件的 DWARF 信息
dwarfdump -a /path/to/elf/file

# 查看帮助
dwarfdump --help
```

### 测试结果摘要
- ✅ 编译成功 (CMake 100%)
- ✅ 版本验证通过
- ✅ DWARF 解析功能正常
- ⚠️ 配置文件路径警告 (不影响功能)
- ✅ 预编译包制作成功

## 预编译包
- **文件**: dwarfutils-2.3.1-ohos-aarch64.tar.gz (2.9MB)
- **安装脚本**: install-dwarfutils-2.3.1.sh

---
*编译记录更新时间: 2026-04-28 11:50*