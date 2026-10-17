# DRAFT-332 — OHOS clang15/libc++15 C++20 兼容系列

openrct2 0.5.3（PR #9656）实证：六类 C++20 特性在 OHOS clang 15.0.4/libc++ 15 的
缺口与修法（stop_token/source_location/typename/make_unique_for_overwrite/std::ranges/
聚合 CTAD + construct_at），外加 nlohmann_json 版本选择（-fno-char8_t 冲突）与
test_package env 组合坑。完整 patch 模板见 archives/o/openrct2/0.5.3/patches/。

## 症状 → 修法速查

| 错误 | patch |
|---|---|
| fatal error: 'stop_token' file not found | 删除未使用 include（代码常是自实现 atomic_bool） |
| fatal error: 'source_location' file not found | __builtin_FILE/LINE polyfill（#if __has_include 守卫） |
| missing 'typename' prior to dependent type name | 补 typename（P0634 不完整） |
| make_unique_for_overwrite（C++23） | 降级 make_unique |
| no member named 'fill' in 'std::ranges' | std::fill/std::lower_bound + 投影 lambda |
| no viable constructor or deduction guide | 显式推导指引/显式构造函数 |
| construct_at no matching function | 聚合体加显式构造函数 |
| char8_t/u8string 报错（-fno-char8_t） | nlohmann-json/3.11.2（勿用 3.12） |
| test Error 127 relocating | env=["conanbuild","conanrun"] 组合 |
