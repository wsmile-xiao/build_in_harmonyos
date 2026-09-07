/*
 * enet 2.7.0 HarmonyOS PC 专项测试 — UDP 回环 + 可靠包内容校验
 *
 * 真实消费者测试（R34）：实际调用 enet 公共 API 建立 client/server 两个
 * ENetHost（同进程 127.0.0.1 回环），完成 connect -> reliable 发包 ->
 * 服务端内容校验 -> echo 回包 -> 客户端内容校验 -> disconnect 全链路，
 * 任一校验失败以非零退出码失败。
 *
 * 编译（OHOS aarch64, clang 15.0.4）:
 *   clang -I<include> test.c libenet.a -o test_enet_ohos
 * 运行: ./test_enet_ohos
 */
#define _WINSOCK_DEPRECATED_NO_WARNINGS

#define ENET_IMPLEMENTATION
#include "enet.h"

#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

#define TEST_PORT 45678
#define TEST_CHANNEL 0
#define PAYLOAD_CLIENT "OHOS_ENET_RELIABLE_PAYLOAD_CLIENT->SERVER"
#define PAYLOAD_SERVER "OHOS_ENET_RELIABLE_PAYLOAD_SERVER->CLIENT"

static int g_failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        printf("[FAIL] %s\n", msg); \
        g_failures++; \
    } else { \
        printf("[PASS] %s\n", msg); \
    } \
} while (0)

/* 同进程双 host：server 监听 127.0.0.1:TEST_PORT，client 连接后双向可靠收发 */
static int run_loopback(void) {
    ENetHost *server = NULL, *client = NULL;
    ENetAddress addr;
    ENetPeer *server_peer = NULL, *client_peer = NULL;
    ENetEvent ev;
    int client_connected = 0, server_received = 0, client_received = 0;
    int server_disconnected = 0, client_disconnected = 0;
    enet_uint32 start, now;
    int rc = 1;

    memset(&addr, 0, sizeof(addr));
    addr.host = ENET_HOST_ANY;
    addr.port = TEST_PORT;
    server = enet_host_create(&addr, 1, 2, 0, 0);
    CHECK(server != NULL, "enet_host_create(server, 127.0.0.1:45678)");
    if (!server) return 1;

    client = enet_host_create(NULL, 1, 2, 0, 0);
    CHECK(client != NULL, "enet_host_create(client)");
    if (!client) { enet_host_destroy(server); return 1; }

    enet_address_set_host(&addr, "127.0.0.1");
    addr.port = TEST_PORT;
    client_peer = enet_host_connect(client, &addr, 2, 0);
    CHECK(client_peer != NULL, "enet_host_connect(client -> server)");
    if (!client_peer) { enet_host_destroy(client); enet_host_destroy(server); return 1; }

    start = enet_time_get();
    /* 事件泵：上限 10 秒，防挂死 */
    while (1) {
        int progress = 0;

        while (enet_host_service(server, &ev, 0) > 0) {
            progress = 1;
            if (ev.type == ENET_EVENT_TYPE_CONNECT) {
                server_peer = ev.peer;
                printf("[info] server: client connected (id=%u)\n", ev.peer->incomingPeerID);
            } else if (ev.type == ENET_EVENT_TYPE_RECEIVE) {
                if (ev.packet->dataLength == strlen(PAYLOAD_CLIENT) &&
                    memcmp(ev.packet->data, PAYLOAD_CLIENT, ev.packet->dataLength) == 0) {
                    server_received = 1;
                    printf("[info] server: payload verified (%zu bytes)\n", ev.packet->dataLength);
                } else {
                    printf("[FAIL] server: payload mismatch (%zu bytes)\n", ev.packet->dataLength);
                    g_failures++;
                }
                enet_packet_destroy(ev.packet);
                if (server_peer) {
                    ENetPacket *echo = enet_packet_create(PAYLOAD_SERVER,
                                                          strlen(PAYLOAD_SERVER),
                                                          ENET_PACKET_FLAG_RELIABLE);
                    enet_peer_send(server_peer, TEST_CHANNEL, echo);
                }
            } else if (ev.type == ENET_EVENT_TYPE_DISCONNECT ||
                       ev.type == ENET_EVENT_TYPE_DISCONNECT_TIMEOUT) {
                server_disconnected = 1;
                printf("[info] server: client disconnected\n");
            }
        }

        while (enet_host_service(client, &ev, 0) > 0) {
            progress = 1;
            if (ev.type == ENET_EVENT_TYPE_CONNECT) {
                client_connected = 1;
                printf("[info] client: connected to server\n");
                ENetPacket *pkt = enet_packet_create(PAYLOAD_CLIENT,
                                                     strlen(PAYLOAD_CLIENT),
                                                     ENET_PACKET_FLAG_RELIABLE);
                enet_peer_send(client_peer, TEST_CHANNEL, pkt);
            } else if (ev.type == ENET_EVENT_TYPE_RECEIVE) {
                if (ev.packet->dataLength == strlen(PAYLOAD_SERVER) &&
                    memcmp(ev.packet->data, PAYLOAD_SERVER, ev.packet->dataLength) == 0) {
                    client_received = 1;
                    printf("[info] client: echo payload verified (%zu bytes)\n", ev.packet->dataLength);
                } else {
                    printf("[FAIL] client: echo payload mismatch (%zu bytes)\n", ev.packet->dataLength);
                    g_failures++;
                }
                enet_packet_destroy(ev.packet);
                /* 收齐 echo 后优雅断开（完整断开握手，双方都会收到 DISCONNECT 事件） */
                if (client_received) enet_peer_disconnect(client_peer, 0);
            } else if (ev.type == ENET_EVENT_TYPE_DISCONNECT ||
                       ev.type == ENET_EVENT_TYPE_DISCONNECT_TIMEOUT) {
                client_disconnected = 1;
                printf("[info] client: disconnected from server\n");
            }
        }

        now = enet_time_get();
        if (client_connected && server_received && client_received &&
            server_disconnected && client_disconnected)
            break;
        if ((now - start) > 10000) {
            printf("[FAIL] loopback timeout: connected=%d server_recv=%d client_recv=%d "
                   "server_disc=%d client_disc=%d\n",
                   client_connected, server_received, client_received,
                   server_disconnected, client_disconnected);
            g_failures++;
            break;
        }
        if (!progress) {
#ifdef _WIN32
            Sleep(1);
#else
            usleep(1000);
#endif
        }
    }

    rc = g_failures == 0 ? 0 : 1;
    enet_host_destroy(client);
    enet_host_destroy(server);
    return rc;
}

int main(void) {
    printf("=== enet 2.7.0 HarmonyOS 专项测试 ===\n");
    if (enet_initialize() != 0) {
        printf("[FAIL] enet_initialize()\n");
        return 1;
    }
    printf("[PASS] enet_initialize()\n");

    int rc = run_loopback();

    enet_deinitialize();
    printf("=== RESULT: %s (failures=%d) ===\n", rc == 0 ? "PASS" : "FAIL", g_failures);
    return rc;
}
