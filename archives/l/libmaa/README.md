# libmaa

Memory Allocator Abstraction library - 提供各种内存分配策略的统一接口。

## 功能概述

- 提供多种内存分配器的抽象接口
- 支持 arena、pool、list 等数据结构
- 提供哈希表、动态数组等工具

## OHOS 适配要点

1. **BSD make 兼容性**：项目使用 `.for/.endfor` 语法（BSD make 特性），GNU make 无法解析，需创建 Makefile.gnu
2. **musl 限制**：
   - `sys/resource.h` 缺失，timer.c 无法编译（已排除）
   - SIZEOF_LONG 需手动定义为 8
3. **共享库编译**：需要添加 `-fPIC` 编译选项
4. **arggram.c 生成**：需要手动运行 `awk -f arggram2c arggram.txt > arggram.c`

## 依赖关系

- 无外部依赖

## 参考资料

- 源码：https://github.com/s-yata/libmaa