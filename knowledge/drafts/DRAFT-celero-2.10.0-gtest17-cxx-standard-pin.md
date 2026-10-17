# DRAFT-celero-2.10.0-gtest17-cxx-standard-pin：gtest ≥ 1.17 要求 C++17 × 上游钉死 C++14

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: celero 2.10.0 HarmonyOS PC 适配（真机 shadow CI 第 3 轮 L1 失败，patch 0001）
> 对应：knowledge/drafts/DRAFT-celero-2.10.0-gtest17-cxx-standard-pin.kv

## 现象

配方为拿真实"上游测试用例通过率"启用上游 GTest 套件（`test_requires "gtest/1.17.0.1"` +
`CELERO_ENABLE_TESTS=ON`），`conan create` 编译测试目标时报两类错误（同源）：

```text
.../conan-home/p/gteste180c036ce0db/p/include/gtest/internal/gtest-port.h:273:2:
  error: C++ versions less than C++17 are not supported.
.../p/include/gtest/gtest-param-test.h:483:48:
  error: use of class template 'function' requires template arguments
```

库本体编译全部通过，失败只集中在链 gtest 头的测试翻译单元。

## 根因

1. googletest 自 **v1.17.0 起要求 C++17**：gtest-port.h 静态断言直接拒绝更低标准；
   gtest-param-test.h 的 `std::function` 前向声明用法在 C++14 下也无法通过。
2. 上游根 CMakeLists **无条件** `set(CMAKE_CXX_STANDARD 14)`（普通变量）。普通变量
   优先于 cache 变量被读取，因此 CMakeToolchain 里 `tc.variables["CMAKE_SYSTEM_NAME"]`
   同伴注入的 `CMAKE_CXX_STANDARD=17` **压不过它**——子目录测试目标继承的是 14。

两条叠加：任何 `test_requires gtest/1.17.x` 的配方，只要上游钉死 C++ < 17，
上游测试目标必然编译失败。本仓库测试依赖统一 gtest/1.17.0.1，此坑具有普遍性。

## 方案

最小补丁只提升**测试可执行目标**的标准，库本体保持上游默认（消费者零感知）：

```cmake
# test/CMakeLists.txt，add_executable 之后（patch 0001，+4 行）
add_executable(${PROJECT_NAME})
# gtest >= 1.17 requires C++17; raise only the test target, the library
# itself keeps the upstream default (C++14).
set_target_properties(${PROJECT_NAME} PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
```

conandata.yml 登记 `patch_type: portability`，经 `export_sources()` +
`apply_conandata_patches()` 随配方分发。整工程提 17 是兜底方案（语义面大，
库本体也被迫变 17），仅当测试目标无法独立寻址时用。

## 验证（真实证据）

- 修复前：真机 run `20260908T001036Z-7fc69c8d8c-33992` L1 fail，
  gtest-port.h 静态断言 ×15 + gtest-param-test.h 模板参数错误
- 修复后（patch 0001，后续轮次叠加其他修复）：run `20260908T022643Z-2a0be6cd82-9099`
  上游 67 个 GTest 用例全量编译执行 **67/67 PASSED**，test_package 6 断言全 PASS，
  G0/L0/L1/L4/L5 全 pass（L4 patches clean），exit_code=0

## 适用边界

- 触发面：`test_requires gtest/1.17.x` + 上游 CMake 钉死 C++ < 17（grep 根
  CMakeLists 的 `set(CMAKE_CXX_STANDARD`，注意有无 `if(NOT DEFINED)` 守卫——
  有守卫时 toolchain cache 变量可直接生效，无需补丁）
- 反例：库本体源码在 C++17 下编译报错 → 是库源码问题，先修源码，勿整体提标准；
  上游若用 `target_compile_options(-std=c++14)` 显式旗标，目标属性会与其竞争，
  补丁需一并移除显式旗标
- 备选：gtest < 1.17（1.14/1.12）仍支持 C++14，可用降版本规避；但本仓库制品仓
  统一 gtest/1.17.0.1，per-test-target 补丁是首选

## 查重

四范围（knowledge/graph/*.kv、knowledge/drafts/、index.tsv）按签名
`C\+\+ versions less than C\+\+17|gtest-port\.h` 与关键词 gtest/1.17、CXX_STANDARD 检索，
无既有条目（E096/E130/E293/E322/E470/E538 命中 "CXX_STANDARD" 字面但主题分别为
CMake policy/链接/安装路径等，无 gtest 1.17 门槛条目）。本条为新增。
