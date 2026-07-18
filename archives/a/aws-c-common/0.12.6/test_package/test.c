#include <stdio.h>
#include <string.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/common/error.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    if (strcmp(aws_error_name(AWS_ERROR_INVALID_ARGUMENT), "AWS_ERROR_INVALID_ARGUMENT") != 0) {
        aws_common_library_clean_up();
        return 1;
    }
    aws_common_library_clean_up();
    printf("aws-c-common smoke test OK\n");
    return 0;
}
