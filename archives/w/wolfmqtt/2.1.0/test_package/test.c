/* Consumer test for wolfmqtt 2.1.0 (HarmonyOS adaptation).
 *
 * Exercises the public client API as a real library consumer:
 *   1. MqttClient_Init() against a stub (zeroed) MqttNet — no I/O needed;
 *   2. asserts the library stored our callback and command timeout;
 *   3. MqttClient_DeInit() cleanup path.
 *
 * Built with ENABLE_MQTT_TLS (upstream default), so this also proves the
 * wolfssl dependency links into a working consumer binary.
 */
#include <stdio.h>
#include <string.h>

#include <wolfmqtt/mqtt_client.h>

static int msg_cb(MqttClient *client, MqttMessage *message,
                  byte msg_new, byte msg_done)
{
    (void)client;
    (void)message;
    (void)msg_new;
    (void)msg_done;
    return MQTT_CODE_SUCCESS;
}

/* Stub network callbacks: MqttClient_Init validates these pointers, but the
 * test never performs I/O. */
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
    byte tx_buf[256];
    byte rx_buf[256];
    int rc;

    (void)memset(&client, 0, sizeof(client));
    (void)memset(&net, 0, sizeof(net));
    net.connect = net_connect;
    net.read = net_read;
    net.write = net_write;
    net.disconnect = net_disconnect;

    rc = MqttClient_Init(&client, &net, msg_cb,
                         tx_buf, (int)sizeof(tx_buf),
                         rx_buf, (int)sizeof(rx_buf),
                         1000);
    if (rc != MQTT_CODE_SUCCESS) {
        fprintf(stderr, "FAIL: MqttClient_Init returned %d\n", rc);
        return 1;
    }
    if (client.msg_cb != msg_cb) {
        fprintf(stderr, "FAIL: MqttClient_Init did not store msg_cb\n");
        return 1;
    }
    if (client.cmd_timeout_ms != 1000) {
        fprintf(stderr, "FAIL: cmd_timeout_ms=%d, expected 1000\n",
                client.cmd_timeout_ms);
        return 1;
    }
    if (client.tx_buf != tx_buf || client.rx_buf != rx_buf) {
        fprintf(stderr, "FAIL: client buffers not stored\n");
        return 1;
    }

    MqttClient_DeInit(&client);

    printf("test_wolfmqtt 2.1.0: OK\n");
    return 0;
}
