# croncpp

Header-only C++ library for parsing CRON expressions and computing next/previous occurrences.

## OHOS 适配

- **构建系统**: CMake（INTERFACE 库，header-only）
- **语言标准**: C++17（string_view 快速路径）
- **依赖**: 无第三方依赖
- **补丁**: 无（OHOS aarch64 直接编译通过）
- **产物**: include/croncpp.h + LICENSE，CMake target `croncpp::croncpp`

## 测试

- 上游 Catch2 套件: 92 TEST_CASE / 44294 assertions，OHOS 主机原生运行 92/92 通过
- OHOS 专项消费者测试: test_package（13 checks），13/13 通过

## 参考

- 官网: https://github.com/mariusbancila/croncpp
- 许可证: MIT
