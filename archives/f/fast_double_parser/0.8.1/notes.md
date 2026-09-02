# fast_double_parser 0.8.1 适配笔记

## 适配结论

- 构建系统：CMake；源码包 SHA-256 为 `685c1b7b9383f5fcd96264467bb2efa0c9995d7e8afb66ed9c84663466c3cefd`。
- 适配路径：路径 A；没有修改上游源码，没有新增知识库扩展。
- 配方将上游库作为 header-only CMake 包，关闭 benchmark，并在 `can_run(self)` 时执行上游 CTest。

## 验证

- 上游：1/1 CTest 通过；上游 `tests/unit.cpp` 构建出的单一测试程序内部包含解析检查。
- 消费者：1/1 通过，调用 `fast_double_parser::parse_number` 解析 `-123.456e2`。

## Conan 包接口

- CMake 包名：`fast_double_parser`。
- CMake target：`fast_double_parser::fast_double_parser`。
- 运行时链接库：无。
