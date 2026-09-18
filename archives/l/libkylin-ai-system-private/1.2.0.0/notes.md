# libkylin-ai-system-private 1.2.0.0 — 适配笔记

## 上游
- 仓库: https://gitee.com/openkylin/libkylin-ai-system-private（openKylin 孵化期）
- tag: debian/1.2.0.0（HEAD 4a427a6e，与 ubuntu/1.2.0.0-0ubuntu1 同 commit）
- 归档: `repository/archive/debian%2F1.2.0.0.tar.gz`（tag 含斜杠需 URL 编码）
- sha256: 695d1fa8c572d549cea27eb1e48929c220ba74528141ec49ff3e50be48976513
- 无第三方依赖（debian/control Build-Depends 仅 cmake），无测试目录

## 结构
- `ai-engine/`: header-only C++17 INTERFACE 库（KylinAiEngine），AI 引擎插件抽象接口
  - include/kylin-ai/ai-engine/*.h + include/kylin-ai/aiengine.h
  - cmake/KylinAiEngineFunctions.cmake（kylin_ai_add_engine_plugin）
- `ai-proto/`: INTERFACE 库（KylinAiProto），仅协议定义文件，无编译产物
  - protocols/usr/share/kylin-ai/protocols/gdbus/*.xml（11 个）
  - protocols/usr/share/kylin-ai/protocols/grpc/**/*.proto（9 个）
  - cmake/KylinAiProtoFunctions.cmake（gdbus 胶水生成宏）
  - cmake/KylinAiProtoGenerate.cmake（grpc 胶水生成宏）

## 适配要点（3 个补丁，与 libkysdk-coreai-speech 的 kylin-ai-proto 同模式）
1. 0001: ai-proto `install(DIRECTORY protocols/usr/ DESTINATION /usr)` 绝对路径越权
   → `DESTINATION ${CMAKE_INSTALL_PREFIX}`（同 speech 0004）
2. 0002: KylinAiProtoFunctions.cmake 硬编码 `/usr/bin/gdbus-codegen` 与
   `/usr/share/kylin-ai/protocols/gdbus/` → `${KYLAI_GDBUS_CODEGEN}` / `${KYLAI_GDBUS_PROTOCOL_DIR}`
   （同 speech 0002）
3. 0003: KylinAiProtoGenerate.cmake 硬编码 `/usr/share/kylin-ai/protocols/grpc/`
   → `${KYLAI_GRPC_PROTOCOL_DIR}`

## 其他
- gitee 归档按 User-Agent 过滤（Conan python-requests UA 返回 HTML 挑战页），
  get() 显式传 `headers={"User-Agent": "curl/8.0"}`（同 speech 教训）
- 路径判定: A + B（gdbus/grpc 协议宏硬编码路径变量化是一类可跨库复用的诊断模式：
  kylin-ai 系列多个库共享同一宏模板，OHOS 下必须变量化）
- 上游测试: 无（如实申报 0）；新增消费者冒烟 1 入口（test_ai_engine.cpp 派生
  AbstractAiEngine 断言 API + conanfile.py 校验协议文件存在）
