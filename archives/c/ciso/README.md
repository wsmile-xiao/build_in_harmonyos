# ciso

ciso 是一个 PSP ISO 镜像压缩和解压工具，可将 ISO 文件压缩为 CSO 格式以节省存储空间。

## 功能概述

- ISO → CSO 压缩（减小镜像体积）
- CSO → ISO 解压（还原原始镜像）
- 支持多种压缩级别
- 轻量级命令行工具

## OHOS 适配

- 原始 Makefile 硬编码 gcc，需改为 clang 编译
- 链接 zlib 库（-lz）
- Format string warnings（uint64_t vs long long）为非致命警告
- 无 configure 脚本，直接 make 即可

## 依赖关系

- zlib（压缩/解压）
- clang 编译器

## 参考资料

- 源码: https://sourceforge.net/projects/ciso/
