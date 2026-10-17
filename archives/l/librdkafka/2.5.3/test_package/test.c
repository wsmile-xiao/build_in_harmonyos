#include <librdkafka/rdkafka.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Create a kafka config object — exercises the library's core API */
    rd_kafka_conf_t *conf = rd_kafka_conf_new();
    if (!conf) {
        fprintf(stderr, "FAIL: rd_kafka_conf_new() returned NULL\n");
        return 1;
    }

    /* Verify version string is accessible */
    const char *ver = rd_kafka_version_str();
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: rd_kafka_version_str() returned empty\n");
        rd_kafka_conf_destroy(conf);
        return 1;
    }
    printf("librdkafka version: %s\n", ver);

    /* Verify we can set a configuration property */
    char errstr[512];
    if (rd_kafka_conf_set(conf, "metadata.broker.list", "localhost:9092",
                          errstr, sizeof(errstr)) != RD_KAFKA_CONF_OK) {
        fprintf(stderr, "FAIL: rd_kafka_conf_set() failed: %s\n", errstr);
        rd_kafka_conf_destroy(conf);
        return 1;
    }

    rd_kafka_conf_destroy(conf);
    printf("test librdkafka 2.5.3: OK\n");
    return 0;
}
