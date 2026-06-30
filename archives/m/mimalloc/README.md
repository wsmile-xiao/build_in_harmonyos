# mimalloc

Microsoft's memory allocator - a high-performance, general-purpose memory allocator with excellent performance characteristics.

## 基本信息

- **名称**: mimalloc
- **主页**: https://github.com/microsoft/mimalloc
- **许可证**: MIT
- **分类**: library

## 鸿蒙适配要点

### 关键配置选项

在鸿蒙系统上编译 mimalloc 时，必须注意以下关键选项：

1. **MI_OVERRIDE=OFF** (必须)
   - **原因**: mimalloc 默认会尝试覆盖系统 malloc/free，但在鸿蒙上会导致段错误
   - **现象**: 测试程序被 killed (SIGKILL)
   - **解决**: 禁用此选项，将 mimalloc 作为独立库使用

2. **MI_LIBC_MUSL=ON** (推荐)
   - **原因**: 鸿蒙使用 musl libc，需要启用相关兼容选项
   - **效果**: 优化内存分配策略以适应 musl 环境

### CMake 配置示例

```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DMI_LIBC_MUSL=ON \
      -DMI_OVERRIDE=OFF \
      ..
make -j2
make install
```

### 测试结果

编译 3.2.8 版本的测试结果：

- ✅ test-api: 37/37 通过
- ✅ test-api-fill: 通过
- ✅ test-stress: 通过 (2.32s)
- ✅ test-stress-dynamic: 通过 (15.89s)

**总计**: 4/4 测试通过 (100%)

### 使用方式

mimalloc 在鸿蒙上只能作为独立库使用，不能通过 LD_PRELOAD 方式：

```bash
# 编译时链接
gcc myapp.c -lmimalloc

# 或使用 mimalloc API
#include <mimalloc.h>
void* ptr = mi_malloc(size);
mi_free(ptr);
```

## 编译历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 3.2.8 | built | 2026-05-20 | 首次成功编译 |

## 依赖关系

无外部依赖。

## 相关知识

- E999: mimalloc MI_OVERRIDE 导致段错误（见 knowledge/graph/draft/E999-draft-F27F.md）