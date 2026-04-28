# libtommath

## 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | libtommath |
| 版本 | 1.3.0 |
| 描述 | C library for number theoretic multiple-precision integers |
| 类别 | math |
| 许可证 | Public Domain |
| 构建系统 | Makefile / CMake |
| URL | https://github.com/libtom/libtommath |

## 功能说明

libtommath 是一个可移植的、符合 ISO C 标准的多精度整数数学库。它提供：
- 大整数运算（加、减、乘、除）
- 模运算
- 素数检测和生成
- 数论函数（GCD、LCM、逆模等）
- Montgomery 形式优化
- Karatsuba 和 Toom-Cook 快速乘法算法

## 主要特性

- **无外部依赖**：纯 C 实现，不需要任何第三方库
- **高性能**：使用多种快速算法优化
- **可移植**：支持多种平台和编译器
- **API 简洁**：提供一致的函数命名风格
- **安全性**：支持密码学应用中的大数运算

## 编译选项

```bash
# 使用 Makefile
make -j$(nproc)
make install PREFIX=/path/to/install

# 使用 CMake
cmake -B build -DCMAKE_INSTALL_PREFIX=/path/to/install
cmake --build build
cmake --install build
```

## 关键文件

| 文件 | 说明 |
|------|------|
| tommath.h | 主头文件，包含所有公开 API |
| tommath_class.h | 函数类声明 |
| tommath_private.h | 内部实现头文件 |
| libtommath.a | 静态库 |

## 使用示例

```c
#include <tommath.h>

int main() {
    mp_int a, b, c;
    mp_init_multi(&a, &b, &c, NULL);
    
    mp_read_radix(&a, "123456789", 10);  // 十进制读取
    mp_read_radix(&b, "987654321", 10);
    mp_add(&a, &b, &c);                   // 加法
    
    char buf[256];
    mp_to_radix(&c, buf, sizeof(buf), 10); // 十进制输出
    printf("Result: %s\n", buf);
    
    mp_clear_multi(&a, &b, &c, NULL);
    return 0;
}
```

## 相关链接

- 官方仓库：https://github.com/libtom/libtommath
- 文档：https://github.com/libtom/libtommath/tree/develop/doc