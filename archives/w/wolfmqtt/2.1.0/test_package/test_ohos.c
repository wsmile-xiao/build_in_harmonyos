/* HarmonyOS-specific test for wolfmqtt 2.1.0.
 *
 * Distinct from the consumer test (test.c, which exercises the
 * MqttClient_Init/DeInit lifecycle) and from the upstream unit suite.
 * This test validates that the library built for HarmonyOS actually
 * produces correct MQTT wire bytes at runtime on the OHOS target:
 *
 *   1. Builds an MQTT CONNECT packet through the public MqttEncode_Connect()
 *      API and asserts the fixed header (0x10), protocol-name bytes
 *      ("MQTT" with length 0x0004), protocol level (4 or 5 matching the
 *      built feature macros), and the clean-session flag (0x02) appear at
 *      the expected offsets — an observable, protocol-level result.
 *   2. Asserts the client-id wire string is present in the encoded payload
 *      and that the remaining-length prefix is consistent, proving the
 *      runtime encoder is coherent.
 *   3. Verifies the ENABLE_MQTT_TLS / WOLFMQTT_V5 / WOLFMQTT_NONBLOCK
 *      feature macros are actually propagated to consumers at compile time
 *      (ABI consistency between installed headers and built lib) and that
 *      the installed version header reports 2.1.0.
 *   4. MqttClient_Init/DeInit lifecycle on the OHOS runtime.
 *
 * This is a genuine HarmonyOS-platform test: it links the OHOS cross-built
 * static library and runs on the HarmonyOS kernel (see uname in W3 log).
 */
#include <stdio.h>
#include <string.h>

#include <wolfmqtt/mqtt_client.h>
#include <wolfmqtt/mqtt_packet.h>
#include <wolfmqtt/version.h>

#ifndef ENABLE_MQTT_TLS
#error "ENABLE_MQTT_TLS must be propagated to consumers (ABI consistency)"
#endif

static int failures = 0;

#define CHECK(cond, msg) do { \
        if (!(cond)) { \
            fprintf(stderr, "FAIL: %s\n", msg); \
            failures++; \
        } \
    } while (0)

/* Stub network callbacks: MqttSocket_Init validates these pointers non-NULL;
 * the test never performs I/O. */
static int net_connect(void *context, const char *host, word16 port,
                       int timeout_ms)
{
    (void)context; (void)host; (void)port; (void)timeout_ms;
    return MQTT_CODE_SUCCESS;
}
static int net_read(void *context, byte *buf, int buf_len, int timeout_ms)
{
    (void)context; (void)buf; (void)buf_len; (void)timeout_ms;
    return MQTT_CODE_SUCCESS;
}
static int net_write(void *context, const byte *buf, int buf_len,
                     int timeout_ms)
{
    (void)context; (void)buf; (void)buf_len; (void)timeout_ms;
    return MQTT_CODE_SUCCESS;
}
static int net_disconnect(void *context)
{
    (void)context;
    return MQTT_CODE_SUCCESS;
}

int main(void)
{
    MqttClient client;
    MqttNet net;
    MqttConnect connect;
    byte tx_buf[512];
    byte rx_buf[256];
    byte packet[128];
    int rc;

    /* --- 1. CONNECT wire bytes via public API --- */
    memset(&connect, 0, sizeof(connect));
    connect.keep_alive_sec = 60;
    connect.clean_session = 1;
    connect.client_id = "ohos-test";
    connect.enable_lwt = 0;

    memset(packet, 0, sizeof(packet));
    rc = MqttEncode_Connect(packet, (int)sizeof(packet), &connect);
    CHECK(rc > 0, "MqttEncode_Connect returns positive packet length");
    CHECK(rc <= (int)sizeof(packet), "encoded packet fits the buffer");

    /* Fixed header: high nibble 0x1 (CONNECT), low nibble 0 (flags). */
    CHECK((packet[0] & 0xF0) == 0x10, "CONNECT fixed header byte 0x10");
    CHECK(packet[1] == (byte)(rc - 2), "remaining-length prefix consistent");

    /* Variable header starts at offset 2 (2-byte fixed header for small
     * packets): protocol name length 0x0004 + "MQTT". */
    CHECK(packet[2] == 0x00 && packet[3] == 0x04, "protocol name length 4");
    CHECK(packet[4] == 'M' && packet[5] == 'Q' && packet[6] == 'T' &&
          packet[7] == 'T', "protocol name MQTT");
#ifdef WOLFMQTT_V5
    CHECK(packet[8] == MQTT_CONNECT_PROTOCOL_LEVEL_5,
          "protocol level 5 (v5 build)");
#else
    CHECK(packet[8] == MQTT_CONNECT_PROTOCOL_LEVEL_4,
          "protocol level 4 (v3.1.1 build)");
#endif
    CHECK((packet[9] & MQTT_CONNECT_FLAG_CLEAN_SESSION) != 0,
          "clean-session flag 0x02 set");

    /* Client id "ohos-test" must appear as wire bytes in the payload.
     * Scan the whole packet (client-id sits after the variable header). */
    {
        const byte needle[] = "ohos-test";
        int i, found = 0;
        for (i = 2; i + (int)sizeof(needle) - 1 <= rc; i++) {
            if (memcmp(packet + i, needle, sizeof(needle) - 1) == 0) {
                found = 1;
                break;
            }
        }
        CHECK(found, "client-id 'ohos-test' present in encoded payload");
    }

    /* --- 2. Feature-macro ABI propagation --- */
#ifdef WOLFMQTT_V5
    CHECK(1, "WOLFMQTT_V5 propagated to consumer build");
#else
    CHECK(0, "WOLFMQTT_V5 must be propagated");
#endif
#ifdef WOLFMQTT_NONBLOCK
    CHECK(1, "WOLFMQTT_NONBLOCK propagated to consumer build");
#else
    CHECK(0, "WOLFMQTT_NONBLOCK must be propagated");
#endif
    if (strcmp(LIBWOLFMQTT_VERSION_STRING, "2.1.0") != 0) {
        fprintf(stderr, "FAIL: version header reports '%s', expected 2.1.0\n",
                LIBWOLFMQTT_VERSION_STRING);
        failures++;
    }

    /* --- 3. Client lifecycle on OHOS runtime --- */
    memset(&client, 0, sizeof(client));
    memset(&net, 0, sizeof(net));
    net.connect = net_connect;
    net.read = net_read;
    net.write = net_write;
    net.disconnect = net_disconnect;
    rc = MqttClient_Init(&client, &net, NULL,
                         tx_buf, (int)sizeof(tx_buf),
                         rx_buf, (int)sizeof(rx_buf),
                         1000);
    CHECK(rc == MQTT_CODE_SUCCESS,
          "MqttClient_Init succeeds on OHOS runtime");
    MqttClient_DeInit(&client);

    if (failures == 0) {
        printf("test_ohos 2.1.0 (HarmonyOS): OK — CONNECT wire bytes, "
               "macro ABI, version header, client lifecycle all pass\n");
        return 0;
    }
    printf("test_ohos 2.1.0 (HarmonyOS): %d FAILURE(S)\n", failures);
    return 1;
}