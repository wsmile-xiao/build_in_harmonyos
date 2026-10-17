# DRAFT：kylin-ai 系列 AI SDK gdbus 协议 XML 版本错配诊断

> Contributor: mkz--mkz | Status: Draft | Updated: 2026-09-03
> Source: PR（libkysdk-ai-private 1.1.0.1 适配 HarmonyOS PC）

## 背景

Kylin AI 系列 SDK（libkysdk-ai-private 1.1.0.1 等）客户端库源码按某版本协议的
gdbus glue 接口编写，构建时经 `kylin_ai_generate_gdbus_proto_code`（gdbus-codegen）
从协议 XML 生成 glue 头。协议 XML 随 libkylin-ai-system-private 内嵌 ai-proto 演进，
而独立 kylin-ai-proto 仓库未同步，导致生成 glue 与源码期望不匹配。

## 现象

编译期（非链接期）两类错误：
- `use of undeclared identifier 'ai_runtime_config_service_call_get_free_trial_models_sync'`
  —— 源码调用 XML 中不存在的方法（方法缺失）
- `no matching function for call to 'ai_runtime_assistant_call_prompts_sync'`
  —— 方法存在但签名不匹配：源码传 5 参（proxy, sessionId, &out, cancellable, error），
  生成 glue 只有 4 参（proxy, &out, cancellable, error），XML 的 prompts 缺
  `session_id` 输入参数

## 根因

独立 kylin-ai-proto 仓库（upstream 及全部发行分支）的 configservice.xml /
assistantservice.xml 旧于 libkysdk-ai-private 1.1.0.1 源码期望：缺
getFreeTrialModels / get_configured_nlp_model_list / set_current_nlp_model /
prompts 的 session_id 等接口。匹配协议在 libkylin-ai-system-private 1.2.0.1
内嵌的 ai-proto 中（Ubuntu 打包 libkysdk-ai-private 即依赖
libkylin-ai-system-private 提供协议）。

## 修复（协议源切换到内嵌 ai-proto）

1. conandata.yml 协议源改为
   `https://gitee.com/openkylin/libkylin-ai-system-private/repository/archive/debian%2F1.2.0.1-1.tar.gz`
   （gitee archive，curl UA；tag 名带 -1 需完整 URL 编码）
2. 配方 source()：get 后把 `vendor/kylin-ai-system/ai-proto` 挪到
   `vendor/kylin-ai-proto`，清理其余内容
3. 继续应用路径变量化补丁（KYLAI_GDBUS_CODEGEN / KYLAI_GDBUS_PROTOCOL_DIR）

## 诊断特征（可复用）

- 编译错误含 `use of undeclared identifier 'ai_runtime_*_sync'` 或
  `no matching function for call to 'ai_runtime_*_sync'`
- grep 生成目录 `*glue.h` 的该函数签名，参数数少于源码调用 → 协议版本错配
- 不要误判为编译/链接/工具链问题去改源码

## 验证

- 本库本地 `conan create` 全流程通过：3 个 .so（libkyai-config / libkyai-assistant /
  libkyai-data-management-client）编译链接 + 签名，test_package 探针 3 库 dlopen +
  3 头文件检查通过。
