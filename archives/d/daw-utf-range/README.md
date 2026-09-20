# daw-utf-range

## 简介
daw-utf-range 是 beached（Darrell Wright）维护的 C++17 UTF-8 迭代器/范围库（daw 系），
提供 `daw::range::create_char_range`（UTF-8 码点范围遍历）、`daw::utf_string`（UTF-8
字符串比较/排序）与 `daw/utf8/{checked,unchecked,core}.h`（底层 UTF-8 码点解码）三组设施。

## OHOS 适配
- **构建系统**: CMake header-only INTERFACE library（`-DDAW_USE_PACKAGE_MANAGEMENT=ON -DDAW_ENABLE_TESTING=OFF`）
- **依赖**: daw-header-libraries（Conan find_package 模式，制品仓已发布 2.135.0）
- **产物**: 仅头文件 `include/daw/utf8*.h` + `include/daw/utf_range/*.h`，CMake 目标 `daw::daw-utf-range`

## 依赖
- daw-header-libraries >= 2.x（header-only）

## 版本
| 版本 | 状态 |
|------|------|
| 2.2.6 | published（2026-09-19） |
