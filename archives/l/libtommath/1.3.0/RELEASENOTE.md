# libtommath 1.3.0 发布说明

## 版本信息

- **版本号**: 1.3.0
- **发布日期**: 2024-03-27
- **维护者**: libtom project

## 主要变更

### 新特性

1. 改进的 API 设计，更加一致的函数命名
2. 新增多个便捷函数：mp_init_i32, mp_init_u64 等
3. 改进的素数检测算法（Baillie-PSW）
4. 更好的错误处理机制

### 改进

1. 优化 Karatsuba 乘法算法的阈值
2. 减少 Montgomery 形式转换开销
3. 改进随机数生成器的安全性
4. 更好的内存管理策略

### 修复

1. 修复若干边界条件下的内存泄漏
2. 修复特定大数运算的精度问题
3. 改进对非标准平台的兼容性

## OpenHarmony 编译说明

### 编译环境

- OpenHarmony SDK 26.0.0.18
- Clang 编译器
- aarch64 架构

### 编译命令

```bash
make -j$(nproc)
make install PREFIX=/path/to/install
```

### 产物

- `libtommath.a` - 静态库
- `tommath.h` - 主头文件

## 使用说明

### 包含头文件

```c
#include <tommath.h>
```

### 链接库

```bash
-ltommath
```

### 示例代码

```c
#include <tommath.h>

int main() {
    mp_int num;
    mp_init(&num);
    mp_read_radix(&num, "12345678901234567890", 10);
    // 进行大数运算...
    mp_clear(&num);
    return 0;
}
```

## 兼容性

- 完全向后兼容 libtommath 1.2.x API
- 支持 C89 及以上标准
- 无外部依赖

## 许可证

Public Domain / WTFPL

---

*编译日期: 2026-04-22*