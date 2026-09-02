# fast_double_parser

Fast C++ double parser, packaged as a header-only Conan library.

## OHOS 适配

- CMake 安装 `fast_double_parser.h` 和上游 Config.cmake。
- Conan target 为 `fast_double_parser::fast_double_parser`。
- 构建时关闭上游 benchmark，设备可运行时执行上游 CTest。
- 本次为路径 A 基础适配，未修改上游源码，也没有新增知识库扩展。

## 验证

- 上游测试：1/1 CTest 通过；测试程序内部检查解析边界。
- Conan 消费测试：1/1 通过，实际调用 `parse_number`。

上游：https://github.com/lemire/fast_double_parser
