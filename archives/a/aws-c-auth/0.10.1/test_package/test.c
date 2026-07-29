#include <stdio.h>
#include <aws/common/common.h>
#include <aws/auth/auth.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_auth_library_init(allocator);
    aws_auth_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-auth smoke test OK\n");
    return 0;
}
