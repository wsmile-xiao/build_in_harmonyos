#include <stdio.h>
#include <aws/common/byte_buf.h>
#include <aws/common/common.h>
#include <aws/mqtt/mqtt.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_common_fatal_assert_library_initialized();
    aws_mqtt_library_init(allocator);

    struct aws_byte_cursor topic = aws_byte_cursor_from_c_str("openharmony/pc/test");
    struct aws_byte_cursor wildcard_topic = aws_byte_cursor_from_c_str("openharmony/+/test");
    if (!aws_mqtt_is_valid_topic(&topic) || aws_mqtt_is_valid_topic(&wildcard_topic)) {
        aws_mqtt_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    aws_mqtt_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-mqtt smoke test OK\n");
    return 0;
}
