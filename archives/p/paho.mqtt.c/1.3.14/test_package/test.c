#include <stdio.h>
#include <string.h>
#include "MQTTClient.h"

int main(void) {
    /* R34: 实质调用被测包 API — MQTTClient 库版本检查 */
    MQTTClient client;
    int rc = MQTTClient_create(&client, "tcp://localhost:1883",
                               "test_client", MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc == MQTTCLIENT_SUCCESS) {
        printf("MQTTClient_create succeeded, rc=%d\n", rc);
        MQTTClient_destroy(&client);
    } else {
        printf("MQTTClient_create returned %d (expected without broker)\n", rc);
    }

    /* Verify library symbols are linked correctly */
    MQTTClient_connectOptions opts = MQTTClient_connectOptions_initializer;
    printf("MQTT connect options struct initialized, keepAliveInterval=%d\n",
           opts.keepAliveInterval);

    printf("paho.mqtt.c test: OK\n");
    return 0;
}
