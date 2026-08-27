#include <stdio.h>
#include <aws/mqtt/mqtt.h>
#include <aws/common/common.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (!allocator) {
        printf("ERROR: default allocator is NULL\n");
        return 1;
    }
    aws_mqtt_library_init(allocator);
    printf("aws-c-mqtt library initialized: OK\n");
    aws_mqtt_library_clean_up();
    printf("aws-c-mqtt library cleaned up: OK\n");
    return 0;
}
