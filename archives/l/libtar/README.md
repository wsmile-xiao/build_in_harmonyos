# libtar

## 软件简介

libtar 是一个用于操作 POSIX tar 文件的 C 语言库。它提供了创建、读取、解压 tar 归档文件的 API。

- **官方网站**: https://repo.or.cz/libtar.git
- **License**: NCSA (University of Illinois/NCSA Open Source License)
- **类型**: 库 + 命令行工具

## 主要功能

- 创建 tar 归档文件
- 读取和列出 tar 文件内容
- 解压 tar 文件到指定目录
- 支持目录递归操作
- 支持 gzip 压缩（-z 选项）

## 已编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 1.2.20 | built | 2026-06-08 | autotools |

## 使用方法

```bash
# 创建tar包
libtar -c archive.tar file1 file2 directory/

# 列出tar包内容
libtar -t archive.tar

# 解压tar包到指定目录
libtar -C /target/path -x archive.tar

# 使用gzip压缩
libtar -z -c archive.tar files...
```

## 库文件

- `libtar.so` - 共享库
- `libtar.a` - 静态库
- `libtar.h` - 头文件
- `libtar_listhash.h` - 列表/哈希辅助库头文件

## 依赖

- zlib (gzip 支持)

## 编译注意事项

参见各版本的 `notes.md` 文件。
