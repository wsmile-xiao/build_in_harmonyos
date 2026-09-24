# liquidfun

## 简介
LiquidFun 是 Google 基于 Box2D 2.3.0 扩展的 2D 刚体+粒子物理引擎（b2ParticleSystem 流体模拟），用于游戏物理仿真。

## OHOS 适配
- Box2D 2.3.0 全量 vendored 自带（liquidfun/Box2D/Box2D/ 54 源文件），与仓内 box2d/2.4.1 为不同 API 线，无外部依赖
- 上游构建树为 cmake-2.8 老式（-Werror 触发新 clang 告警 + Unittests 大小写笔误）→ patch 0001 注入自写 headless CMakeLists 直接编源
- 头文件按上游布局安装：include/Box2D/...（消费者 `#include <Box2D/Box2D.h>`）
- 上游 13 个 gtest 测试二进制（179 用例）在 conan build() 阶段用 vendored googletest 构建+bash 包装实跑
- 排除 freeglut/OpenGL/Testbed 示例（headless）

## 依赖
- 无

## 功能验证
```bash
conan create archives/l/liquidfun/1.1.0 -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64
```

## 参考
- 主页: https://google.github.io/liquidfun/
- 源码: https://github.com/google/liquidfun
