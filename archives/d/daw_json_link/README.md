# daw_json_link

## 简介
daw_json_link 是 beached（Darrell Wright）维护的 C++17 静态 JSON 解析/序列化库（daw 系），
通过 `daw::json::json_data_contract` 数据契约实现编译期绑定：`from_json`（解析到结构体）、
`to_json`（结构体序列化）与 `json_value`（动态访问）三组核心设施，主打解析速度与
constexpr 能力。

## OHOS 适配
- **构建系统**: CMake header-only INTERFACE library（`-DDAW_USE_PACKAGE_MANAGEMENT=ON -DDAW_ENABLE_TESTING=OFF`）
- **依赖**: daw-header-libraries + daw-utf-range（Conan find_package 模式）
- **产物**: 仅头文件 `include/daw/json/*.h`，CMake 目标 `daw::daw-json-link`

## 依赖
- daw-header-libraries >= 2.x（header-only）
- daw-utf-range >= 2.x（header-only，序列化路径）

## 版本
| 版本 | 状态 |
|------|------|
| 3.38.1 | published（2026-09-19） |
