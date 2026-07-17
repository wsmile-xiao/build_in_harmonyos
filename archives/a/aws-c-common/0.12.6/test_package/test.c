#include <stdio.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_common_fatal_assert_library_initialized();
    aws_common_library_clean_up();
    printf("aws-c-common smoke test OK\n");
    return 0;
}
