# libkysdk-genai

麒麟 AI 生成式 AI（GenAI）NLP 客户端库（openKylin，上游仓库项目名 `libkysdk-genai-nlp`），
提供 `kylin-ai/genai/text/` 下的 `chat / chatmessage / config / error / result` C 接口，
经 D-Bus 与 AI 运行时服务（genai-nlp.sock）交互实现对话、历史消息、系统提示词等功能。

## 已适配版本

| 版本 | 上游 | 状态 |
|------|------|------|
| 1.1.0.1 | gitee.com/openkylin/libkysdk-genai-nlp (tag upstream/1.1.0.1, commit 47f0725a) | built |

## 要点

- CMake（C++17）共享库，产物 `libkysdk-genai-nlp.so`（SONAME 显式注入）
- 依赖：kysdk-ai-common/1.1.0.1、libkysdk-ai-private/1.1.0.1、glib/2.88.0.1、
  jsoncpp/1.9.8、json-glib/1.10.6、openssl/3.5.8.1
- KylinAiProto（gdbus 协议生成宏）制品仓无配方 → 配方内 vendor
  （libkylin-ai-system-private debian/1.2.0.1-1 内嵌 ai-proto）
- 补丁 5 个：jsoncpp 头前缀、CMakeLists（JsonCpp CONFIG / link_directories /
  usr install 前缀 / SONAME）、KylinAiProto 宏路径变量化、公开头 include 全路径
- 上游测试为交互式 + 依赖真实 AI 云服务（OHOS CI 不可运行，清点证据见
  `1.1.0.1/notes.md` 申报表），test_package 提供 16 断言鸿蒙特有实质测试
