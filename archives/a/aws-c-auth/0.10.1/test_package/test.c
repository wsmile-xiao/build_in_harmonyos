#include <stdio.h>
#include <aws/common/common.h>
#include <aws/auth/auth.h>

static int init_libraries(struct aws_allocator *allocator) {
    aws_common_library_init(allocator);
    aws_common_fatal_assert_library_initialized();
    aws_auth_library_init(allocator);
    return 0;
}

static void clean_up_libraries(void) {
    aws_auth_library_clean_up();
    aws_common_library_clean_up();
}

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    if (init_libraries(allocator) != 0) {
        return 1;
    }
    clean_up_libraries();
    printf("aws-c-auth smoke test OK\n");
    return 0;
}
