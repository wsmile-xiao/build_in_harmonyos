# libmmap-allocator

## 简介

libmmap-allocator 是一个为 STL 容器提供 mmap 文件后端的 C++ 库，包含
`mmap_allocator`、`mmappable_vector`、文件映射池和异常类型。

## HarmonyOS 适配

- 版本：`0.4.0-git20200122.adbfbe1`
- 构建系统：上游 Makefile
- 依赖：无 Conan 依赖
- 默认产物：静态库 `libmmap_allocator.a`
- 可选产物：共享库 `libmmap_allocator.so`
- 测试：上游 `make test`，直接 mmap 测试，以及 Conan 消费者测试
- HarmonyOS 专测：运行时页大小对齐、真实文件映射读写和共享写回

## 来源与许可证

- 上游仓库：https://github.com/johannesthoma/mmap_allocator
- 许可证：LGPL-2.1（上游 README 声明为 LGPL）
