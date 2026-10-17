# DRAFT：Qt6 独立子模块在 cmake_find_mode=none 依赖下的 CMake 定位完整模式

> Source: qtscxml/6.11.1 HarmonyOS PC 适配（权威 CI PASS）
> Category: qt6-module-adapt | Status: Draft | E3XX 编号待知识系统分配

## 场景

Qt6 的独立子模块（qtscxml 提供 Qt6Scxml/Qt6StateMachine）在 OHOS PC 上作为 Conan
包适配。qtbase/6.11.1 使用 `cmake_find_mode=none`：它自带完整、可重定位的
`Qt6Config.cmake`，不允许 CMakeDeps 用生成配置遮蔽。子模块的 CMake 构建和消费
都必须直接使用 qtbase 的安装树来定位 Qt6 体系。

## 问题

若只依赖 CMakeDeps（默认 `cmake_find_mode=config`），会生成不完整的
`Qt6Config.cmake`，导致子模块找不到 `Platform/HarmonyOS.cmake`。其后果：

- CMake 把 HarmonyOS 当作未知平台 → 跳过共享库 SOVERSION/SONAME 处理 → 插件
  `DT_NEEDED` 退化为字面相对路径；
- Qt6Scxml/Qt6StateMachine 的组件依赖（core/gui）无法正确传导到下游。

另外 OHOS Clang 暴露 ARM crypto 特性，但平台 `arm_neon.h` 缺少 Qt hash 所用的
AES intrinsics，需要 `-DQT_NO_ARM_AES_INTRINSICS`；qtbase 提供 Gui 时
`qeventtransition` feature 启用，`Qt6StateMachine` 公开链接 `Qt::Gui`，组件
requires 必须带 `qtbase::gui`。

## 修复（要点）

1. `generate()` 设 `CMAKE_PREFIX_PATH=<qtbase package_folder>`；
2. `CMAKE_MODULE_PATH=<qtbase>/lib/cmake/Qt6/platforms`（携带
   `Platform/HarmonyOS.cmake`，`include Linux`）；
3. test_package 用缓存变量直接定位：`Qt6_DIR=<qtbase>/lib/cmake/Qt6`、
   `Qt6Scxml_DIR=<pkg>/lib/cmake/Qt6Scxml`、
   `Qt6StateMachine_DIR=<pkg>/lib/cmake/Qt6StateMachine`；
4. `package_info` 设 `cmake_find_mode=none` + `builddirs=["lib/cmake"]`；
   组件 scxml→`qtbase::core`、statemachine→`qtbase::core+gui`。

## 验证

- `conan create qtscxml/6.11.1`：编译通过，test_package `test_qtscxml` PASS；
- 2026-08-30 权威 FULL CI：17 个上游测试 17/17 PASS（早期离线阶段 6/6）；安装产物 SONAME 完整并带 `.codesign` 段。

## 可复用边界

- 所有 Qt6 独立子模块（Scxml/StateMachine/quick…）在 OHOS 的 Conan 适配通用；
- qtbase 必须保持 `cmake_find_mode=none`，不要改为 config 模式；
- 若下游需要额外 Qt6 组件（如 Widgets），同步扩展组件 requires。

## 与现有知识的关系

- `E2149` 覆盖设备无 curl 时 conan 镜像兜底下载，与本草稿（cmake_find_mode 定位）
  主题不同，无重叠。
