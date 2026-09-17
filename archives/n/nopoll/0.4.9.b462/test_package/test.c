// test_package smoke test — 实质调用 noPoll 公开 API (R34)
//
// 场景：进程内创建 nopoll listener (127.0.0.1) + nopoll client 连接自身
// listener，发送/接收一条文本消息并断言回显一致。覆盖 noPoll 核心机制：
// nopoll_ctx_new/nopoll_listener_new/nopoll_conn_new/nopoll_conn_send_text/
// nopoll_conn_get_msg（握手、帧编解码、事件循环）。
//
// 鸿蒙特有验证：__OHOS__ 宏下输出平台标识，验证库在 HarmonyOS 上
// epoll/select、pthread mutex、socket 语义均正常工作。
#include <nopoll/nopoll.h>
#include <stdio.h>
#include <string.h>

#if defined(__OHOS__)
  #define PLATFORM_LABEL "HarmonyOS (OHOS)"
#else
  #define PLATFORM_LABEL "generic"
#endif

/* echo handler: reply with the same text */
static void on_msg(noPollCtx *ctx, noPollConn *conn, noPollMsg *msg, noPollPtr user_data) {
    const char *payload = (const char *)nopoll_msg_get_payload(msg);
    int len = nopoll_msg_get_payload_size(msg);
    nopoll_conn_send_text(conn, payload, len);
    nopoll_msg_unref(msg);
}

int main(void) {
    noPollCtx *ctx = nopoll_ctx_new();
    if (!ctx) { printf("FAIL: ctx_new\n"); return 1; }
    printf("platform: %s, nopoll ctx created\n", PLATFORM_LABEL);

    /* listener on a high port to avoid clashing with regression ports */
    noPollConn *listener = nopoll_listener_new(ctx, "127.0.0.1", "29876");
    if (!listener || !nopoll_conn_is_ok(listener)) {
        printf("FAIL: listener_new\n"); return 1;
    }
    printf("listener ready at 127.0.0.1:29876\n");

    nopoll_ctx_set_on_msg(ctx, on_msg, NULL);

    /* client connecting to our own listener */
    noPollConn *conn = nopoll_conn_new(ctx, "127.0.0.1", "29876", NULL, NULL, NULL, NULL);
    if (!conn || !nopoll_conn_is_ok(conn)) {
        printf("FAIL: conn_new\n"); return 1;
    }

    /* wait handshake — drive the listener loop while waiting so the
     * server side of the handshake is served */
    int tries = 0;
    while (!nopoll_conn_is_ready(conn) && tries < 400) {
        if (!nopoll_conn_is_ok(conn)) { printf("FAIL: handshake broken\n"); return 1; }
        nopoll_loop_wait(ctx, 10000); /* 10ms slice serving listener events */
        tries++;
    }
    if (!nopoll_conn_is_ready(conn)) { printf("FAIL: handshake timeout\n"); return 1; }

    /* drive listener loop while waiting for the echo */
    const char *text = "hello nopoll on ohos";
    if (nopoll_conn_send_text(conn, text, strlen(text)) != (int)strlen(text)) {
        printf("FAIL: send_text\n"); return 1;
    }

    noPollMsg *msg = NULL;
    tries = 0;
    while (tries < 300) {
        nopoll_loop_wait(ctx, 1); /* serve listener events (1us slice each) */
        msg = nopoll_conn_get_msg(conn);
        if (msg) break;
        if (!nopoll_conn_is_ok(conn)) { printf("FAIL: conn broken while waiting echo\n"); return 1; }
        tries++;
    }
    if (!msg) { printf("FAIL: no echo received\n"); return 1; }

    const char *echo = (const char *)nopoll_msg_get_payload(msg);
    int ok = (strcmp(echo, text) == 0);
    printf("echo roundtrip: '%s' -> %s\n", echo, ok ? "PASS" : "MISMATCH");
    nopoll_msg_unref(msg);

    nopoll_conn_close(conn);
    nopoll_conn_close(listener);
    nopoll_ctx_unref(ctx);

    printf("%s: nopoll loopback echo on %s\n", ok ? "PASS" : "FAIL", PLATFORM_LABEL);
    return ok ? 0 : 1;
}
