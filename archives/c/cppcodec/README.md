# cppcodec

C++ header-only library to encode/decode **base64**, **base64url**, **base32**,
**base32hex** and **hex**. Compatible with C++11 and later.

- 官方仓库: https://github.com/tplgy/cppcodec
- License: MIT
- 类型: header-only（纯 .hpp，无编译二进制产物）

## OHOS 适配要点

- 库本体为 header-only，CMake 仅用于构建 test/ 与 tool/ 下的测试与命令行工具。
- 适配以 header-only Conan 配方（`package_type = header-library`）归档，
  复制 `cppcodec/` 头文件树即可，无需编译。
- 上游 CMakeLists.txt 中 `PROJECT_VERSION` 仍是 0.1（tag v0.2 未同步），
  配方版本以官方 tag `v0.2` 为准。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.2  | adapting | 2026-08-29 |
