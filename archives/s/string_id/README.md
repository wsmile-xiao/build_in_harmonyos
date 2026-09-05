# string_id

`foonathan/string_id` 是一个使用哈希值表示字符串标识、同时支持从数据库取回原字符串的 C++ 库。

## 功能

- `string_id` 与数据库 API
- FNV-1a 64-bit 哈希
- 编译期字符串字面量
- 线程安全数据库适配器与计数/随机 ID 生成器

## HarmonyOS 适配

该版本使用 CMake 构建，默认打包静态库和公共头文件。上游没有安装规则或正式 CTest 用例，配方显式打包构建产物，并通过官方 example 与 Conan 消费者测试验证。设备的 CMake 4.1.2 需要通过 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上游的 CMake 2.8 最低版本声明。

## 依赖

无 Conan 外部依赖，使用 C++ 标准库。

## 参考

- [上游仓库](https://github.com/foonathan/string_id)
- [Zlib License](https://github.com/foonathan/string_id/blob/v2.0-3/LICENSE)
