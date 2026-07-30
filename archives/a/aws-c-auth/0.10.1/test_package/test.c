#include <stdio.h>
#include <aws/common/common.h>
#include <aws/auth/auth.h>

static int init_void_library(void (*init)(struct aws_allocator *), struct aws_allocator *allocator) {
    init(allocator);
    return AWS_OP_SUCCESS;
}

static int init_int_library(int (*init)(struct aws_allocator *), struct aws_allocator *allocator) {
    return init(allocator);
}

#define INIT_LIBRARY(func, allocator) \
    _Generic((func), \
        void (*)(struct aws_allocator *): init_void_library, \
        int (*)(struct aws_allocator *): init_int_library \
    )((func), (allocator))

static int init_libraries(struct aws_allocator *allocator) {
    if (INIT_LIBRARY(aws_common_library_init, allocator) != AWS_OP_SUCCESS) {
        return 1;
    }
    aws_common_fatal_assert_library_initialized();
    if (INIT_LIBRARY(aws_auth_library_init, allocator) != AWS_OP_SUCCESS) {
        aws_common_library_clean_up();
        return 1;
    }
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
