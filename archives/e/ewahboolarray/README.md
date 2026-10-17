# EWAHBoolArray

EWAHBoolArray 是一个 C++11 header-only 压缩位图库，提供 EWAHBoolArray 和 BoolArray 两种位图实现，以及集合运算、序列化和迭代器 API。

## OHOS 适配要点

- 上游 v0.8.0 使用 CMake，库目标为 `ewah::ewah`，没有外部依赖。
- Conan 包类型为 `header-library`，只安装头文件、CMake/pkg-config 元数据和许可证，不生成二进制库。
- 设备端 Conan 构建必须运行上游唯一的 CTest `unit` 目标；该目标的 `main()` 展开执行 105 个可失败测试点，归属 37 个逻辑测试族，另遍历 207 组嵌套数据输入。

## 依赖

无第三方依赖；需要 C++11 编译器和 CMake。

## 功能验证

```bash
ctest --output-on-failure
```

## 参考

- [官方文档](https://lemire.github.io/EWAHBoolArray/)
- [源码仓库](https://github.com/lemire/EWAHBoolArray)
