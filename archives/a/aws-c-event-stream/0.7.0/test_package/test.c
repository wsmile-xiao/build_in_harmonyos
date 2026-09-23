#include <aws/event-stream/event_stream.h>
#include <aws/common/allocator.h>
#include <aws/common/byte_buf.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 4;
    }
    /* aws_event_stream_library_init() returns void (unlike other aws-c-*
     * library_init functions), so there is no return value to check. */
    aws_event_stream_library_init(allocator);

    /* Create a message with no headers and no payload */
    struct aws_event_stream_message message;
    if (aws_event_stream_message_init(&message, allocator, NULL, NULL) != 0) {
        return 1;
    }

    /* The minimal message is prelude (12 bytes) + trailer (4 bytes) = 16 bytes */
    uint32_t total_len = aws_event_stream_message_total_length(&message);
    if (total_len < 16) {
        return 2;
    }

    /* Buffer should be non-NULL after init */
    const uint8_t *buf = aws_event_stream_message_buffer(&message);
    if (buf == NULL) {
        return 3;
    }

    aws_event_stream_message_clean_up(&message);
    aws_event_stream_library_clean_up();
    printf("aws-c-event-stream test passed\n");
    return 0;
}
