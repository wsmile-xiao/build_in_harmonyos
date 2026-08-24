/*
 * test_package consumer test — 实质调用 ccp (libccp) 公共 API。
 * 覆盖: ccp_init / ccp_connection_start / ccp_connection_lookup /
 *       ccp_set_impl / ccp_get_impl / write_ready_msg / ccp_connection_free / ccp_free
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ccp.h>

#define MAX_CONNECTIONS 16
#define MAX_PROGRAMS 8

/* mock datapath 回调 */
static void mock_set_cwnd(struct ccp_connection *conn, u32 cwnd) {
    (void)conn;
    (void)cwnd;
}

static void mock_set_rate_abs(struct ccp_connection *conn, u32 rate) {
    (void)conn;
    (void)rate;
}

static int mock_send_msg(struct ccp_connection *conn, char *msg, int msg_size) {
    (void)conn;
    (void)msg;
    (void)msg_size;
    return 0;
}

static u64 mock_now(void) {
    return 0;
}

static u64 mock_since_usecs(u64 then) {
    (void)then;
    return 0;
}

static u64 mock_after_usecs(u64 usecs) {
    (void)usecs;
    return 0;
}

int main(void) {
    struct ccp_datapath dp;
    struct ccp_datapath_info info;
    struct ccp_connection *conn = NULL;
    struct ccp_connection *lookup = NULL;
    int rc = 0;
    int failures = 0;
    int marker = 0x1234abcd;

    memset(&dp, 0, sizeof(dp));
    dp.max_connections = MAX_CONNECTIONS;
    dp.ccp_active_connections =
        (struct ccp_connection *)calloc(MAX_CONNECTIONS, sizeof(struct ccp_connection));
    if (!dp.ccp_active_connections) {
        printf("FAIL: calloc active connections\n");
        return 1;
    }
    dp.max_programs = MAX_PROGRAMS;
    dp.set_cwnd = mock_set_cwnd;
    dp.set_rate_abs = mock_set_rate_abs;
    dp.send_msg = mock_send_msg;
    dp.now = mock_now;
    dp.since_usecs = mock_since_usecs;
    dp.after_usecs = mock_after_usecs;
    dp.fto_us = 100000;

    rc = ccp_init(&dp);
    if (rc < 0) {
        printf("FAIL: ccp_init rc=%d\n", rc);
        failures++;
        goto out;
    }

    memset(&info, 0, sizeof(info));
    info.init_cwnd = 10;
    info.mss = 1460;
    info.src_ip = 0x0100007f; /* 127.0.0.1 */
    info.src_port = 12345;
    info.dst_ip = 0x0100007f;
    info.dst_port = 443;
    strncpy(info.congAlg, "cubic", MAX_CONG_ALG_SIZE - 1);

    conn = ccp_connection_start(&dp, NULL, &info);
    if (!conn) {
        printf("FAIL: ccp_connection_start returned NULL\n");
        failures++;
        goto out;
    }

    lookup = ccp_connection_lookup(&dp, conn->index);
    if (lookup != conn) {
        printf("FAIL: ccp_connection_lookup mismatch\n");
        failures++;
        goto out;
    }

    /* impl 指针往返 */
    ccp_set_impl(conn, &marker);
    if (ccp_get_impl(conn) != &marker) {
        printf("FAIL: ccp_set_impl/ccp_get_impl roundtrip\n");
        failures++;
        goto out;
    }

    /* write_ready_msg: 生成 READY 消息 */
    {
        char buf[READY_MSG_SIZE];
        int n = write_ready_msg(buf, sizeof(buf), conn->index);
        if (n != READY_MSG_SIZE) {
            printf("FAIL: write_ready_msg rc=%d\n", n);
            failures++;
            goto out;
        }
    }

    ccp_connection_free(&dp, conn->index);

    if (failures == 0) {
        printf("test ccp 1.0.0: OK (init/start/lookup/impl/ready-msg/free)\n");
    }

out:
    ccp_free(&dp);
    free(dp.ccp_active_connections);
    return failures == 0 ? 0 : 1;
}
