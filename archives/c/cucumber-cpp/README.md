# Cucumber-CPP

## 简介
Cucumber-CPP 是 Cucumber BDD 框架的 C++ 实现, 通过 wire 协议将 Ruby 的 Cucumber 与 C++ 步骤定义桥接, 支持 `GIVEN`/`WHEN`/`THEN` 宏与多种测试驱动 (GTest/Boost/Qt).

## OHOS 适配
- CMake 3.16+, C++17, 使用 `find_package` 查找 `nlohmann_json` 与 `GTest`
- `asio` 与 `tclap` 无 OHOS 制品仓包, 在 `source()` 中以 `get()` 拉取至 `deps/` 并通过 `ASIO_INCLUDE_DIR`/`TCLAP_INCLUDE_DIR` 缓存变量注入
- `cmake/modules/GitVersion.cmake` 在非 git 源码树上会 `FATAL_ERROR`; 补丁回退到 `0.8.0`
- `pthread` 仅在 Linux/OHOS 上链接

## 依赖
- `nlohmann_json/3.12.0`
- `gtest/1.17.0`

## 功能验证
```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
ctest --output-on-failure
./test_package --gtest_output=xml
```

## 参考
- 官网: https://github.com/cucumber/cucumber-cpp
- 源码: https://github.com/cucumber/cucumber-cpp/archive/refs/tags/v0.8.0.tar.gz
