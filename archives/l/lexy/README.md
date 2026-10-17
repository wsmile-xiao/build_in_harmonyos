# lexy

lexy is a parser combinator library for C++17 and onwards.
It allows you to write a parser by specifying it in a convenient C++ DSL,
which gives you all the flexibility and control of a handwritten parser without any of the manual work.

- **上游仓库**: https://github.com/foonathan/lexy
- **License**: BSL-1.0
- **构建系统**: CMake（上游 targets：`lexy` / `lexy_core` / `lexy_dev` / `lexy_file`(STATIC) / `lexy_unicode` / `lexy_ext` / `_lexy_base` / `lexy_experimental`，namespace `foonathan::`）
- **类型**: C++17 库（核心为 header-only INTERFACE targets + 一个 STATIC target `lexy_file`，对应 `src/input/file.cpp`）
- **外部依赖**: 无（tests 通过 FetchContent 拉取 doctest，非库依赖）
- **公开头文件**: `include/lexy/` + `include/lexy_ext/`

## 可用版本

| 版本 | 状态 |
|------|------|
| 2025.05.0 | bootstrap（新建骨架，未 adapt/编译/发布） |
