// test_package/test.cpp — libkysdk-genai 1.1.0.1 消费者实质测试（R34 非空壳）。
//
// 上游 tests/testGenAiNlp.cpp 是交互式程序（g_main_loop_run + std::getchar()
// 等待键盘输入，且依赖真实 AI 云服务认证：百度 ERNIE / 讯飞 Spark），OHOS CI
// 无法运行。本测试适配为「不依赖云服务/AI 运行时服务进程」的可运行实质路径：
//   1. 对象生命周期（ChatModelConfig / ChatMessage / GenAiTextSession 建/毁）
//   2. genai_text_init_session 无 AI 运行时服务（genai-nlp.sock 不存在）时
//      返回 AISDK_RUNTIME_ERROR（真实连接失败错误路径，实测 ~10s 重连退避）
//   3. chat_result_get_* 空指针默认值（NLP_INPUT_INVALID / nullptr / true）
//   4. PromptId / ModelDeployType / AiSdkCommonErrorCode 枚举值
//
// 全部 16 项断言通过 → 退出 0。

#include <kylin-ai/genai/text/chat.h>
#include <kylin-ai/genai/text/chatmessage.h>
#include <kylin-ai/genai/text/config.h>
#include <kylin-ai/genai/text/error.h>
#include <kylin-ai/genai/text/result.h>

#include <kylin-ai/common/enums.h>
#include <kylin-ai/common/error.h>

#include <cstdio>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        ++g_checks;                                                            \
        if (cond) {                                                            \
            std::printf("PASS: %s\n", msg);                                    \
        } else {                                                               \
            std::fprintf(stderr, "FAIL: %s\n", msg);                           \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

int main() {
    // 1) ChatModelConfig 生命周期 + 参数设置
    ChatModelConfig *cfg = chat_model_config_create();
    CHECK(cfg != nullptr, "chat_model_config_create returns non-null");
    chat_model_config_set_name(cfg, "百度-ERNIE-Bot-4");
    chat_model_config_set_top_k(cfg, 0.5);
    chat_model_config_set_deploy_type(cfg, ModelDeployType::PublicCloud);
    chat_model_config_destroy(&cfg);
    CHECK(cfg == nullptr, "chat_model_config_destroy nulls pointer");

    // 2) ChatMessage 生命周期 + 消息角色
    ChatMessage *msg = chat_message_create();
    CHECK(msg != nullptr, "chat_message_create returns non-null");
    chat_message_add_system_message(msg, "system");
    chat_message_add_user_message(msg, "hello");
    chat_message_add_assistant_message(msg, "hi");
    chat_message_destroy(&msg);
    CHECK(msg == nullptr, "chat_message_destroy nulls pointer");

    // 3) GenAiTextSession 生命周期 + init 错误路径（无 AI 运行时服务）
    GenAiTextSession *session = genai_text_create_session();
    CHECK(session != nullptr, "genai_text_create_session returns non-null");
    genai_text_set_model_config(session, nullptr);  // null 配置安全路径
    genai_text_result_set_callback(session, nullptr, nullptr);
    int ec = genai_text_init_session(session);
    // OHOS CI 无 kylin-ai-runtime 的 genai-nlp D-Bus 服务（unix:path=
    // /tmp/.kylin-ai-runtime-unix/<uid>/genai-nlp.sock 不存在）→ 服务连接失败
    // → 重连退避后返回 AISDK_RUNTIME_ERROR。
    CHECK(ec == AISDK_RUNTIME_ERROR,
          "genai_text_init_session returns AISDK_RUNTIME_ERROR without AI server");
    genai_text_destroy_session(&session);
    CHECK(session == nullptr, "genai_text_destroy_session nulls pointer");

    // 4) ChatResult 访问器空指针默认值（src/_chatresult.cpp 语义）
    CHECK(chat_result_get_assistant_message(nullptr) == nullptr,
          "chat_result_get_assistant_message(nullptr)==nullptr");
    CHECK(chat_result_get_finish_reason_message(nullptr) == nullptr,
          "chat_result_get_finish_reason_message(nullptr)==nullptr");
    CHECK(chat_result_get_error_code(nullptr) == NLP_INPUT_INVALID,
          "chat_result_get_error_code(nullptr)==NLP_INPUT_INVALID(100)");
    CHECK(chat_result_get_error_message(nullptr) == nullptr,
          "chat_result_get_error_message(nullptr)==nullptr");
    CHECK(chat_result_get_is_end(nullptr) == true,
          "chat_result_get_is_end(nullptr)==true");

    // 5) 枚举值（include/kylin-ai/genai/text/error.h、common/enums.h、common/error.h）
    CHECK(SUMMARY == 9, "PromptId SUMMARY == 9");
    CHECK(TRANSLATE_CHINESE_TO_ENGLISH == 3,
          "PromptId TRANSLATE_CHINESE_TO_ENGLISH == 3");
    CHECK(ModelDeployType::PublicCloud == 1, "ModelDeployType::PublicCloud == 1");
    CHECK(AISDK_RUNTIME_ERROR == 3, "AISDK_RUNTIME_ERROR == 3");

    if (g_failures == 0) {
        std::printf("test libkysdk-genai 1.1.0.1: OK (%d checks passed)\n",
                    g_checks);
        return 0;
    }
    std::fprintf(stderr, "%d/%d checks FAILED\n", g_failures, g_checks);
    return 1;
}
