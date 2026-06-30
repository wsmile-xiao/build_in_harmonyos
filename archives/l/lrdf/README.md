# lrdf

Lightweight RDF library for reading and writing RDF files.

## 特点

- **RDF 解析库**：用于读取和写入 RDF 文件
- **C 库**：提供 liblrdf.so 和 liblrdf.a
- **raptor2 依赖**：依赖 raptor2 进行 RDF 解析

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.6.1 | built | 2026-06-17 |

## 安装说明

lrdf 使用 autotools 构建：

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

安装产物：
- `lib/liblrdf.so` - 共享库
- `lib/liblrdf.a` - 静态库
- `include/lrdf.h` - 头文件
- `include/lrdf_types.h` - 头文件

## 使用说明

链接库：
```bash
clang your_program.c -llrdf -lraptor2 -o your_program
```

API 示例：
```c
#include <lrdf.h>

lrdf_urilist *list = lrdf_get_instances("http://example.org/ontology#Class");
```

## 源码信息

- **项目主页**: https://github.com/lrdf/lrdf
- **许可证**: GPL-2.0

## 依赖

- raptor2 >= 2.0.16
- libxml2 >= 2.15.3