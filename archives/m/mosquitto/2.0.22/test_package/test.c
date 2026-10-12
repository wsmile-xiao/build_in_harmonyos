#include <stdio.h>
#include <string.h>
#include <mosquitto.h>

int main(void) {
    int major = 0, minor = 0, revision = 0;
    mosquitto_lib_init();
    mosquitto_lib_version(&major, &minor, &revision);
    printf("mosquitto version: %d.%d.%d\n", major, minor, revision);

    struct mosquitto *mosq = mosquitto_new("test_client", true, NULL);
    if (!mosq) {
        fprintf(stderr, "Failed to create mosquitto instance\n");
        mosquitto_lib_cleanup();
        return 1;
    }
    printf("mosquitto instance created successfully\n");

    mosquitto_destroy(mosq);
    mosquitto_lib_cleanup();
    printf("All tests passed\n");
    return 0;
}
