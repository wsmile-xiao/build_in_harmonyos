# libdwarfp - DWARF 调试信息生产者库

## 软件简介

libdwarfp 是 libdwarf 项目中的 DWARF **生产者（写）** 库，用于生成
DWARF 调试信息（.debug_info/.debug_abbrev 等节），供编译器、调试
信息生成工具等使用。与同项目的消费者（读）库 libdwarf 分别打包。

**主要组件**:
- **libdwarfp**: C 库，提供 DWARF producer API（dwarf_producer_init 系）

## 已编译版本

| 版本 | 状态 | 构建系统 | 依赖 | 日期 |
|------|------|----------|------|------|
| 2.1.0 | ✅ published | cmake | 无（自含消费者库） | 2026-09-14 |

## 依赖关系

- **编译依赖**: 无 conan 依赖（同工程消费者库 libdwarf 一并打包，
  静态 libdwarfp.a 的公开符号引用由此闭合）
- **运行依赖**: musl libc (已预装)
- 说明: zlib/zstd 是消费者侧（libdwarf 包）的可选解压依赖，
  libdwarfp 源码零引用

## 使用示例

### 使用 libdwarfp 库
```c
#include <libdwarf.h>
#include <libdwarfp.h>

/* 初始化 producer（arm64、DWARF5、符号重定位） */
dwarf_producer_init(DW_DLC_POINTER64 | DW_DLC_TARGET_LITTLEENDIAN |
                        DW_DLC_SYMBOLIC_RELOCATIONS,
                    callback, NULL, NULL, NULL,
                    "arm64", "V5", "", &dbg, &err);
```

### 静态链接
当使用静态库时，需要定义 `LIBDWARF_STATIC=1`（conan 会自动处理）：
```bash
gcc -o myproducer myproducer.c -ldwarfp -ldwarf -DLIBDWARF_STATIC=1
```
注意：libdwarfp.h 自身不包含 libdwarf.h，请先包含 <libdwarf.h>。
本包同时提供 libdwarfp 与消费者库 libdwarf，无需额外安装。

## 编译指导

### 构建系统说明

libdwarfp 与 libdwarf 同属一个 CMake 工程，dwarfp 目标仅在
`BUILD_DWARFGEN=TRUE` 时进入构建，在 HarmonyOS 上使用标准 conan
CMake 流程。

```bash
# CMake 构建
cmake -B build \
    -DBUILD_NON_SHARED=ON \
    -DBUILD_SHARED=OFF \
    -DBUILD_DWARFGEN=ON \
    -DBUILD_DWARFDUMP=OFF \
    -DBUILD_DWARFEXAMPLE=OFF
cmake --build build -j$(nproc)
cmake --install build
```

### 构建选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| shared | False | 构建共享库 |
| fPIC | True | 生成位置无关代码 |

### 上游测试

```bash
cmake -DDO_TESTING=ON ...    # 上游没有 BUILD_TESTING 选项
cmake --build build
ctest --output-on-failure    # 全量 26 项（需 BUILD_DWARFDUMP=ON）
ctest -E selfdwarfdump       # 自包含单元子集（20 项）
```

## 参考资料

- 官方网站: https://www.prevanders.net/dwarf.html
- DWARF 标准: https://dwarfstd.org/
- 源码: https://github.com/davea42/libdwarf-code
- 消费者库配方: archives/l/libdwarf
