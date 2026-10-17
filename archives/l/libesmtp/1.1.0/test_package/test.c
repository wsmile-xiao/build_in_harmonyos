// test_package 实质测试：链接 libesmtp 并调用 SMTP 会话/消息 API（R34 反空壳）。
// 全程离线：只组装会话、消息、收件人、头字段与消息回调，不调用 smtp_start_session()。
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <libesmtp.h>

static int msg_enum_count = 0;
static void count_message(smtp_message_t message, void *arg)
{
    (void)message;
    (*(int *)arg)++;
    msg_enum_count++;
}

static int rcpt_enum_count = 0;
static void count_recipient(smtp_recipient_t recipient, const char *mailbox, void *arg)
{
    (void)recipient;
    (void)arg;
    if (mailbox == NULL || mailbox[0] == '\0') {
        fprintf(stderr, "FAIL: recipient mailbox empty\n");
    }
    rcpt_enum_count++;
}

static const char *message_text = "Subject: HarmonyOS probe\r\n\r\nHello libesmtp\r\n";

int main(void)
{
    char verbuf[64];
    int failures = 0;

    /* 断言 1: 会话创建成功 */
    smtp_session_t session = smtp_create_session();
    if (session == NULL) {
        fprintf(stderr, "FAIL: smtp_create_session returned NULL\n");
        return 2;
    }
    printf("PASS[1/6]: smtp_create_session non-NULL\n");

    /* 断言 2: 版本查询与前缀匹配（参照数据非空，避免空比空） */
    if (!smtp_version(verbuf, sizeof(verbuf), Ver_VERSION)) {
        fprintf(stderr, "FAIL: smtp_version failed\n");
        failures++;
    } else if (strncmp(verbuf, "1.1.0", 5) != 0) {
        fprintf(stderr, "FAIL: version mismatch: got '%s', want prefix '1.1.0'\n", verbuf);
        failures++;
    } else {
        printf("PASS[2/6]: smtp_version='%s'\n", verbuf);
    }

    /* 断言 3: 服务器与本地主机名设置 */
    if (!smtp_set_server(session, "localhost:25")) {
        fprintf(stderr, "FAIL: smtp_set_server failed\n");
        failures++;
    } else if (strcmp(smtp_get_server_name(session), "localhost") != 0) {
        fprintf(stderr, "FAIL: server name got '%s'\n", smtp_get_server_name(session));
        failures++;
    } else if (!smtp_set_hostname(session, "harmonyos-pc")) {
        fprintf(stderr, "FAIL: smtp_set_hostname failed\n");
        failures++;
    } else {
        printf("PASS[3/6]: server='localhost', hostname set\n");
    }

    /* 断言 4: 消息组装（发件人/收件人/头/消息体回调） */
    smtp_message_t message = smtp_add_message(session);
    if (message == NULL) {
        fprintf(stderr, "FAIL: smtp_add_message returned NULL\n");
        failures++;
    } else {
        int ok = 1;
        ok &= !!smtp_set_reverse_path(message, "sender@example.org");
        ok &= (smtp_add_recipient(message, "rcpt@example.org") != NULL);
        ok &= !!smtp_set_header(message, "Subject", "HarmonyOS probe");
        ok &= !!smtp_set_message_str(message, (void *)message_text);
        ok &= !!smtp_dsn_set_ret(message, Ret_FULL);
        ok &= !!smtp_size_set_estimate(message, (unsigned long)strlen(message_text));
        if (!ok) {
            fprintf(stderr, "FAIL: message assembly API returned failure\n");
            failures++;
        } else {
            printf("PASS[4/6]: message assembled (reverse-path/recipient/header/body/dsn/size)\n");
        }
    }

    /* 断言 5: 枚举回调真实触发且计数正确 */
    {
        int nmsg = 0;
        rcpt_enum_count = 0;
        if (!smtp_enumerate_messages(session, count_message, &nmsg) || nmsg != 1) {
            fprintf(stderr, "FAIL: enumerate_messages count=%d, want 1\n", nmsg);
            failures++;
        } else if (!smtp_enumerate_recipients(message, count_recipient, NULL) || rcpt_enum_count != 1) {
            fprintf(stderr, "FAIL: enumerate_recipients count=%d, want 1\n", rcpt_enum_count);
            failures++;
        } else {
            printf("PASS[5/6]: enumerate messages=1 recipients=1\n");
        }
    }

    /* 断言 6: 超时配置返回生效值（离线可验证的行为） */
    {
        long t = smtp_set_timeout(session, Timeout_ENVELOPE, 60000L);
        if (t < 1000L) {
            fprintf(stderr, "FAIL: smtp_set_timeout returned %ld\n", t);
            failures++;
        } else {
            printf("PASS[6/6]: envelope timeout=%ld ms\n", t);
        }
    }

    smtp_destroy_session(session);

    if (failures != 0) {
        fprintf(stderr, "RESULT: %d of 6 assertions failed\n", failures);
        return 1;
    }
    printf("PASS: libesmtp linked, 6/6 session/message assertions ok\n");
    return 0;
}
