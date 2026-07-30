#include <stdio.h>
#include <aws/common/common.h>
#include <aws/auth/auth.h>

typedef void (*aws_library_init_fn)(struct aws_allocator *);

static void init_aws_common_library(struct aws_allocator *allocator) {
    aws_library_init_fn init = aws_common_library_init;
    init(allocator);
}

static void init_aws_auth_library(struct aws_allocator *allocator) {
    aws_library_init_fn init = aws_auth_library_init;
    init(allocator);
}

static void init_libraries(struct aws_allocator *allocator) {
    init_aws_common_library(allocator);
    aws_common_fatal_assert_library_initialized();
    init_aws_auth_library(allocator);
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
    init_libraries(allocator);
    clean_up_libraries();
    printf("aws-c-auth smoke test OK\n");
    return 0;
}
