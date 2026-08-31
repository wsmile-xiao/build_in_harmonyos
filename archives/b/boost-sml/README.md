# Boost.SML

Boost.SML（State Machine Language）是一个 C++14 header-only 的状态机实现库，
提供轻量、编译期可检查的有限状态机（FSM）与 UML 风格状态机建模能力。

## 功能概述

- Header-only，零运行时依赖，仅需 `#include <boost/sml.hpp>`
- 基于模板元编程的编译期状态机实现，事件/状态/转移在编译期验证
- 支持 guard、action、defer、process、sub-state machine、async 等特性
- C++14 起可用，兼容 GCC / Clang / MSVC

## OHOS 适配

- 该库为 header-only，无编译产物、无运行时二进制依赖，理论上可直接移植
- 适配要点：确认 OHOS 平台编译器（clang）对 C++14 模板的支持、
  空 SM 最小体积开关（`BOOST_SML_CFG_ENABLE_MIN_SIZE`，1.2.0 起默认关闭）
- 首次适配以归档骨架 + `conan create` 验证为主，后续按需补充平台专项验证

## 依赖关系

- 编译依赖：C++14 编译器（无第三方库依赖）
- 运行依赖：无

## 参考资料

- 官网: https://boost-ext.github.io/sml/
- 源码仓库: https://github.com/boost-ext/sml
- 变更日志: https://boost-ext.github.io/sml/CHANGELOG.html