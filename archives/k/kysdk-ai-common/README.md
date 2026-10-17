# kysdk-ai-common

Kylin AI 公共库（openKylin AI 子系统 SDK 层底座），提供 `is_ai_subsystem_inited()`、
`AiSdkCommonErrorCode`、`ModelDeployType` 等公共 API/枚举，供 `libkysdk-genai-*`、
`libkysdk-coreai-*` 等 SDK 包依赖。

## 已适配版本

| 版本 | 上游 | 状态 |
|------|------|------|
| 1.1.0.1 | gitee.com/openkylin/kysdk-ai-common (tag upstream/1.1.0.1, commit 8e1950b9) | built |

## 要点

- 纯 C++ CMake 库，无外部依赖
- CMake target：`KysdkAiCommon::KysdkAiCommon`（cmake_file_name=KysdkAiCommon）
- 补丁 1 个：移除 `install(DIRECTORY usr/ DESTINATION /usr)`（直写系统根）
- 上游无测试（清点证据见 1.1.0.1/notes.md），test_package 消费者测试 3 断言
