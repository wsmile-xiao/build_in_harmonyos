# vec

## 简介
类型安全的 C 动态数组（vector）实现，提供宏驱动的类型化容器
（`vec_int_t`/`vec_str_t` 等），支持 push/pop/insert/splice/sort/foreach 等操作。

## OHOS 适配
- 上游无构建系统，为 drop-in 源码对（src/vec.c + src/vec.h）
- 配方直接以工具链编译器编译 vec.c 为静态库 libvec.a（R33）
- 无平台依赖，libc 纯标准库调用，无需补丁

## 依赖
- 无

## 功能验证
```bash
# conan create 内建 test_package：映射上游 22 分节 / 52 断言验证 API 与链接
```

## 参考
- 上游: https://github.com/rxi/vec
- 适配笔记: archives/v/vec/0.2.1/notes.md
