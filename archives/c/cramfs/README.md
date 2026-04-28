# cramfs

cramfs（Compressed ROM File System）是一个轻量级的压缩只读文件系统工具，提供创建和检查 cramfs 镜像的功能。

## 功能概述

- **mkcramfs**: 创建 cramfs 压缩文件系统镜像
- **cramfsck**: 检查和验证 cramfs 镜像完整性
- 高压缩比，适用于嵌入式系统
- 基于 zlib 压缩

## OHOS 适配

- GNUmakefile 硬编码 gcc，通过补丁改为 clang
- configure 脚本需要适配
- mkcramfs.c 需要源码修复
- 使用 `make CC=clang CFLAGS="-fPIC -O2 -W -Wall -I." LDLIBS="-lz"` 编译

## 依赖关系

- zlib（压缩/解压）
- clang 编译器

## 参考资料

- 源码: https://sourceforge.net/projects/cramfs/
