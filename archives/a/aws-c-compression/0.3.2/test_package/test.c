#include <stdio.h>
#include <string.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/compression/compression.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    aws_common_library_init(allocator);
    aws_compression_library_init(allocator);

    /* Verify error codes are registered correctly */
    const char *err_name = aws_error_name(AWS_ERROR_COMPRESSION_UNKNOWN_SYMBOL);
    const char *expected = "AWS_ERROR_COMPRESSION_UNKNOWN_SYMBOL";
    if (err_name == NULL || strcmp(err_name, expected) != 0) {
        fprintf(stderr, "FAIL: error name mismatch: got %s, expected %s\n",
                err_name ? err_name : "(null)", expected);
        aws_compression_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    aws_compression_library_clean_up();
    aws_common_library_clean_up();

    printf("test aws-c-compression 0.3.2: OK\n");
    return 0;
}
