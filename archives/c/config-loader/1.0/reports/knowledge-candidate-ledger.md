# 知识候选台账 — config-loader 1.0

> task_type: 知识库扩展；knowledge_candidate_observation: required
> 本台账记录适配过程中每个非噪声候选：真实错误、根因、修复、验证、适用范围与
> 四范围查重（index.tsv 正式条目 / knowledge/doc / knowledge/graph .kv / knowledge/drafts 草稿）结果。

## 候选 C1：CMake custom target 引用空全局 CMAKE_RUNTIME_OUTPUT_DIRECTORY 导致复制到根目录

| 字段 | 内容 |
|---|---|
| 真实错误 | 构建失败：`Error copying directory from ".../test/ut/configs" to "/configs"`（目标路径被拼成根目录 /configs） |
| 根因 | 上游 `test/ut/CMakeLists.txt` 的 `add_custom_target(copy_configs)` 用 `COMMAND ${CMAKE_COMMAND} -E copy_directory ... ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/configs`。`CMAKE_RUNTIME_OUTPUT_DIRECTORY` 是**全局目录变量**，上游未设置（只有 `set_target_properties(RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)` 是目标属性），CMake 4.x 下变量为空 → 目标路径被拼成 `/configs` → 复制到根目录因权限失败 |
| 修复 | 最小补丁：改为 `copy_directory ... ${CMAKE_BINARY_DIR}/bin/configs`（与目标属性输出目录一致） |
| 验证 | patch 后 `cmake --build` 成功（exit 0）；`config_loader_test` 全量 29/29（352 assertions）通过；conan create（ohos-aarch64）内 CTest 2/2 通过 |
| 适用范围 | 上游 CMake 在 custom target 命令中引用全局 `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 而只设置目标属性/或未设置全局变量的库；CMake 4.x 尤其暴露（旧 CMake 可能恰好有全局值） |
| 正式知识(index.tsv/doc) | 未命中 |
| 图谱(graph .kv) | 未命中（E103/E187/E383 为 CMake 4 兼容性/其他主题，非本问题） |
| 草稿(drafts) | DRAFT-ohos-cmake-add-test-target-file：`trigger_overlap`（均涉测试构建目录/CMAKE_RUNTIME_OUTPUT_DIRECTORY/CMAKE_BINARY_DIR 路径问题），但其根因是 add_test 硬编码 TEST_PATH、方案是 `$<TARGET_FILE:>` 生成器表达式；本候选根因是**空全局变量导致的 custom copy target 路径错乱**、方案是补全为 `CMAKE_BINARY_DIR/bin`。根因/方案均不同，新增差异成立且已由真实日志验证 |
| 关系 | similar_to: DRAFT-ohos-cmake-add-test-target-file; caused_by: CMake 全局目录变量未设置 |
| 判定 | **new_draft**（路径 B）→ 建立同 stem 草稿 DRAFT-cmake-custom-target-empty-runtime-output-dir（.kv/.md 配对） |

## 候选 C2：conan 相对路径 profile 被遮蔽 → 解析到默认 profile（libstdc++11/gnu14）

| 字段 | 内容 |
|---|---|
| 真实错误 | `conan create` 时 catch2 等依赖以 `compiler.libcxx=libstdc++11 compiler.cppstd=gnu14`（默认 profile）解析，OHOS clang 报 `invalid library name in argument '-stdlib=libstdc++'`；`conan profile show -pr:h=相对路径` 显示的是默认 profile 而非 worktree 官方文件 |
| 根因 | 相对路径 `-pr:h=ci/conan/profiles/ohos-aarch64` 未命中 worktree 官方 profile（本机 ~/.conan2/profiles 同名嵌套旧 profile/回退默认），与官方 profile（libcxx=libc++/cppstd=17）不一致 |
| 修复 | 使用绝对路径 `-pr:h=$PWD/ci/conan/profiles/ohos-aarch64 -pr:b=...` 后，catch2 直接命中制品仓预编译 binary（4b9772…），不再本地构建；全流程通过 |
| 验证 | 绝对路径后 conan create 全部依赖 - Cache，config-loader conan create/CTest 2/2 通过（exit 0） |
| 草稿查重 | DRAFT-elfio-3.9-conan-profile-relative-path-shadowing、DRAFT-tiny-utf8-4.4.3-conan-profile-relative-path-shadow：**exact_duplicate**（同一根因、同一修复、受影响 scope 一致） |
| 判定 | **reuse_existing**（复用既有草稿；无独立新增差异） |

## 候选 C3：OHOS clang 拒绝 -stdlib=libstdc++

| 字段 | 内容 |
|---|---|
| 真实错误 | `clang-15: error: invalid library name in argument '-stdlib=libstdc++'`（OHOS clang 仅提供 libc++） |
| 根因 | profile/默认值中 compiler.libcxx 为 libstdc++ 变体，OHOS 工具链无 libstdc++ |
| 修复 | 确保使用官方 ohos-aarch64 profile（libcxx=libc++）— 即 C2 的绝对路径修复 |
| 查重 | knowledge/graph/E455：**exact_duplicate**（error_signature `invalid library name in argument '-stdlib=libstdc++'` 完全一致；rec_approach use-ohos-profile-libcxx） |
| 判定 | **reuse_existing**（正式条目 E455 已覆盖） |

## 候选 C4：PUBLIC 编译宏（HAS_*）在 Conan 打包后需 cpp_info.defines 导出 + 解析器依赖显式链接

| 字段 | 内容 |
|---|---|
| 真实错误 | 消费端编译/运行：`loadJSON2Obj` 返回 `ERR_UNSUPPORTED_PARSER`（HAS_JSONCPP 宏缺失）；随后 `tinyxml2.h file not found`（依赖 include 未传播） |
| 根因 | 上游 `target_compile_definitions(... PUBLIC HAS_*)` 宏不随 Conan install/cpp_info 导出；公开头文件 include <tinyxml2.h> 等，消费者需显式 require 并链接解析器库 |
| 修复 | `package_info()` 导出 `cpp_info.defines = ["HAS_TINYXML2","HAS_JSONCPP","HAS_YAMLCPP"]`；test_package/消费者显式 `requires + target_link_libraries` 三个解析器 |
| 验证 | 修复后 test_config-loader 与 ohos_platform_test 均通过（CTest 2/2） |
| 查重 | DRAFT-flatbuffers-locale-macro-export-consistency：**solution_overlap**（核心一致：CMake 级编译宏不随安装导出 → cpp_info.defines 导出；影响面一致）。本候选新增差异小（PUBLIC target 宏场景 + 依赖显式链接的组合），方案已被该草稿覆盖 |
| 判定 | **reuse_existing**（复用 flatbuffers 草稿方案；不另建草稿避免硬凑） |

## 候选 C5：config-loader dumpObj2OStream 输出自定义调试格式（非标准 JSON）

| 字段 | 内容 |
|---|---|
| 现象 | `dumpObj2OStream` 序列化输出 `{ .x{1.5}, .y{-2.25}, }`（自定义格式），不能直接反哺 `loadJSON2Obj`（返回 ERR_ILL_FORMED） |
| 判断 | 库特有公开 API 行为，非跨库通用知识；已记入 notes.md 与 test_package 注释（专项测试改用标准 JSON 做往返） |
| 查重 | 无命中 |
| 判定 | **path_a_no_knowledge**（库特定行为，不入草稿） |

## 路径决定

- **new_draft**：C1（本库新建 DRAFT-cmake-custom-target-empty-runtime-output-dir 草稿 .kv/.md）
- **reuse_existing**：C2（两草稿 exact_duplicate）、C3（E455 exact_duplicate）、C4（flatbuffers 草稿 solution_overlap）
- **path_a_no_knowledge**：C5（库特有）
- 结论：走知识库扩展（路径 B），随 config-loader 1.0 归档 PR 提交新建 C1 草稿；无【知识库扩展】之外的新建知识 PR。