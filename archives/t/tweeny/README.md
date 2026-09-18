# tweeny

Modern C++ inbetweening/tweening library for animations — header-only with
30+ easing functions, multi-point tweens and timeline seeking.

- 上游仓库: https://github.com/mobius3/tweeny
- 版本: 3（上游发布形态为 git tag `v3`；本仓库制品版本 `tweeny/v3`）
- 许可证: MIT
- 类型: header-only（CMake INTERFACE 库，上游自带 install/export 规则）
- 构建系统: CMake（`TWEENY_BUILD_EXAMPLES/EXTRAS/DOCUMENTATION=OFF`）

## 用途

用声明式 API 生成插值动画：

```cpp
auto tween = tweeny::from(0.0f).to(100.0f).during(10).via(tweeny::easing::quadraticInOut);
tween.step(5);              // 推进一步（参数是时间单位）
float v = tween.peek();     // 当前值
```

支持 30+ 缓动、自定义缓动、多点 tween、异构多值 tween、正/反向播放与任意时间 seek。
单值 tween 走标量 API（`tween<T>` 特化，`peek()/step()/seek()` 直接返回 `T`）；
多值 tween 返回 `std::tuple`。

## 在 OpenHarmony / HarmonyOS PC 上

- 包安装路径：`include/tweeny/*.h/.tcc` 与 `lib/cmake/Tweeny/*.cmake`
  （镜像上游 `$<INSTALL_INTERFACE:include/tweeny>`）
- 消费方：

  ```cmake
  find_package(Tweeny REQUIRED)
  target_link_libraries(app Tweeny::tweeny)
  ```
  ```cpp
  #include <tweeny.h>
  ```

- 上游 `cmake_minimum_required(VERSION 3.0)` 会被 CMake 4.x 直接拒绝；本配方注入
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`（知识条目 E103），下游自带构建时遇同样报错可照此处理。
- 上游 v3 无测试套件，本仓库的验证由 `test_package` 消费者测试承载（17 条断言，
  覆盖线性插值、多值 tween、缓动形状、seek 越界钳制、onStep 回调与步进越界钳制）。
