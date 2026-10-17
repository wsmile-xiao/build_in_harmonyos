/* Stub implementation of aws_tls_handler_protocol.
 *
 * aws-c-io built with BYO_CRYPTO=ON does not compile this function,
 * but aws-c-http references it. This stub provides a safe fallback
 * that returns an empty byte_buf.
 */
#include <stddef.h>

/* aws_byte_buf is a struct with { size_t len, uint8_t *buffer, size_t capacity, struct aws_allocator *allocator }.
 * Field order must match aws-c-common's definition for correct ABI on struct return by value.
 * On aarch64, returning a zero-initialized struct is safe. */
typedef struct {
    size_t len;
    unsigned char *buffer;
    size_t capacity;
    void *allocator;
} aws_byte_buf_stub;

aws_byte_buf_stub aws_tls_handler_protocol(void *handler) {
    aws_byte_buf_stub empty = {0, NULL, 0, NULL};
    return empty;
}
