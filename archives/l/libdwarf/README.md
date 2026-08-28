# libdwarf - DWARF 调试信息库

## 软件简介

libdwarf 是用于读取和写入 DWARF 调试信息的 C 库。DWARF 是 ELF 可执行文件中广泛使用的调试数据格式，被 GCC、Clang 等编译器采用。

**主要组件**:
- **libdwarf**: C 库，提供 DWARF 数据访问 API
- **dwarfdump** (可选): 命令行工具，用于查看和分析 ELF 文件中的 DWARF 调试信息
- **dwarfgen** (可选): 命令行工具，用于生成 DWARF 调试信息

## 已编译版本

| 版本 | 状态 | 构建系统 | 依赖 | 日期 |
|------|------|----------|------|------|
| 2.1.0 | ✅ published | cmake | zlib/1.3.1, zstd/1.5.6 | 2026-08-28 |

## 依赖关系

- **编译依赖**: zlib/1.3.1, zstd/1.5.6
- **运行依赖**: musl libc (已预装)

## 使用示例

### 使用 libdwarf 库
```bash
# 编译时链接
gcc -o mytool mytool.c -ldwarf

# 包含头文件
#include <libdwarf.h>
#include <dwarf.h>
```

### 静态链接
当使用静态库时，需要定义 `LIBDWARF_STATIC=1`（conan 会自动处理）：
```bash
gcc -o mytool mytool.c -ldwarf -DLIBDWARF_STATIC=1
```

## 编译指导

### 构建系统说明

libdwarf 使用 CMake 构建系统，在 HarmonyOS 上使用标准 conan CMake 流程。

```bash
# CMake 构建
cmake -B build \
    -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
    -DBUILD_SHARED=OFF \
    -DBUILD_NON_SHARED=ON \
    -DBUILD_DWARFDUMP=OFF \
    -DBUILD_DWARFGEN=OFF \
    -DBUILD_DWARFEXAMPLE=OFF
cmake --build build -j$(nproc)
cmake --install build --prefix $HOME/usr/local
```

### 构建选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| shared | False | 构建共享库 |
| fPIC | True | 生成位置无关代码 |
| with_dwarfgen | False | 构建 dwarfgen 工具 |
| with_dwarfdump | False | 构建 dwarfdump 工具 |

## 参考资料

- 官方网站: https://www.prevanders.net/dwarf.html
- DWARF 标准: https://dwarfstd.org/
- 源码: https://github.com/davea42/libdwarf-code
