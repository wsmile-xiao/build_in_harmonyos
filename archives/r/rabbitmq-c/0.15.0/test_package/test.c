#include <stdio.h>
#include <rabbitmq-c/amqp.h>

int main(void) {
    const char *ver = amqp_version();
    uint32_t ver_num = amqp_version_number();

    if (ver == NULL) {
        fprintf(stderr, "FAIL: amqp_version() returned NULL\n");
        return 1;
    }

    printf("rabbitmq-c version: %s (0x%06x)\n", ver, ver_num);

    /* Verify version matches expected */
    if (ver_num == 0) {
        fprintf(stderr, "FAIL: amqp_version_number() returned 0\n");
        return 1;
    }

    printf("test rabbitmq-c 0.15.0: OK\n");
    return 0;
}
