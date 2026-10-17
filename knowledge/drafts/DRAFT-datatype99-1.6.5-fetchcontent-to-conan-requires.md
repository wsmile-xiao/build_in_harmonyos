# DRAFT-datatype99-1.6.5-fetchcontent-to-conan-requires

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: datatype99 1.6.5 HarmonyOS PC 适配（FetchContent → conan requires）

## 现象

datatype99 1.6.5（hirrolot，C99 代数数据类型库）是 header-only 单头库，但上游
`CMakeLists.txt` 用 **FetchContent 现场下载** metalang99：

```cmake
FetchContent_Declare(metalang99
    URL https://github.com/hirrolot/metalang99/archive/refs/tags/v1.13.5.tar.gz)
FetchContent_MakeAvailable(metalang99)
```

在 OHOS conan 沙箱里这条路两头堵：构建期网络拉取与 conan 依赖管理冲突，
且沙箱策略不保证外网 fetch 可用。

## 根因

- header-only 库的"构建系统"只承担测试驱动 + 依赖获取；当依赖本身已被本仓
  适配（metalang99/1.13.5 在 archives）时，FetchContent 纯属重复且有害。
- 上游 tests/CMakeLists.txt 给 GCC/Clang 挂 `-fsanitize=address`，在 OHOS musl
  clang 上不在配方保证范围内，但 **省掉它不断言任何语义**（assert 照常）。

## 解决方案

1. `requires("metalang99/1.13.5", transitive_headers=True)`——版本与上游
   FetchContent 钉的 **完全一致**（对齐先于省事）。
2. 不走上游 CMake：build() 内直接编译 tests/ 5 个程序
   （tests/metalang99_compliant/derive/record_derive/version），
   `-I` 本库源根 + metalang99 includedirs（经 conan 依赖聚合）；
   编译期断言文件（version.c 的 ML99_ASSERT_UNEVAL）"编译成功即通过"，
   与 metalang99 上游 scripts/test.sh 的合同一致。
3. package() 只装 `datatype99.h`；`package_id` clear。

## 禁止策略

- 不得保留 FetchContent 让 CMake 现场下载（沙箱网络/依赖管理双冲突）。
- 不得改钉版本去迁就手头的 metalang99（先查上游 URL 里的 tag 再 requires）。
- 不得为跑测试引入 ASan 依赖——省 `-fsanitize=address` 并如实记录即可。

## 适用范围

hirrolot 系（metalang99/datatype99/interface99…）及一切"header-only +
FetchContent 钉依赖 + 测试不依赖 CMake 生成物"的库。
