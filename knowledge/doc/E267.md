# E140: OpenHarmony CMake 平台名兼容

## 基本信息
- **严重度**: 2
- **类别**: platform-cmake-detection
- **触发工具**: cmake
- **阶段**: configuration

## 错误特征
```
CMAKE_SYSTEM_NAME.*(OHOS|HarmonyOS)|System is unknown to cmake.*(OHOS|HarmonyOS)|OS_LINUX.*not defined
```

**关键词**: CMAKE_SYSTEM_NAME, OHOS, HarmonyOS, OS_LINUX, platform detection, target_compile_definitions, object library

## 根因分析
OpenHarmony 工具链不会稳定使用 `CMAKE_SYSTEM_NAME=Linux`。官方 SDK 的
`ohos.toolchain.cmake` 设置为 `OHOS`，适配版 Conan 工具链可能映射为
`HarmonyOS`。只匹配 Linux 或只匹配其中一种拼写，会让本地 SDK 验证与 CI 静默
进入不同平台分支。

**影响范围**: 任何按 `CMAKE_SYSTEM_NAME` 路由 Unix 行为、共享库属性、依赖或平台宏的 CMake 工程和公共模块。

## 推荐方案
- **方法**: add-harmonyos-cmake-detection
- **描述**: CMake 平台分支同时匹配 `^(OHOS|HarmonyOS)$`；只在目标能力确实兼容时恢复 Unix 语义。若源码行为需要复用这一配置决策，使用项目私有特性宏，并把 `PRIVATE` 定义加到真正编译该源码的 target。
- **示例**:

```cmake
if(CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
  target_compile_definitions(obj.example PRIVATE EXAMPLE_OHOS_FEATURE=1)
endif()
```

- **禁止**: 只写 `STREQUAL "OHOS"` 或只写 `MATCHES "HarmonyOS"`，然后用另一套工具链验证；也禁止把定义挂到只消费 `$<TARGET_OBJECTS:...>` 的表面库，而遗漏真正编译源码的对象库。
- **自动修复**: false

## 验证
```bash
grep -R -E 'CMAKE_SYSTEM_NAME.*(OHOS|HarmonyOS)' CMakeLists.txt cmake
```

验证必须覆盖实际使用的两类入口：官方 SDK toolchain 和 Conan CI toolchain。Cling
1.3 的目标图验证中，前者实际使用 `OHOS`；补丁同时覆盖两种拼写后，
`libcling`/`libclingJupyter` 的版本软链规则均从 1 降为 0。涉及源码特性宏时还应导出
`compile_commands.json`，确认目标源码的真实编译命令包含该宏，并确认 `PRIVATE` 宏
未泄漏到无关 target。Cling 的 `CIFactory.cpp` 实际编译进 `obj.clingInterpreter`，
不能仅依据外层 `clingInterpreter` 名称推断定义会逆向传播。
