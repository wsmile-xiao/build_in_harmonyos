# DRAFT-8959：kylin-ai 系列库 gdbus/grpc 协议生成宏硬编码路径变量化

> Contributor: mkz--mkz | Status: Draft | Updated: 2026-09-03
> Source: PR（libkylin-ai-system-private 1.2.0.0 适配 HarmonyOS PC）

## 背景

Kylin AI 子系统系列库（libkylin-ai-system-private 的 ai-proto、libkysdk-coreai-speech
的 vendored kylin-ai-proto 等）共享同一套 CMake 协议生成宏。宏内硬编码 Linux 绝对
路径，OHOS 上路径不存在导致配置期/生成期失败。

## 现象

- `kylin_ai_generate_gdbus_proto_code`：`set(XML_FILE /usr/share/kylin-ai/protocols/gdbus/...)`
  → `gdbus-codegen: Unable to find XML file: corespeechservice`（FATAL_ERROR）
- `COMMAND /usr/bin/gdbus-codegen` → execute_process 失败（OHOS 无 /usr/bin/gdbus-codegen）
- `kylin_ai_generate_grpc_proto_source/service`：`set(SRC_DIR /usr/share/kylin-ai/protocols/grpc/${PATH})`
  → proto 文件找不到
- `install(DIRECTORY protocols/usr/ DESTINATION /usr)` → 写 /usr 越权（Permission denied）

## 根因

宏与安装规则硬编码 Linux 布局：/usr/bin/gdbus-codegen、/usr/share/kylin-ai/protocols。
OHOS 上 gdbus-codegen 由 glib 配方提供（<glib>/bin/gdbus-codegen），协议文件安装到
Conan staging/prefix 下（prefix/share/kylin-ai/...），/usr 布局不存在。

## 修复（变量化 + install prefix）

1. `KylinAiProtoFunctions.cmake`：
   - `set(XML_FILE ${KYLAI_GDBUS_PROTOCOL_DIR}/${XML_FILE_NAME}.xml)`
   - `COMMAND ${KYLAI_GDBUS_CODEGEN}`
2. `KylinAiProtoGenerate.cmake`（两处）：
   - `set(SRC_DIR ${KYLAI_GRPC_PROTOCOL_DIR}/${PATH})`
3. `ai-proto/CMakeLists.txt`：
   - `install(DIRECTORY protocols/usr/ DESTINATION ${CMAKE_INSTALL_PREFIX})`
4. 配方 `generate()` 注入变量（从 self.dependencies 取 glib package_folder）：
   - `KYLAI_GDBUS_CODEGEN`、`KYLAI_GDBUS_PROTOCOL_DIR`、`KYLAI_GRPC_PROTOCOL_DIR`

## 复用价值

- libkylin-ai-system-private（本库）、libkysdk-coreai-speech（vendored kylin-ai-proto）
  及其它 kylin-ai 系列消费者库，遇 `gdbus-codegen` / `/usr/share/kylin-ai` 硬编码路径
  均可按本模式变量化。
- 纯协议/头库（INTERFACE target）的 Conan 配方要点：`package_type=header-library`、
  `package_info` 用 components 声明双 cmake 目标、消费者 `find_package` 用包名 +
  组件 target 链接（CMakeDeps 不按组件 cmake_file_name 单独产出 config 文件）。

## 验证

- 本库本地 `conan create` 全流程通过（3 补丁应用 → configure/install → test_package
  ctest 1/1 Passed + 协议文件存在性检查 OK）。
- 消费者冒烟：test_ai_engine.cpp 派生 AbstractAiEngine 断言 API（C++17 编译 +
  链接 KylinAiEngine::KylinAiEngine）。
