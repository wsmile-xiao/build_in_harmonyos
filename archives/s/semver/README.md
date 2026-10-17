# semver

## 简介
semver（Neargye/semver）是一个 C++17 header-only 的 Semantic Versioning 2.0.0 库，
提供版本解析与校验、比较、自增、格式化以及常见版本约束范围语法。无外部依赖。

## OHOS 适配
- Header-only 库，无需编译二进制（package_type = header-library）
- C++17 实现，安装单个头文件到 include/semver.hpp
- 无外部依赖

## 依赖
- 无外部依赖（header-only）
- 需要 C++17 兼容编译器

## 功能验证
```bash
# 头文件安装验证
ls ~/usr/local/include/semver.hpp
```

## 参考
- GitHub：https://github.com/Neargye/semver
- Release：https://github.com/Neargye/semver/releases/tag/v0.3.0
