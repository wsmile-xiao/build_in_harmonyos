# scnlib

## 简介

scnlib 是一个现代 C++17 库，用于从字符串/输入流中扫描（读取）值，作为
`std::scanf` 和 `iostreams` 的替代方案。它提供类型安全、无异常开销的
scanning API，是 {fmt} 库的反向对应物（fmt 负责格式化输出，scn 负责
格式化输入解析）。

- 上游：https://github.com/eliaskosunen/scnlib
- 许可证：Apache-2.0

## OHOS 适配要点

- **构建系统**：CMake（>= 3.16），产出 compiled library `libscn.a/.so`（SOVERSION 4）
- **依赖**：fast_float/6.1.6（仓内 conan 包；上游 bundled tag 即 v6.1.6，版本精确对应）
- **关键 patch**：上游 `find_package(FastFloat)` 与 Conan CMakeDeps 生成的
  `fast_float-config.cmake`（小写包名 + `fast_float::fast_float` target）不匹配，
  patch 0001 使其先试小写名再回退上游拼写
- **平台兼容**：OHOS musl 无 `xlocale.h`，上游 `SCN_XLOCALE` 检测链自动落到
  `SCN_XLOCALE_OTHER` 分支（使用 `std::strtod` + locale guard），无需修改源码
- **测试**：上游 unittests 用 FetchContent 从 GitHub 拉 googletest（CI 网络不可达），
  适配采用 `SCN_TESTS=OFF` + test_package 消费者测试覆盖（int/float/string/
  vector-range/xchar/错误处理共 9 组断言）

## 依赖

- fast_float/6.1.6（浮动点解析后端）
