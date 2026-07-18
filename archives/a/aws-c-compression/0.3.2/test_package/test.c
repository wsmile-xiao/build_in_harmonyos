#include <stdio.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/compression/compression.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    /* These init functions return void in aws-c-common/aws-c-compression 0.x. */
    aws_common_library_init(allocator);
    aws_compression_library_init(allocator);
    if (aws_error_name(AWS_ERROR_COMPRESSION_UNKNOWN_SYMBOL) == NULL) {
        aws_compression_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }
    aws_compression_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-compression smoke test OK\n");
    return 0;
}
