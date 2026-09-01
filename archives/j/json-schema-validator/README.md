# json-schema-validator

## 简介
json-schema-validator 是一个基于 JSON for Modern C++（nlohmann/json）的 C++ JSON Schema 校验库，
支持 JSON Schema draft-7。将 schema 解析为编译后的 C++ 对象用于校验，产生可读性强的错误信息，
校验速度较 draft-4 版本提升明显。

## OHOS 适配
- CMake 库项目，依赖 nlohmann_json（header-only）
- 上游自带 Conan 1.x 配方（`from conans`），需转 Conan 2.x
- 提供库 `nlohmann_json_schema_validator`（静态/共享）与命令行示例 `json-schema-validate`

## 依赖
- 编译依赖：clang, cmake
- 运行依赖：libc
- 第三方：nlohmann_json（ohpcd 制品仓已有 3.1.1 / 3.12.0）

## 功能验证
```bash
# 库安装检查
ls -la $PREFIX/lib/libnlohmann_json_schema_validator*
ls -la $PREFIX/include/nlohmann/json-schema.hpp
# 命令行校验示例
$PREFIX/bin/json-schema-validate <schema> <instance>
```

## 参考
- 源码：https://github.com/pboettch/json-schema-validator
- 版本：2.1.0（标签 `2.1.0`，commit 27fc1d09）
- 许可证：MIT
