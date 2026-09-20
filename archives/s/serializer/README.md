# serializer

[zpp serializer](https://github.com/eyalz800/serializer) — 单头文件标准 C++ 序列化框架（MIT）。

## 简介

`serializer.h` 提供零开销的二进制序列化：任意 STL 容器、自定义类（
`friend zpp::serializer::access` + 静态 `serialize()`）以及多态对象（派生
`zpp::serializer::polymorphic` 并注册类型）均可 save/load 往返。默认容器
大小类型为 4 字节（可用 `size_is<T>()` 覆盖），多态对象额外 8 字节序列化 ID。

## OHOS 适配

- 纯头文件库：无构建系统、无编译产物，`conanfile.py` 按 header-only 模板安装
  `serializer.h` 与 LICENSE。
- 消费端要求 C++17（`std::optional/std::variant` 分支与 polymorphic 支持）。
- 上游官方 tag v0.5 源码不含任何测试套件；消费者测试
  `test_package/test.cpp` 覆盖 STL 容器、自定义类与多态往返。

## 依赖

无（仅依赖 C++ 标准库）。

## 功能验证

```bash
conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=missing
# test_package: serializer consumer test PASSED
```

## 参考

- 官网: https://github.com/eyalz800/serializer
- 源码: https://github.com/eyalz800/serializer/archive/refs/tags/v0.5.tar.gz
