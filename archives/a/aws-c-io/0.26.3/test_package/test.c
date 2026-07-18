#include <stdio.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/io/io.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_cal_library_init(allocator);
    aws_io_library_init(allocator);

    if (!aws_io_error_code_is_retryable(AWS_IO_DNS_QUERY_AGAIN)) {
        aws_io_library_clean_up();
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    aws_io_library_clean_up();
    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-io smoke test OK\n");
    return 0;
}
