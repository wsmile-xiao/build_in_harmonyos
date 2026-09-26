# DRAFT-cmake-custom-target-empty-runtime-output-dir

> 草稿知识项 — CMake custom target 引用空全局 CMAKE_RUNTIME_OUTPUT_DIRECTORY 导致复制到根目录
> 来源：config-loader 1.0 适配（feat/config-loader-1.0，2026-09-25）
> 同 stem 配对：`knowledge/drafts/DRAFT-cmake-custom-target-empty-runtime-output-dir.kv`

## 问题（现象 / error_signature）

- 上游 `test/ut/CMakeLists.txt` 的 `add_custom_target(copy_configs)` 用
  `COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/configs ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/configs`
  复制测试数据文件。
- CMake 4.x 构建时报错：`Error copying directory from ".../test/ut/configs" to "/configs"`——
  目标路径变成根目录 `/configs`，复制因权限失败，构建中断（`make: *** Error 2`）。

## 根因（root_cause）

1. `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 是**全局目录变量**，不是目标属性；上游只在
   `set_target_properties(config_loader_test PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)`
   里设置了**目标级**输出目录，从未设置全局变量。
2. 旧 CMake 环境的某些路径下该全局变量恰好被赋值（或默认非空），掩盖了问题；CMake 4.x
   下全局变量为空字符串 → `${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/configs` 被拼成 `/configs`。
3. 在 custom target 的命令串（configure 期展开的普通变量引用）中，CMake 不会做目标
   属性解析——目标属性的 RUNTIME_OUTPUT_DIRECTORY 只对目标自身生效，不作用于命令串。

## 可复用方案（rec_approach: explicit-binary-dir-in-custom-target-copy）

把 custom target 的 copy 目标路径改为显式构建目录 `${CMAKE_BINARY_DIR}/bin/configs`
（与该目标属性输出目录一致），不依赖全局变量：

```cmake
# 上游（问题）
add_custom_target(copy_configs
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/configs
            ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/configs)
# 修复
add_custom_target(copy_configs
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/configs
            ${CMAKE_BINARY_DIR}/bin/configs)
```

- 若上游输出目录由目标属性控制且可配置，将同一路径源统一定义为一个 CMake 变量，
  供 `set_target_properties` 与 custom target 共同引用，避免二次漂移。

## 适用条件（affected_scope）

- 上游在 `add_custom_target` / `add_custom_command` 的命令串中引用全局
  `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 的 CMake 项目（未先设置该全局变量）；
- 测试数据/资源文件通过 custom target 复制到运行目录的库；
- CMake 4.x、Conan 交叉构建、输出目录被改写（目录级或目标级）的环境必然暴露。

## 反例（不适用场景）

- 上游已显式 `set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ...)` 设置全局变量的项目；
- custom target 直接使用目标名/生成器表达式 `$<TARGET_FILE_DIR:...>` 定位产物的项目；
- 不复制资源文件的纯库项目。

## 验证证据（真实命令 + 结果）

- config-loader 1.0 修复前：`cmake --build build-static -j2` → 
  `Error copying directory from ".../test/ut/configs" to "/configs"`（exit 2）。
- 修复补丁 `0001-test-ut-CMakeLists.txt.patch` 后：`cmake --build build-static -j2` 成功（exit 0）；
  `./build-static/bin/config_loader_test` → `All tests passed (352 assertions in 29 test cases)`（exit 0）；
  `conan create`（ohos-aarch64）内 CTest 2/2 通过（消费者 + 平台专项）。

## 适用边界与查重差异

- 查重：knowledge/graph/index.tsv、doc/、graph .kv 均未命中；
  knowledge/drafts/DRAFT-ohos-cmake-add-test-target-file 仅 `trigger_overlap`
  （同属测试构建目录 / CMAKE_RUNTIME_OUTPUT_DIRECTORY / CMAKE_BINARY_DIR 路径主题），
  但其根因是 add_test 硬编码 TEST_PATH、方案是 `$<TARGET_FILE:>` 生成器表达式；
  本条目根因是**空全局变量导致的 custom copy 目标路径错乱**、方案是显式
  `${CMAKE_BINARY_DIR}/bin` 路径，二者根因/方案互不相同，新增差异成立。
- 反例验证：本条目修复不依赖 `$<TARGET_FILE:>`（custom target 无单一 target），
  与 DRAFT-ohos-cmake-add-test-target-file 不冲突；CTest 注册仍用 add_test + WORKING_DIRECTORY。

## 相关关系

- similar_to: DRAFT-ohos-cmake-add-test-target-file（测试数据/产物路径主题）
- caused_by: CMake 全局目录变量未设置（目标属性 ≠ 全局变量）
- conflicts_with: 无