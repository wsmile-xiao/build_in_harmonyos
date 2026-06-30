# libcutl — C++ 编译器通用工具库

## 简介
libcutl 是由 Code Synthesis 开发的 C++ 通用工具库，提供适用于 C++ 编译器开发和其他 C++ 项目的基础组件，包括：

- **compiler**（编译器工具）: code-stream（代码流）、context（上下文）、cxx-indenter（C++ 缩进器）、sloc-counter（源码行计数器）、traversal（遍历）、type-id（类型标识）、type-info（类型信息）
- **container**（容器）: any（任意类型容器）、graph（图容器）、multi-index（多索引）、pointer-iterator（指针迭代器）
- **fs**（文件系统）: path（跨平台路径操作）、auto-remove（自动删除）、exception（异常）
- **meta**（元编程）: class-p（类指针检测）、polymorphic-p（多态检测）、remove-c/cv/p/v（类型修饰移除）、answer（布尔回答）
- **re**（正则表达式）: 正则表达式支持
- **shared-ptr**（共享指针）: 侵入式引用计数智能指针

## 链接
- 主页: https://www.codesynthesis.com/projects/libcutl/
- 源码: https://www.codesynthesis.com/download/xsd/4.2/libcutl-1.11.0.tar.gz

## 编译说明
- v1.11.0 使用 **build2** 构建系统（而非早期版本的 autotools）
- 鸿蒙平台无 build2/bpkg，需要手动编译（逐文件 clang++ 编译 + llvm-ar 打包为静态库）
- 推荐使用 clang++ 编译为静态库，参数: `-O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD`
- libcutl::shared_ptr 是侵入式智能指针，要求对象继承自带引用计数的 shared base

## 版本记录
| 版本 | 状态 | 日期 |
|------|------|------|
| 1.11.0 | built（编译成功） | 2026-06-11 |