# kguiaddons 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM/KDE Frameworks 6)
- 编译日期: 2026-08-24
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64, libc++, cppstd=17)
- 状态: published

## 编译步骤

conan create 流水线（profile ohos-aarch64）：
1. `requires qtbase/6.11.1`，`tool_requires ecm/6.26.0`
2. CMakeToolchain 变量：`KF_IGNORE_PLATFORM_CHECK=TRUE`、`WITH_WAYLAND=OFF`、
   `WITH_X11=OFF`、`USE_DBUS=OFF`、`BUILD_GEO_SCHEME_HANDLER=OFF`、
   `BUILD_PYTHON_BINDINGS=OFF`、`BUILD_TESTING=ON`
3. generate() 手工注入 ECM_MODULE_PATH 与 qtbase lib/cmake 路径
   （qtbase 为 cmake_find_mode=none）
4. build() 内跑上游 ctest 全量 autotests（8 项全过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 Failed to find required Qt component "Qml" | src/qml 子目录在 TARGET Qt6::Qml 存在时才加入，但上游某处仍探测 Qml 组件 | 上游日志显示为非致命探测；实际由 BUILD_PYTHON_BINDINGS=OFF + 环境无 Qt6Qml 自动跳过，无需补丁 |
| 2 | test_package 运行时 Error loading shared library libQt6Gui.so.6 | test() 直接 run 二进制时未加载 conanrun 环境 | test() 中 self.run(..., env="conanrun") 并物化 libKF6*.so 符号链接到兼容 bin/ |
| 3 | cmake.test() 报 No rule to make target 'test' | test_package/CMakeLists.txt 未定义任何 add_test，make test 无目标 | 移除 cmake.test() 调用，仅运行消费者二进制 |

## 源码修改

无补丁（patches: {}）。全部通过 CMake 变量开关达成 OHOS 基线。

## 依赖版本

- qtbase/6.11.1（制品仓已发布）
- ecm/6.26.0（tool_requires，制品仓已发布）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify kguiaddons 6.26.0
# G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
# 上游 ctest: 8/8 通过
```

## 注意事项

- kcolorscheme 依赖本包（KF6GuiAddons ≥6.26）；kcolorscheme 的 PRIVATE 链接
  还需要 ki18n/6.26.0（归档已有）。
- 本包配方是纯 Qt6::Gui 核心库的 KDE Frameworks 最简模板：WAYLAND/X11/DBus/
  PYTHON 全关即可零补丁通过，后续同类包可参考。
---

**编译结束**: 2026-08-24 13:35
**最终状态**: published
