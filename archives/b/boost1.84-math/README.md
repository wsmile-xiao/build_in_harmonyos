# boost1.84-math

[Boost.Math](https://www.boost.org/doc/libs/1_84_0/libs/math/) 组件独立包
（boost 1.84.0 math 裁剪）。

## 内容

- **编译库（6 个静态库）**：`libboost_math_{tr1,tr1f,tr1l,c99,c99f,c99l}.a`
  - `tr1` 系：TR1 特殊函数 C 接口（beta/bessel/legendre/hermite/...）
  - `c99` 系：C99 数学函数 C 接口（acosh/cbrt/erf/tgamma/...）
  - 后缀：无=double，`f`=float，`l`=long double
- **header-only**：完整 `boost/` 头文件树（constants、gcd/lcm、quaternion、
  distributions、statistics、special_functions 模板、interpolation、
  quadrature 等）

## 用法（Conan / CMake）

```cmake
find_package(BoostMath REQUIRED CONFIG COMPONENTS tr1 tr1f c99)
target_link_libraries(app PRIVATE BoostMath::tr1 BoostMath::tr1f BoostMath::c99)
# header-only 部分：BoostMath::headers（或直接 include 后使用，define 自动传播）
```

## 平台说明

- HarmonyOS PC (aarch64-linux-ohos)，clang 15，libc++/musl
- b2 构建系统不兼容 OHOS（E068/E099），手动编译（沿 1.84.0 底稿方案）
- OHOS musl 的 long double 数学函数族为 double 精度别名，`l` 变体库精度
  等同 double（符号/ABI 完整）；double/float 全量上游断言通过
- 版本：1.84.0（对应 boost 1.84.0）

## 上游测试

上游 boost.math 官方测试 `libs/math/test/test_tr1.c`（tr1/c99 C 接口数值
正确性，269 断言/模式）绕过 b2 手动编译运行：普通模式（float+double，
538 断言）100% 通过；TEST_LD 模式的 95 项失败为 OHOS musl long double
精度别名平台限制（详见 notes.md 问题 4 与 PR 描述豁免说明）。

## 包结构

- `1.84.0/conanfile.py`：6 库手动编译配方（b2 不兼容 OHOS，E068/E099）
- `1.84.0/patches/0001`：sp_thread_sleep 特性检测宏（保护下游 smart_ptr 用户）
- `1.84.0/test_package/`：CMake 消费者验证（10 组 API 断言）
- 依赖：无（Boost.Math 不需要 zlib）
